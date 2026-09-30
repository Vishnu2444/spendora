"""
Spendora — AI Service (Personal Financial ChatGPT).

Integrates Google Gemini (gemini-3.8-flash) and local financial intelligence for:
1. Personalized category prediction based on profession and lifestyle baselines.
2. Grounded, conversational financial assistant (Personal Financial ChatGPT) with:
   - Full live visibility into balances, budgets, ledger, burn rate, and cash flow.
   - Conversational multi-turn memory.
   - Natural language expense & income logging (e.g. "Spent ₹250 on coffee").
   - Scenario forecasting & affordability checks ("Can I afford a ₹15,000 phone?").
   - 50-30-20 budget audits and personalized coaching.
   - 100% mathematical grounding in deterministic database calculations.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import date, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from config.settings import (
    CURRENCY_SYMBOLS,
    DEFAULT_CURRENCY,
    GEMINI_API_KEY,
    PROFESSION_CATEGORY_SUGGESTIONS,
)
from database.database import get_session
from database.models import Category, Transaction
from database.repositories.user_repository import UserRepository
from services.analytics_service import AnalyticsService
from services.calculation_service import CalculationService
from services.category_service import CategoryService
from services.profile_service import ProfileService
from services.transaction_service import TransactionService
from utils.date_utils import (
    date_range_last_month,
    date_range_this_month,
    month_label,
    today,
)
from utils.formatting import format_currency
from utils.validators import validate_category_name

logger = logging.getLogger(__name__)

# Primary Gemini model
GEMINI_MODEL = "gemini-3.8-flash"


class AIContextScope(str, Enum):
    """Scope of financial context shared with Cloud AI (Minimum Necessary Data)."""
    NONE = "NONE"                     # Zero financial records (generic concepts, greetings)
    CATEGORY = "CATEGORY"             # Only requested category aggregate
    AFFORDABILITY = "AFFORDABILITY"   # Only net surplus & safe burn rate
    SUMMARY = "SUMMARY"               # Monthly aggregate totals (no itemized transactions)
    RECENT_TXNS = "RECENT_TXNS"       # Recent transactions list


class CandidateTransaction(BaseModel):
    """
    Pydantic-validated structured candidate transaction.
    Must be explicitly confirmed by the user before database persistence.
    """
    amount_str: str
    transaction_type: str = Field(pattern="^(EXPENSE|INCOME)$")
    category_id: Optional[int] = None
    category_name: str = "General"
    transaction_date: date
    description: str
    currency: str = "INR"
    notes: Optional[str] = None


class AIChatResponse:
    """Structured response from the Spendora AI Personal Financial Advisor."""

    def __init__(
        self,
        reply: str,
        action: Optional[str] = None,
        transaction_data: Optional[Dict[str, Any]] = None,
        suggested_followups: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.reply = reply
        self.action = action  # "TRANSACTION_LOGGED", "TRANSACTION_PENDING_CONFIRMATION", "AFFORDABILITY", "INSIGHT"
        self.transaction_data = transaction_data or {}
        self.suggested_followups = suggested_followups or []
        self.metadata = metadata or {}

    def __str__(self) -> str:
        return self.reply

    def __repr__(self) -> str:
        return f"<AIChatResponse action={self.action!r} reply={self.reply[:30]!r}...>"


class AIService:
    """Service coordinating Gemini AI features with local financial data grounding."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        self._api_key = api_key or GEMINI_API_KEY
        self._client = None
        if self._api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=self._api_key)
            except Exception as exc:
                logger.warning("Failed to initialize GenAI client: %s", exc)
                self._client = None

        self._calculation_service = CalculationService()
        self._analytics_service = AnalyticsService()
        self._transaction_service = TransactionService()
        self._category_service = CategoryService()
        self._profile_service = ProfileService()
        self._conversation_history: List[Dict[str, str]] = []
        self._pending_candidate_transaction: Optional[Dict[str, Any]] = None

    def is_configured(self) -> bool:
        """Return True if Gemini API key is configured and client initialized."""
        return self._client is not None and bool(self._api_key)

    def is_cloud_ai_enabled(self, user_id: Optional[int] = None) -> bool:
        """
        Check if cloud AI processing is enabled for this user.
        Privacy-first: Cloud AI defaults to 'false' (opt-in only).
        Must be explicitly enabled by user in settings.
        """
        if not self.is_configured():
            return False
        if user_id:
            try:
                pref = self._profile_service.get_preference(user_id, "cloud_ai_enabled", "false")
                return (pref or "").strip().lower() == "true"
            except Exception:
                return False
        return False

    def confirm_transaction(self, candidate_data: Dict[str, Any], user_id: int) -> Transaction:
        """
        Explicitly write candidate transaction to database after user confirmation.
        Validates structure deterministically using Pydantic.
        """
        candidate = CandidateTransaction(**candidate_data)
        txn = self._transaction_service.create_transaction(
            user_id=user_id,
            transaction_type=candidate.transaction_type,
            amount_str=candidate.amount_str,
            transaction_date=candidate.transaction_date,
            category_id=candidate.category_id,
            description=candidate.description,
            notes=candidate.notes,
            currency=candidate.currency,
        )
        self._pending_candidate_transaction = None
        return txn

    def clear_history(self) -> None:
        """Reset conversation session history."""
        self._conversation_history = []
        self._pending_candidate_transaction = None

    # ------------------------------------------------------------------
    # Category Prediction
    # ------------------------------------------------------------------

    def predict_categories(
        self,
        profession: str,
        custom_profession: Optional[str] = None,
        monthly_income_str: Optional[str] = None,
        fixed_expenses_str: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Predict personalized expense categories using Gemini.
        Falls back to curated profession suggestions if unconfigured or offline.
        """
        prof_label = (
            f"{profession} ({custom_profession})"
            if profession == "Other" and custom_profession
            else profession
        )

        if not self.is_configured():
            logger.info("Gemini API key not set — using local suggestions for %r", prof_label)
            return self._local_category_fallback(profession)

        prompt = (
            f"Generate a personalized list of 6 to 9 expense categories for a person working as '{prof_label}'.\n"
            f"Monthly income: {monthly_income_str or 'Not specified'}. "
            f"Fixed monthly expenses: {fixed_expenses_str or 'Not specified'}.\n\n"
            "Return a valid JSON array of objects with the following schema for each category:\n"
            "[\n"
            "  {\n"
            '    "name": "Category Name (e.g. Groceries, Tech Gadgets)",\n'
            '    "icon": "valid_icon_name (food, car, train, bus, home, laptop, book-open-variant, television-play, shopping, heart-pulse, lightning-bolt, piggy-bank, wifi, briefcase, cash, tag)",\n'
            '    "color": "hex_color_code (e.g. #FF6B6B, #4ECDC4, #45B7D1, #F7DC6F, #BB8FCE, #82E0AA, #F0B27A)",\n'
            '    "subcategories": ["Subcategory 1", "Subcategory 2", "Subcategory 3"]\n'
            "  }\n"
            "]\n"
            "Focus on categories relevant to their daily life, career expenses, utilities, and financial habits."
        )

        try:
            from google.genai import types

            response = self._client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.2,
                ),
            )

            raw_json = response.text
            data = json.loads(raw_json)
            if isinstance(data, list) and len(data) > 0:
                validated = []
                for item in data:
                    try:
                        clean_name = validate_category_name(item.get("name", ""))
                        clean_subs = [
                            validate_category_name(s)
                            for s in item.get("subcategories", [])
                            if isinstance(s, str) and s.strip()
                        ]
                        validated.append({
                            "name": clean_name,
                            "icon": item.get("icon", "tag"),
                            "color": item.get("color", "#4ECDC4"),
                            "subcategories": clean_subs,
                        })
                    except ValueError:
                        continue

                if validated:
                    return validated

        except Exception as exc:
            logger.warning("Gemini category prediction failed (%s) — falling back", exc)

        return self._local_category_fallback(profession)

    def _local_category_fallback(self, profession: str) -> List[Dict[str, Any]]:
        """Return curated default suggestions for the profession."""
        return PROFESSION_CATEGORY_SUGGESTIONS.get(
            profession,
            PROFESSION_CATEGORY_SUGGESTIONS.get("Other", []),
        )

    # ------------------------------------------------------------------
    # Personal Financial ChatGPT Interface
    # ------------------------------------------------------------------

    def chat(
        self,
        query: str,
        user_id: Optional[int] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        require_confirmation: bool = False,
    ) -> AIChatResponse:
        """
        Chat with Spendora AI — Personal Financial ChatGPT.

        Capabilities:
        - Resolves user context dynamically from database.
        - Parses natural language expense and income logging with relative dates ("yesterday").
        - Supports interactive transaction candidate preview before database persistence.
        - Evaluates financial questions against 100% grounded financial calculations.
        - Strict privacy: Cloud AI is opt-in only via user preferences.
        - Returns structured AIChatResponse with action, reply, and suggested followups.
        """
        if not user_id:
            user = self._profile_service.get_current_user()
            user_id = user.id if user else 1

        q_clean = query.strip().lower()

        # Check for natural language confirmation of pending candidate transaction
        if self._pending_candidate_transaction is not None:
            if q_clean in [
                "confirm", "confirm & log", "confirm and log", "yes", "log it",
                "save it", "proceed", "sure", "ok", "yes log it", "save",
            ]:
                candidate_data = self._pending_candidate_transaction
                txn = self.confirm_transaction(candidate_data, user_id=user_id)
                new_ctx = self._gather_financial_context(user_id)
                amount_paise = int(Decimal(candidate_data["amount_str"]) * 100)
                reply = (
                    f"✅ **Confirmed & Recorded {candidate_data['transaction_type'].title()}!**\n\n"
                    f"• **Amount**: **{format_currency(amount_paise, candidate_data['currency'])}**\n"
                    f"• **Description**: {candidate_data['description']}\n"
                    f"• **Category**: {candidate_data['category_name']}\n"
                    f"• **Date**: {candidate_data['transaction_date'].strftime('%d %b %Y')}\n\n"
                    f"📊 **Updated Financial Health ({new_ctx['this_month_name']})**:\n"
                    f"- Total Expenses: **{new_ctx['cur_expense']}**\n"
                    f"- Net Surplus: **{new_ctx['cur_net']}** ({new_ctx['cur_status']})\n"
                    f"- Safe Daily Spend: **{new_ctx['safe_daily_spend']}/day** remaining"
                )
                self._record_turn(query, reply)
                return AIChatResponse(
                    reply=reply,
                    action="TRANSACTION_LOGGED",
                    transaction_data={
                        "transaction_id": txn.id,
                        "amount_paise": txn.amount_paise,
                        "type": candidate_data["transaction_type"],
                        "category": candidate_data["category_name"],
                    },
                    suggested_followups=[
                        "What is my remaining surplus?",
                        "Can I still afford dinner tonight?",
                        "Show my 50-30-20 budget split",
                    ],
                )
            elif q_clean in ["cancel", "no", "discard", "nevermind", "stop", "abort", "don't log", "dont log"]:
                self._pending_candidate_transaction = None
                reply = "❌ **Transaction discarded.** No records were modified."
                self._record_turn(query, reply)
                return AIChatResponse(reply=reply, action="TRANSACTION_CANCELLED")

        context = self._gather_financial_context(user_id)
        history = conversation_history if conversation_history is not None else self._conversation_history

        # 1. Check for Natural Language Transaction Logging Intent
        tx_intent = self._parse_transaction_intent(query, context)
        if tx_intent:
            if tx_intent.get("is_ambiguous"):
                action_word = "spend on" if tx_intent.get("type") == "EXPENSE" else "receive for"
                reply = (
                    f"How much did you {action_word} **{tx_intent.get('desc')}**? "
                    f"Please specify the amount (for example: *'Spent ₹250 on {tx_intent.get('desc')}'*)."
                )
                self._record_turn(query, reply)
                return AIChatResponse(reply=reply, action="CLARIFICATION_NEEDED")

            return self._handle_transaction_logging(
                user_id,
                tx_intent,
                context,
                require_confirmation=require_confirmation,
            )

        # 2. If Cloud AI is Configured AND user has explicitly opted in
        if self.is_configured() and self.is_cloud_ai_enabled(user_id):
            scope, scope_meta = self.classify_context_scope(query)
            system_instruction = self._build_gemini_system_instruction(
                context, scope=scope, scope_meta=scope_meta
            )
            try:
                from google.genai import types

                logger.info("Executing Cloud AI assistant query (model: %s, scope: %s)", GEMINI_MODEL, scope.value)
                response = self._client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=query,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=0.3,
                    ),
                )

                if response and response.text:
                    reply_text = response.text.strip()
                    self._record_turn(query, reply_text)
                    followups = self._generate_suggested_followups(query, context)
                    return AIChatResponse(
                        reply=reply_text,
                        action="INSIGHT",
                        suggested_followups=followups,
                    )
            except Exception as exc:
                logger.warning("Gemini financial assistant call failed (%s) — using local answer", type(exc).__name__)

        # 3. Local Deterministic Financial Intelligence Fallback
        resp = self._smart_financial_chat(query, context, history)
        self._record_turn(query, resp.reply)
        return resp

    def query_financial_assistant(
        self,
        user_id: int,
        question: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """
        Backward-compatible string query method.
        Preserves compatibility with existing tests and services.
        """
        return self.chat(
            query=question,
            user_id=user_id,
            conversation_history=conversation_history,
        ).reply

    def _record_turn(self, query: str, reply: str) -> None:
        """Record turn into session conversation history."""
        self._conversation_history.append({"role": "user", "content": query})
        self._conversation_history.append({"role": "assistant", "content": reply})
        # Keep last 12 turns to prevent context blowup
        if len(self._conversation_history) > 12:
            self._conversation_history = self._conversation_history[-12:]

    # ------------------------------------------------------------------
    # Natural Language Transaction Logging
    # ------------------------------------------------------------------

    def _extract_relative_date(self, text: str) -> Tuple[date, str]:
        """
        Extract relative date reference from text and return (date, cleaned_text).
        Supports: yesterday, day before yesterday, X days ago, today.
        """
        t = text
        resolved_date = today()

        m_days_ago = re.search(r'\b(\d+)\s+days?\s+ago\b', t, re.IGNORECASE)
        if m_days_ago:
            days = int(m_days_ago.group(1))
            resolved_date = today() - timedelta(days=days)
            t = re.sub(r'\b\d+\s+days?\s+ago\b', '', t, flags=re.IGNORECASE)
        elif re.search(r'\bday\s+before\s+yesterday\b', t, re.IGNORECASE):
            resolved_date = today() - timedelta(days=2)
            t = re.sub(r'\bday\s+before\s+yesterday\b', '', t, flags=re.IGNORECASE)
        elif re.search(r'\byesterday\b', t, re.IGNORECASE):
            resolved_date = today() - timedelta(days=1)
            t = re.sub(r'\byesterday\b', '', t, flags=re.IGNORECASE)
        elif re.search(r'\btoday\b', t, re.IGNORECASE):
            resolved_date = today()
            t = re.sub(r'\btoday\b', '', t, flags=re.IGNORECASE)

        t = re.sub(r'\s+', ' ', t).strip()
        return resolved_date, t

    def _parse_transaction_intent(self, text: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse natural language expense/income logging statements.
        Extracts amounts, categories, and relative dates ("yesterday").
        Detects ambiguous attempts lacking amounts to request clarification.
        """
        t = text.strip()
        tl = t.lower()

        # Reject inquiry questions
        inquiry_triggers = [
            "how much", "can i afford", "did i spend", "what did i",
            "what is", "where is", "why is", "show me", "tell me",
            "forecast", "predict", "calculate", "compare", "?",
        ]
        if any(trig in tl for trig in inquiry_triggers):
            return None

        txn_date, cleaned_text = self._extract_relative_date(t)

        # 1. Income patterns
        inc_patterns = [
            r'(?:received|earned|got|credited)\s+(?:₹|rs\.?|inr)?\s*(\d+(?:,\d+)*(?:\.\d{1,2})?)\s*(?:as|from|for)?\s+(.+)',
            r'(?:received|earned|got|credited)\s+(?:a\s+)?(.+?)\s+(?:of\s+)?(?:₹|rs\.?|inr)?\s*(\d+(?:,\d+)*(?:\.\d{1,2})?)',
            r'(?:add|log)\s+income\s*(?:of)?\s*(?:₹|rs\.?|inr)?\s*(\d+(?:,\d+)*(?:\.\d{1,2})?)\s*(?:for|from)?\s+(.+)',
            r'(?:add|log)\s+income\s+(.+?)\s*(?:of)?\s*(?:₹|rs\.?|inr)?\s*(\d+(?:,\d+)*(?:\.\d{1,2})?)',
        ]
        for p in inc_patterns:
            m = re.search(p, cleaned_text, re.IGNORECASE)
            if m:
                val1, val2 = m.group(1), m.group(2)
                if re.match(r'^\d+(?:,\d+)*(?:\.\d{1,2})?$', val1.strip()):
                    amt, desc = val1, val2
                else:
                    amt, desc = val2, val1
                desc_clean = re.sub(r'^(?:for|from|as)\s+', '', desc.strip(), flags=re.IGNORECASE).strip()
                return {
                    "type": "INCOME",
                    "amount": amt.replace(',', ''),
                    "desc": desc_clean,
                    "category_hint": desc_clean,
                    "date": txn_date,
                }

        # 2. Expense patterns
        exp_patterns = [
            r'(?:spent|paid|bought|purchased|ordered|expensed)\s+(?:₹|rs\.?|inr)?\s*(\d+(?:,\d+)*(?:\.\d{1,2})?)\s*(?:on|for|at)?\s+(.+)',
            r'(?:bought|ordered)\s+(.+?)\s+(?:for|at)\s*(?:₹|rs\.?|inr)?\s*(\d+(?:,\d+)*(?:\.\d{1,2})?)',
            r'(?:paid)\s+(.+?)\s+(?:bill|fee|rent)?\s*(?:of)?\s*(?:₹|rs\.?|inr)?\s*(\d+(?:,\d+)*(?:\.\d{1,2})?)',
            r'(?:log|add)\s+expense\s*(?:of)?\s*(?:₹|rs\.?|inr)?\s*(\d+(?:,\d+)*(?:\.\d{1,2})?)\s*(?:for|on)?\s+(.+)',
            r'(?:log|add)\s+expense\s+(.+?)\s*(?:of)?\s*(?:₹|rs\.?|inr)?\s*(\d+(?:,\d+)*(?:\.\d{1,2})?)',
            r'(?:spent|paid)\s+(?:₹|rs\.?|inr)?\s*(\d+(?:,\d+)*(?:\.\d{1,2})?)\s*(?:at|in)?\s+(.+)',
        ]
        for p in exp_patterns:
            m = re.search(p, cleaned_text, re.IGNORECASE)
            if m:
                val1, val2 = m.group(1), m.group(2)
                if re.match(r'^\d+(?:,\d+)*(?:\.\d{1,2})?$', val1.strip()):
                    amt, desc = val1, val2
                else:
                    amt, desc = val2, val1
                desc_clean = re.sub(r'^(?:for|on|at)\s+', '', desc.strip(), flags=re.IGNORECASE).strip()
                return {
                    "type": "EXPENSE",
                    "amount": amt.replace(',', ''),
                    "desc": desc_clean,
                    "category_hint": desc_clean,
                    "date": txn_date,
                }

        # 3. Ambiguity detection: user attempted transaction logging without amount
        ambiguous_expense_match = re.search(
            r'^(?:spent|paid|bought|ordered|expensed|log\s+expense|add\s+expense)\s*(?:on|for|at)?\s*(.+)$',
            cleaned_text,
            re.IGNORECASE,
        )
        if ambiguous_expense_match:
            subj = ambiguous_expense_match.group(1).strip()
            if subj and not any(kw in subj.lower() for kw in ["how", "what", "where", "why", "when", "can i"]):
                return {
                    "is_ambiguous": True,
                    "type": "EXPENSE",
                    "desc": subj,
                }

        ambiguous_income_match = re.search(
            r'^(?:received|earned|got|credited|log\s+income|add\s+income)\s*(?:as|from|for)?\s*(.+)$',
            cleaned_text,
            re.IGNORECASE,
        )
        if ambiguous_income_match:
            subj = ambiguous_income_match.group(1).strip()
            if subj and not any(kw in subj.lower() for kw in ["how", "what", "where", "why", "when", "can i"]):
                return {
                    "is_ambiguous": True,
                    "type": "INCOME",
                    "desc": subj,
                }

        return None

    def _resolve_category(self, user_id: int, hint: str, desc: str) -> Tuple[Optional[int], str]:
        """Match natural language description to user's registered categories."""
        try:
            cats = self._category_service.list_categories(user_id)
        except Exception:
            cats = []

        if not cats:
            return None, "General"

        combined_text = f"{hint} {desc}".lower()

        keyword_map = {
            "food": ["food", "dinner", "lunch", "breakfast", "coffee", "cafe", "restaurant", "pizza", "burger", "swiggy", "zomato", "zepto", "blinkit", "grocer", "groceries", "snack", "tea", "subway", "meal"],
            "tech": ["tech", "laptop", "monitor", "software", "hardware", "cloud", "aws", "phone", "keyboard", "mouse", "apple", "gadget", "electronics", "chatgpt"],
            "travel": ["uber", "ola", "rapido", "cab", "taxi", "petrol", "fuel", "diesel", "parking", "toll", "flight", "train", "metro", "bus", "auto", "commute", "travel"],
            "utilities": ["electricity", "electric", "power", "water", "gas", "cylinder", "wifi", "broadband", "internet", "recharge", "rent", "maintenance", "bill", "mobile recharge"],
            "shopping": ["shopping", "clothes", "apparel", "amazon", "flipkart", "myntra", "shoes", "dress", "shirt", "mall", "retail"],
            "health": ["health", "gym", "medicine", "doctor", "clinic", "pharmacy", "hospital", "fitness", "supplement", "medical"],
            "entertainment": ["movie", "film", "netflix", "cinema", "spotify", "prime", "concert", "game", "gaming", "subscription", "book"],
        }

        # 1. Keyword semantic match
        for cat in cats:
            cat_lower = cat.name.lower()
            for key, keywords in keyword_map.items():
                if key in cat_lower and any(kw in combined_text for kw in keywords):
                    return cat.id, cat.name

        # 2. Substring match against existing category names
        for cat in cats:
            if cat.name.lower() in combined_text:
                return cat.id, cat.name

        # 3. Default to first active category
        return cats[0].id, cats[0].name

    def _handle_transaction_logging(
        self,
        user_id: int,
        intent: Dict[str, Any],
        context: Dict[str, Any],
        require_confirmation: bool = False,
    ) -> AIChatResponse:
        """Process transaction intent either for immediate persistence or candidate confirmation."""
        cat_id, cat_name = self._resolve_category(user_id, intent["category_hint"], intent["desc"])
        txn_type = intent["type"]
        amount_str = intent["amount"]
        raw_desc = intent["desc"].strip()
        desc_clean = (raw_desc[0].upper() + raw_desc[1:]) if raw_desc else txn_type.title()
        curr = context["currency"]
        txn_date = intent.get("date", today())

        candidate = CandidateTransaction(
            amount_str=amount_str,
            transaction_type=txn_type,
            category_id=cat_id,
            category_name=cat_name,
            transaction_date=txn_date,
            description=desc_clean,
            currency=curr,
            notes="Detected from natural language input",
        )

        amount_paise = int(Decimal(amount_str) * 100)

        # Interactive Mode: generate structured preview requiring confirmation
        if require_confirmation:
            self._pending_candidate_transaction = candidate.model_dump()
            date_str = "Today" if txn_date == today() else txn_date.strftime("%d %b %Y")
            reply = (
                f"📋 **Confirm Transaction Candidate**:\n\n"
                f"• **Type**: {candidate.transaction_type.title()}\n"
                f"• **Amount**: **{format_currency(amount_paise, curr)}**\n"
                f"• **Description**: {candidate.description}\n"
                f"• **Category**: {candidate.category_name}\n"
                f"• **Date**: {date_str}\n\n"
                f"Would you like me to log this to your ledger?\n"
                f"*(Reply **'Confirm'** or **'Cancel'**, or use the action buttons below)*"
            )
            self._record_turn(f"Candidate: {txn_type} {amount_str} for {desc_clean}", reply)
            return AIChatResponse(
                reply=reply,
                action="TRANSACTION_PENDING_CONFIRMATION",
                transaction_data=self._pending_candidate_transaction,
                suggested_followups=["Confirm & Log", "Cancel"],
            )

        # Immediate Persistence: used when require_confirmation is False (e.g. automated tests)
        try:
            txn = self.confirm_transaction(candidate.model_dump(), user_id)
            new_ctx = self._gather_financial_context(user_id)
            date_str = "Today" if txn_date == today() else txn_date.strftime("%d %b %Y")

            reply = (
                f"✅ **Recorded {txn_type.title()}!**\n\n"
                f"• **Amount**: **{format_currency(txn.amount_paise, curr)}**\n"
                f"• **Description**: {txn.description}\n"
                f"• **Category**: {cat_name}\n"
                f"• **Date**: {date_str} ({txn_date.strftime('%d %b %Y')})\n\n"
                f"📊 **Updated Financial Health ({new_ctx['this_month_name']})**:\n"
                f"- Total Expenses: **{new_ctx['cur_expense']}**\n"
                f"- Net Surplus: **{new_ctx['cur_net']}** ({new_ctx['cur_status']})\n"
                f"- Safe Daily Spend: **{new_ctx['safe_daily_spend']}/day** remaining"
            )

            self._record_turn(f"Log {txn_type} {amount_str} for {desc_clean}", reply)

            return AIChatResponse(
                reply=reply,
                action="TRANSACTION_LOGGED",
                transaction_data={
                    "transaction_id": txn.id,
                    "amount_paise": txn.amount_paise,
                    "type": txn_type,
                    "category": cat_name,
                },
                suggested_followups=[
                    "What is my remaining surplus?",
                    "Can I still afford dinner tonight?",
                    "Show my 50-30-20 budget split",
                ],
            )
        except Exception as exc:
            logger.error("Failed to log transaction from chat: %s", exc, exc_info=True)
            return AIChatResponse(
                reply=f"⚠️ I couldn't log that transaction: {exc}. Please check the amount and try again.",
                action="ERROR",
            )

    # ------------------------------------------------------------------
    # Gemini System Instruction Builder
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Data Minimization Context Classifier & Gemini Instruction Builder
    # ------------------------------------------------------------------

    @staticmethod
    def classify_context_scope(query: str) -> Tuple[AIContextScope, Dict[str, Any]]:
        """
        Classify query intent to enforce the Minimum Necessary Data Principle.
        Determines the minimal data scope required to answer the query.
        """
        q = query.strip().lower()

        # 1. Generic queries, definitions, budgeting rules, greetings, tips: ZERO financial records
        generic_triggers = [
            "what is", "explain", "how does", "define", "rule", "50/30/20", "50-30-20",
            "tip", "advice", "how to save", "hello", "hi", "hey", "who are you",
            "help", "what can you do", "best way to", "investing", "tax slab"
        ]
        is_personal = any(p in q for p in [
            "my ", "i spend", "did i", "can i", "have i", "my savings", "my budget",
            "my expense", "my income", "my balance", "for me", "we spend"
        ])

        if not is_personal and any(g in q for g in generic_triggers):
            return AIContextScope.NONE, {}

        # 2. Recent transactions inquiry
        if any(k in q for k in [
            "recent transaction", "latest transaction", "recent purchase",
            "latest purchase", "what did i buy", "show transactions", "list transaction"
        ]):
            return AIContextScope.RECENT_TXNS, {}

        # 3. Category-specific inquiries
        known_categories = [
            "food", "dining", "travel", "transport", "cab", "uber", "groceries", "grocery",
            "tech", "gadget", "electronics", "utilities", "electricity", "bill", "rent",
            "shopping", "health", "medical", "entertainment", "movie"
        ]
        for cat in known_categories:
            if cat in q:
                return AIContextScope.CATEGORY, {"category_hint": cat}

        # 4. Affordability / Purchase scenario check
        if any(k in q for k in ["can i afford", "can i buy", "should i buy", "can i spend"]):
            return AIContextScope.AFFORDABILITY, {}

        # 5. Default personal financial query: high-level summary only
        return AIContextScope.SUMMARY, {}

    def _build_gemini_system_instruction(
        self,
        context: Dict[str, Any],
        scope: AIContextScope = AIContextScope.SUMMARY,
        scope_meta: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Build minimal necessary prompt for Gemini based on query scope.
        Enforces Privacy-First Data Minimization:
        - Scope NONE: 0 financial records attached.
        - Scope CATEGORY: Only single matching category aggregate.
        - Scope AFFORDABILITY: Only net surplus & safe burn.
        - Scope RECENT_TXNS: Only recent transactions list.
        - Scope SUMMARY: High-level totals (excludes itemized transaction log).
        """
        base_instruction = (
            "You are Spendora Assistant, an elite personal financial ChatGPT and wealth coach.\n"
            "CRITICAL INSTRUCTIONS:\n"
            "1. Ground all answers strictly in the Verified Financial Data provided below (if any). NEVER invent or guess figures.\n"
            "2. If the user asks about an amount or category not found in the data, state clearly that no records exist for it.\n"
            f"3. Always quote exact figures with the user's currency symbol ({context['currency_sym']}).\n"
            "4. Format answers beautifully using Markdown (bold figures, bullet points, concise sections).\n"
            "5. Keep answers friendly, conversational, actionable, and concise (1 to 3 short paragraphs).\n"
            "6. Always frame financial insights non-authoritatively with context: 'Based on your recorded surplus of X, and assuming all recent expenses have been logged...'. State clearly that Spendora provides informational analysis, not certified financial or tax advice.\n\n"
        )

        # 1. SCOPE: NONE (Generic question or definition -> ZERO financial data)
        if scope == AIContextScope.NONE:
            return (
                "You are Spendora Assistant, an elite personal financial ChatGPT and wealth coach.\n"
                "CRITICAL INSTRUCTIONS:\n"
                "1. Answer the user's question clearly, concisely, and helpfully using standard financial principles.\n"
                "2. State clearly that Spendora provides informational financial analysis, not certified financial or tax advice.\n"
                "3. Keep answers friendly, conversational, and formatted with Markdown.\n"
                "[DATA MINIMIZATION ENFORCED: No personal financial records or transaction data were attached to this query.]\n"
            )

        # 2. SCOPE: CATEGORY (Only requested category aggregate)
        if scope == AIContextScope.CATEGORY:
            hint = (scope_meta or {}).get("category_hint", "").lower()
            matched_lines = []
            if context.get("categories_raw"):
                for cat in context["categories_raw"]:
                    if hint in cat["name"].lower():
                        matched_lines.append(
                            f"• Category '{cat['name']}': Total Spent: {format_currency(cat['amount_paise'], context['currency'])} "
                            f"({cat['percentage']}% of total expenses, {cat['transaction_count']} transactions)"
                        )
            cat_payload = "\n".join(matched_lines) if matched_lines else f"• No recorded spending found matching '{hint}' for this month."
            return (
                base_instruction +
                f"--- VERIFIED FINANCIAL DATA (CATEGORY SCOPE ONLY) ---\n"
                f"Currency: {context['currency']} ({context['currency_sym']})\n"
                f"Month: {context['this_month_name']}\n\n"
                f"[CATEGORY SPENDING DATA]:\n"
                f"{cat_payload}\n"
                f"[DATA MINIMIZATION ENFORCED: Irrelevant categories, recent transaction logs, and overall income records were omitted.]\n"
            )

        # 3. SCOPE: AFFORDABILITY (Only surplus and daily burn rate)
        if scope == AIContextScope.AFFORDABILITY:
            return (
                base_instruction +
                f"--- VERIFIED FINANCIAL DATA (AFFORDABILITY SCOPE ONLY) ---\n"
                f"Currency: {context['currency']} ({context['currency_sym']})\n"
                f"Month: {context['this_month_name']}\n"
                f"- Net Surplus: {context['cur_net']} ({context['cur_status']})\n"
                f"- Safe Daily Spend: {context['safe_daily_spend']}/day ({context['days_left']} days left in month)\n"
                f"[DATA MINIMIZATION ENFORCED: Itemized transactions and individual category logs were omitted.]\n"
            )

        # 4. SCOPE: RECENT_TXNS (Only recent transactions)
        if scope == AIContextScope.RECENT_TXNS:
            return (
                base_instruction +
                f"--- VERIFIED FINANCIAL DATA (RECENT TRANSACTIONS SCOPE ONLY) ---\n"
                f"Currency: {context['currency']} ({context['currency_sym']})\n"
                f"Month: {context['this_month_name']}\n\n"
                f"[RECENT TRANSACTIONS]:\n"
                f"{context['recent_txns_text']}\n"
                f"[DATA MINIMIZATION ENFORCED: Baseline income and budget audit models were omitted.]\n"
            )

        # 5. SCOPE: SUMMARY (Default financial summary: high-level aggregates, NO itemized transaction log)
        return (
            base_instruction +
            f"--- VERIFIED FINANCIAL DATA (GROUND TRUTH SUMMARY) ---\n"
            f"User: {context['user_name']}\n"
            f"Profession: {context['profession']}\n"
            f"Currency: {context['currency']} ({context['currency_sym']})\n"
            f"Monthly Income Baseline: {context['monthly_income_str']}\n"
            f"Fixed Expenses Baseline: {context['fixed_expenses_str']}\n\n"
            f"[THIS MONTH ({context['this_month_name']})]:\n"
            f"- Total Income: {context['cur_income']}\n"
            f"- Total Expenses: {context['cur_expense']}\n"
            f"- Net Balance: {context['cur_net']} ({context['cur_status']})\n"
            f"- Average Daily Expense: {context['cur_daily_burn']}/day\n"
            f"- Safe Daily Spend: {context['safe_daily_spend']}/day ({context['days_left']} days left)\n"
            f"- Opening Balance: {context['opening_balance']}\n"
            f"- Closing Ledger Balance: {context['closing_balance']}\n"
            f"- Transaction Count: {context['cur_txns_count']}\n\n"
            f"[50-30-20 BUDGET RULE AUDIT]:\n"
            f"- Needs (Fixed & Essentials): {context['needs_pct']}% (Target 50%)\n"
            f"- Wants (Discretionary): {context['wants_pct']}% (Target 30%)\n"
            f"- Savings / Surplus: {context['savings_pct']}% (Target 20%)\n\n"
            f"[CATEGORY SPENDING THIS MONTH]:\n"
            f"{context['category_breakdown_text']}\n"
            f"[DATA MINIMIZATION ENFORCED: Raw itemized transaction descriptions were omitted to protect privacy.]\n"
        )

    # ------------------------------------------------------------------
    # Ground Truth Financial Context Gathering
    # ------------------------------------------------------------------

    def _gather_financial_context(self, user_id: int) -> Dict[str, Any]:
        """Gather verified real-time financial context for the user."""
        with get_session() as session:
            user = UserRepository(session).get_by_id(user_id)
            user_name = user.name if user else "User"
            profession = user.profession if user and user.profession else "Professional"
            currency = user.currency if user and user.currency else DEFAULT_CURRENCY
            monthly_inc = user.monthly_income_paise if user else None
            fixed_exp = user.fixed_expenses_paise if user else None

        currency_sym = CURRENCY_SYMBOLS.get(currency, "₹")

        # 1. This Month
        start_cur, end_cur = date_range_this_month()
        cur_summary = self._calculation_service.calculate_period_summary(user_id, start_cur, end_cur)

        # 2. Last Month
        start_last, end_last = date_range_last_month()
        last_summary = self._calculation_service.calculate_period_summary(user_id, start_last, end_last)

        # 3. Days calculation
        d_today = today()
        days_passed = (d_today - start_cur).days + 1
        # Days remaining in month
        next_month_1st = (d_today.replace(day=28) + timedelta(days=4)).replace(day=1)
        last_day_of_month = next_month_1st - timedelta(days=1)
        days_in_month = last_day_of_month.day
        days_left = max(1, (last_day_of_month - d_today).days + 1)

        # 4. Safe Daily Spend calculation
        cur_net = cur_summary["net_paise"]
        safe_daily_paise = max(0, cur_net // days_left) if cur_net > 0 else 0

        # 5. Category Distribution This Month
        dist = self._analytics_service.get_category_spending_distribution(user_id, start_cur, end_cur)
        if dist:
            cat_lines = [
                f"• {item['name']}: {format_currency(item['amount_paise'], currency)} ({item['percentage']}%, {item['transaction_count']} txns)"
                for item in dist
            ]
            cat_text = "\n".join(cat_lines)
        else:
            cat_text = "No expenses recorded this month."

        # 6. Spending Insights
        insights = self._analytics_service.get_spending_insights(user_id, start_cur, end_cur)
        top_cat = (
            f"{insights['top_category_name']} ({format_currency(insights['top_category_paise'], currency)})"
            if insights["top_category_name"]
            else "None"
        )
        peak_day = (
            f"{insights['peak_day'].strftime('%d %B')} ({format_currency(insights['peak_day_amount_paise'], currency)})"
            if insights["peak_day"]
            else "None"
        )
        largest = (
            f"{insights['largest_expense']['description']} ({format_currency(insights['largest_expense']['amount_paise'], currency)})"
            if insights["largest_expense"]
            else "None"
        )
        avg_txn = format_currency(insights["average_transaction_paise"], currency)

        # 7. Recent Transactions
        recent = self._transaction_service.get_recent_transactions(user_id, limit=6)
        if recent:
            recent_lines = [
                f"• {t.transaction_date}: {t.transaction_type.value} of {format_currency(t.amount_paise, currency)} - {t.description or 'No description'}"
                for t in recent
            ]
            recent_text = "\n".join(recent_lines)
        else:
            recent_text = "No recent transactions recorded."

        # 8. 50-30-20 Budget Rule Calculation
        effective_income_paise = cur_summary["total_income_paise"] or (monthly_inc or 0)
        total_expense_paise = cur_summary["total_expenses_paise"]
        needs_paise = fixed_exp or 0
        wants_paise = max(0, total_expense_paise - needs_paise)
        savings_paise = max(0, effective_income_paise - total_expense_paise)

        if effective_income_paise > 0:
            needs_pct = round((needs_paise / effective_income_paise) * 100, 1)
            wants_pct = round((wants_paise / effective_income_paise) * 100, 1)
            savings_pct = round((savings_paise / effective_income_paise) * 100, 1)
        else:
            needs_pct, wants_pct, savings_pct = 50.0, 30.0, 20.0

        return {
            "user_name": user_name,
            "profession": profession,
            "currency": currency,
            "currency_sym": currency_sym,
            "monthly_income_str": format_currency(monthly_inc, currency) if monthly_inc else "None set",
            "fixed_expenses_str": format_currency(fixed_exp, currency) if fixed_exp else "None set",
            "monthly_income_paise": monthly_inc or 0,
            "fixed_expenses_paise": fixed_exp or 0,
            "this_month_name": month_label(today()),
            "days_passed": days_passed,
            "days_in_month": days_in_month,
            "days_left": days_left,
            "cur_income": format_currency(cur_summary["total_income_paise"], currency),
            "cur_expense": format_currency(cur_summary["total_expenses_paise"], currency),
            "cur_net": format_currency(cur_summary["net_paise"], currency),
            "cur_status": cur_summary["status"],
            "cur_daily_burn": format_currency(cur_summary["avg_daily_expense_paise"], currency),
            "cur_txns_count": cur_summary["transaction_count"],
            "cur_income_paise": cur_summary["total_income_paise"],
            "cur_expense_paise": cur_summary["total_expenses_paise"],
            "cur_net_paise": cur_summary["net_paise"],
            "opening_balance_paise": cur_summary["opening_balance_paise"],
            "closing_balance_paise": cur_summary["closing_balance_paise"],
            "opening_balance": format_currency(cur_summary["opening_balance_paise"], currency),
            "closing_balance": format_currency(cur_summary["closing_balance_paise"], currency),
            "safe_daily_spend_paise": safe_daily_paise,
            "safe_daily_spend": format_currency(safe_daily_paise, currency),
            "needs_paise": needs_paise,
            "wants_paise": wants_paise,
            "savings_paise": savings_paise,
            "needs_pct": needs_pct,
            "wants_pct": wants_pct,
            "savings_pct": savings_pct,
            "last_month_name": month_label(start_last),
            "last_income": format_currency(last_summary["total_income_paise"], currency),
            "last_expense": format_currency(last_summary["total_expenses_paise"], currency),
            "last_net": format_currency(last_summary["net_paise"], currency),
            "last_status": last_summary["status"],
            "category_breakdown_text": cat_text,
            "categories_raw": dist,
            "top_category": top_cat,
            "peak_day": peak_day,
            "largest_purchase": largest,
            "avg_txn_size": avg_txn,
            "recent_txns_text": recent_text,
        }

    # ------------------------------------------------------------------
    # Local Deterministic Financial Intelligence Engine
    # ------------------------------------------------------------------

    def _smart_financial_chat(
        self,
        query: str,
        ctx: Dict[str, Any],
        history: List[Dict[str, str]],
    ) -> AIChatResponse:
        """
        Comprehensive local deterministic financial intelligence engine.
        Acts as personal financial ChatGPT when offline or unconfigured.
        """
        q = query.lower()
        notice = "" if self.is_configured() else "\n\n*(💡 Set GEMINI_API_KEY in .env for full conversational AI)*"
        advice_disclaimer = (
            f"\n\n*(ℹ️ Informational guidance based on your recorded surplus of {ctx['cur_net']}. "
            f"Assumes all recent expenses have been logged. Spendora provides informational analytics, not certified financial or tax advice.)*"
        )
        curr = ctx["currency"]

        # 1. Affordability Scenario Check ("Can I afford ₹X?")
        if any(kw in q for kw in ["can i afford", "can i buy", "should i buy", "can i spend"]):
            amount_match = re.search(r'(?:₹|rs\.?|inr)?\s*(\d+(?:,\d+)*(?:\.\d{1,2})?)', q)
            if amount_match:
                amount_str = amount_match.group(1).replace(',', '')
                try:
                    purchase_paise = int(Decimal(amount_str) * 100)
                    cur_net = ctx["cur_net_paise"]
                    days_left = ctx["days_left"]
                    rem_surplus = cur_net - purchase_paise
                    rem_daily = max(0, rem_surplus // days_left) if rem_surplus > 0 else 0

                    if cur_net <= 0:
                        verdict = (
                            f"🔴 **Affordability Verdict: Caution — Over Budget**\n\n"
                            f"You are currently operating in a deficit (**{ctx['cur_net']}**) this month. "
                            f"Spending **{format_currency(purchase_paise, curr)}** would deepen your deficit to "
                            f"**{format_currency(abs(rem_surplus), curr)}**.{notice}"
                        )
                    elif purchase_paise > cur_net:
                        deficit_delta = purchase_paise - cur_net
                        verdict = (
                            f"🔴 **Affordability Verdict: Not Recommended Right Now**\n\n"
                            f"Your current monthly surplus is **{ctx['cur_net']}**, which is less than this purchase of **{format_currency(purchase_paise, curr)}**.\n"
                            f"Buying this now will tip your monthly cash flow into a deficit of **{format_currency(deficit_delta, curr)}** unless offset by extra income.{notice}"
                        )
                    elif purchase_paise <= cur_net * 0.5:
                        verdict = (
                            f"🟢 **Affordability Verdict: Yes, comfortably affordable!**\n\n"
                            f"You currently have a healthy net surplus of **{ctx['cur_net']}** with **{days_left} days** remaining in {ctx['this_month_name']}.\n"
                            f"After spending **{format_currency(purchase_paise, curr)}**, you will still retain **{format_currency(rem_surplus, curr)}** in surplus "
                            f"(giving you a safe discretionary spend of **{format_currency(rem_daily, curr)}/day**).{notice}"
                        )
                    else:
                        pct = round((purchase_paise / cur_net) * 100)
                        verdict = (
                            f"🟡 **Affordability Verdict: Feasible, but tight**\n\n"
                            f"This purchase of **{format_currency(purchase_paise, curr)}** will consume **{pct}%** of your remaining monthly surplus ({ctx['cur_net']}).\n"
                            f"Your remaining surplus will be **{format_currency(rem_surplus, curr)}**, leaving you with a daily allowance of **{format_currency(rem_daily, curr)}/day** for the rest of the month.{notice}"
                        )

                    return AIChatResponse(
                        reply=verdict,
                        action="AFFORDABILITY",
                        suggested_followups=[
                            "What is my safe daily spend?",
                            "Where can I trim expenses?",
                            "How is my 50-30-20 budget split?",
                        ],
                    )
                except Exception:
                    pass

        # 2. 50-30-20 Budget Rule Audit
        if any(kw in q for kw in ["50-30-20", "50/30/20", "budget rule", "split", "rule", "needs wants"]):
            reply = (
                f"### 📊 50-30-20 Budget Health Check ({ctx['this_month_name']})\n\n"
                f"• **Needs (Target 50%)**: **{ctx['needs_pct']}%** ({format_currency(ctx['needs_paise'], curr)})\n"
                f"  *Includes baseline fixed commitments and essential living costs.*\n\n"
                f"• **Wants (Target 30%)**: **{ctx['wants_pct']}%** ({format_currency(ctx['wants_paise'], curr)})\n"
                f"  *Discretionary spending across dining, tech, shopping, and entertainment.*\n\n"
                f"• **Savings / Investments (Target 20%)**: **{ctx['savings_pct']}%** ({format_currency(ctx['savings_paise'], curr)})\n"
                f"  *Your active net surplus accumulated this month.*\n\n"
                f"**Advisor Verdict**: "
            )
            if ctx["savings_pct"] >= 20.0:
                reply += f"🌟 **Excellent!** You are beating the 20% savings rule with a **{ctx['savings_pct']}%** retention rate."
            elif ctx["savings_pct"] > 0:
                reply += f"👍 **On Track!** You are saving {ctx['savings_pct']}%. Trimming 5-10% from your top category ({ctx['top_category']}) will help hit the golden 20% threshold."
            else:
                reply += f"⚠️ **Attention Needed.** Expenses exceed income. Prioritize cutting non-essential wants to restore positive savings."

            reply += notice
            return AIChatResponse(
                reply=reply,
                action="BUDGET_ADVICE",
                suggested_followups=[
                    "Can I afford a ₹10,000 purchase?",
                    "Forecast my month-end savings",
                    "What is my safe daily spend?",
                ],
            )

        # 3. Safe Daily Spend & Burn Rate
        if any(kw in q for kw in ["safe daily", "burn rate", "daily spend", "daily burn", "how much can i spend per day", "daily limit"]):
            reply = (
                f"### ⏱️ Spending Velocity & Safe Burn ({ctx['this_month_name']})\n\n"
                f"• **Current Daily Burn Rate**: **{ctx['cur_daily_burn']}/day** (averaged over the past {ctx['days_passed']} days)\n"
                f"• **Safe Discretionary Spend**: **{ctx['safe_daily_spend']}/day** for the remaining **{ctx['days_left']} days**\n"
                f"• **Current Net Position**: **{ctx['cur_net']}** ({ctx['cur_status']})\n\n"
                f"💡 **Strategy**: As long as your daily outlay stays under **{ctx['safe_daily_spend']}**, your month will close with positive surplus."
                f"{notice}"
            )
            return AIChatResponse(
                reply=reply,
                action="INSIGHT",
                suggested_followups=[
                    "How much did I spend this month?",
                    "Forecast month-end balance",
                    "Am I spending more than I earn?",
                ],
            )

        # 4. Forecast & Month-End Savings Projection
        if any(kw in q for kw in ["forecast", "month end", "end of month", "project", "projection", "runway", "will i save"]):
            daily_burn = ctx["cur_daily_burn"]
            projected_more_exp = ctx["cur_expense_paise"] + (
                (ctx["cur_expense_paise"] // max(1, ctx["days_passed"])) * ctx["days_left"]
            )
            projected_net = ctx["cur_income_paise"] - projected_more_exp
            status_word = "SURPLUS (GAIN)" if projected_net >= 0 else "DEFICIT (LOSS)"

            reply = (
                f"### 📈 Month-End Projection ({ctx['this_month_name']})\n\n"
                f"Based on your current burn rate of **{daily_burn}/day**:\n\n"
                f"• **Projected Month-End Expenses**: ~**{format_currency(projected_more_exp, curr)}**\n"
                f"• **Projected Net Position**: ~**{format_currency(projected_net, curr)}** ({status_word})\n"
                f"• **Days Remaining**: {ctx['days_left']} days\n\n"
                f"Maintain your safe daily spend under **{ctx['safe_daily_spend']}** to maximize your cash retention."
                f"{notice}"
            )
            return AIChatResponse(
                reply=reply,
                action="INSIGHT",
                suggested_followups=[
                    "What is my safe daily spend?",
                    "How to save 10% more?",
                    "Where is most of my money going?",
                ],
            )

        # 5. Category-Specific Inquiries
        categories = ["food", "dining", "travel", "transportation", "tech", "gadget", "groceries", "utilities", "bills", "shopping", "entertainment", "health"]
        matched_cat_term = next((c for c in categories if c in q), None)
        if matched_cat_term:
            matched_item = None
            if ctx["categories_raw"]:
                for item in ctx["categories_raw"]:
                    if matched_cat_term in item["name"].lower():
                        matched_item = item
                        break

            if matched_item:
                reply = (
                    f"### 🏷️ Spending in {matched_item['name']} ({ctx['this_month_name']})\n\n"
                    f"• **Total Spent**: **{format_currency(matched_item['amount_paise'], curr)}**\n"
                    f"• **Share of Total Expenses**: **{matched_item['percentage']}%**\n"
                    f"• **Transaction Count**: {matched_item['transaction_count']} transactions\n\n"
                    f"This is currently part of your tracked discretionary budget.{notice}"
                )
            else:
                reply = f"You haven't recorded any expenses under **{matched_cat_term.title()}** yet this month ({ctx['this_month_name']}).{notice}"

            return AIChatResponse(
                reply=reply,
                action="INSIGHT",
                suggested_followups=[
                    "Where is most of my money going?",
                    "Can I afford dinner tonight?",
                    "Log an expense",
                ],
            )

        # 6. Ledger & Cash Flow Summary
        if any(kw in q for kw in ["ledger", "cash flow", "opening balance", "closing balance", "inflow", "outflow", "credits", "debits"]):
            reply = (
                f"### 📑 Financial Ledger Summary ({ctx['this_month_name']})\n\n"
                f"• **Opening Balance**: **{ctx['opening_balance']}**\n"
                f"• **Total Credits (Inflow)**: **+{ctx['cur_income']}**\n"
                f"• **Total Debits (Outflow)**: **-{ctx['cur_expense']}**\n"
                f"• **Closing Net Balance**: **{ctx['closing_balance']}**\n"
                f"• **Net Cash Position**: **{ctx['cur_net']}** ({ctx['cur_status']})\n\n"
                f"Your chronological journal contains {ctx['cur_txns_count']} verified postings.{notice}"
            )
            return AIChatResponse(
                reply=reply,
                action="INSIGHT",
                suggested_followups=[
                    "Show recent transactions",
                    "How much did I spend this month?",
                    "What is my burn rate?",
                ],
            )

        # 7. Deficit, Surplus, or Net Position
        if any(kw in q for kw in ["more than i earn", "deficit", "surplus", "balance", "net"]):
            net_paise = ctx["cur_net_paise"]
            if net_paise > 0:
                reply = (
                    f"Good news! You are currently operating at a **surplus (GAIN)** of **{ctx['cur_net']}** this month. "
                    f"Your income ({ctx['cur_income']}) exceeds your expenses ({ctx['cur_expense']}).{notice}"
                )
            elif net_paise < 0:
                reply = (
                    f"⚠️ You are currently spending more than you earn this month by **{ctx['cur_net']}** (LOSS). "
                    f"Total expenses: {ctx['cur_expense']} vs Total income: {ctx['cur_income']}.{notice}"
                )
            else:
                reply = f"You are currently at **break-even** this month ({ctx['cur_net']}).{notice}"

            return AIChatResponse(
                reply=reply,
                action="INSIGHT",
                suggested_followups=[
                    "Where is most of my money going?",
                    "What is my burn rate?",
                    "50-30-20 budget audit",
                ],
            )

        # 8. Category Distribution & Top Spending
        if any(kw in q for kw in ["category", "where", "most", "biggest"]):
            reply = (
                f"Here is where your money is going this month ({ctx['this_month_name']}):\n\n"
                f"{ctx['category_breakdown_text']}\n\n"
                f"Largest single purchase: {ctx['largest_purchase']}.{notice}"
            )
            return AIChatResponse(
                reply=reply,
                action="INSIGHT",
                suggested_followups=[
                    "How much did I spend on dining?",
                    "Can I afford a ₹10,000 gadget?",
                    "What is my safe daily spend?",
                ],
            )

        # 9. Expenses / Spending Queries
        if any(kw in q for kw in ["spend", "expense", "cost"]):
            if "last month" in q:
                reply = f"Last month ({ctx['last_month_name']}), you spent a total of **{ctx['last_expense']}**.{notice}"
            else:
                reply = (
                    f"So far this month ({ctx['this_month_name']}), your total expenses are **{ctx['cur_expense']}**, "
                    f"averaging approximately **{ctx['cur_daily_burn']}/day** across {ctx['cur_txns_count']} transactions.\n\n"
                    f"Top expense category: {ctx['top_category']}.{notice}"
                )
            return AIChatResponse(
                reply=reply,
                action="INSIGHT",
                suggested_followups=[
                    "Where is most of my money going?",
                    "Can I afford dinner tonight?",
                    "What is my safe daily spend?",
                ],
            )

        # 10. Income Queries
        if any(kw in q for kw in ["income", "earn", "salary"]):
            if "last month" in q:
                reply = f"Last month ({ctx['last_month_name']}), your recorded income was **{ctx['last_income']}**.{notice}"
            else:
                reply = f"So far this month ({ctx['this_month_name']}), your recorded income is **{ctx['cur_income']}**.{notice}"
            return AIChatResponse(
                reply=reply,
                action="INSIGHT",
                suggested_followups=[
                    "How much have I spent so far?",
                    "What is my net surplus?",
                    "Forecast month-end savings",
                ],
            )

        # 11. Recent Transactions
        if any(kw in q for kw in ["recent", "last transaction", "latest purchase", "what did i buy"]):
            reply = (
                f"### 🕒 Recent Transactions ({ctx['this_month_name']})\n\n"
                f"{ctx['recent_txns_text']}\n\n"
                f"Total transactions this month: {ctx['cur_txns_count']}.{notice}"
            )
            return AIChatResponse(
                reply=reply,
                action="INSIGHT",
                suggested_followups=[
                    "What was my largest purchase?",
                    "Where is my money going?",
                    "What is my safe daily spend?",
                ],
            )

        # 12. Savings Optimization Advice
        if any(kw in q for kw in ["save", "optimize", "tip", "advice", "cut"]):
            reply = (
                f"Here are actionable suggestions based on your {ctx['this_month_name']} data:\n\n"
                f"1. **Monitor your top category**: You spent {ctx['top_category']}, your largest expense area.\n"
                f"2. **Daily burn rate**: You are averaging {ctx['cur_daily_burn']}/day. Reducing this by 10% would save you significant money over 30 days.\n"
                f"3. **Current net position**: Your net position is {ctx['cur_net']} ({ctx['cur_status']}).{notice}"
            )
            return AIChatResponse(
                reply=reply,
                action="INSIGHT",
                suggested_followups=[
                    "How is my 50-30-20 split?",
                    "What is my burn rate?",
                    "Can I afford a ₹12,000 purchase?",
                ],
            )

        # 13. Greetings / Help / Default Overview
        if any(kw in q for kw in ["hi", "hello", "hey", "who are you", "what can you do", "help"]):
            reply = (
                f"Hello {ctx['user_name']}! 👋 I am your **Spendora AI Personal Financial Concierge**.\n\n"
                f"I'm plugged directly into your live financial data to help you save and plan smarter:\n\n"
                f"• 💬 **Ask anything**: *'Can I afford a ₹15,000 phone?'*, *'How is my 50-30-20 split?'*\n"
                f"• ⚡ **Auto-Log Expenses**: Type *'Spent ₹350 on lunch'* or *'Paid 1500 for electricity'*\n"
                f"• 📊 **Analyze Spending**: *'How much did I spend on dining out?'*\n"
                f"• 📈 **Forecasting**: *'Project my month-end savings'*\n\n"
                f"Your current surplus this month is **{ctx['cur_net']}** with **{ctx['safe_daily_spend']}/day** in safe burn.{notice}"
            )
            return AIChatResponse(
                reply=reply,
                action="GREETING",
                suggested_followups=[
                    "Can I afford a ₹10,000 gadget?",
                    "How is my 50-30-20 split?",
                    "Safe daily spend",
                ],
            )

        # Default Overview Answer
        reply = (
            f"Here is your financial summary for {ctx['this_month_name']}:\n\n"
            f"• **Income**: {ctx['cur_income']}\n"
            f"• **Expenses**: {ctx['cur_expense']}\n"
            f"• **Net Position**: {ctx['cur_net']} ({ctx['cur_status']})\n"
            f"• **Daily Average**: {ctx['cur_daily_burn']}/day\n"
            f"• **Top Spending Area**: {ctx['top_category']}{notice}"
        )
        return AIChatResponse(
            reply=reply,
            action="INSIGHT",
            suggested_followups=[
                "Can I afford dinner out tonight?",
                "Analyze my 50-30-20 budget",
                "Where is my money going?",
            ],
        )

    def _generate_suggested_followups(self, query: str, context: Dict[str, Any]) -> List[str]:
        """Generate contextual suggestion chips for the user."""
        q = query.lower()
        if "afford" in q:
            return ["What is my safe daily spend?", "Show category breakdown", "50-30-20 budget audit"]
        if "50-30-20" in q or "budget" in q:
            return ["Can I afford a ₹12,000 purchase?", "Forecast month-end savings", "Where can I cut expenses?"]
        if "spend" in q or "expense" in q:
            return ["What is my daily burn rate?", "Show recent transactions", "Am I in surplus or deficit?"]
        return ["Can I afford a ₹15,000 purchase?", "How is my 50-30-20 split?", "What is my safe daily spend?"]
