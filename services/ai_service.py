"""
Spendora — AI Service.

Integrates Google Gemini (gemini-3.8-flash) for:
1. Personalized category prediction based on profession and lifestyle baselines.
2. Grounded conversational financial assistant with strict anti-hallucination rules.

Safety & Architecture Principles:
- Financial figures are ALWAYS computed deterministically by the calculation engine
  and passed as ground-truth context to Gemini. The model is forbidden from inventing numbers.
- The assistant is strictly read-only.
- Robust offline fallbacks ensure the app never crashes if the API key is missing or network fails.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

from config.settings import (
    CURRENCY_SYMBOLS,
    DEFAULT_CURRENCY,
    GEMINI_API_KEY,
    PROFESSION_CATEGORY_SUGGESTIONS,
)
from database.database import get_session
from database.repositories.user_repository import UserRepository
from services.analytics_service import AnalyticsService
from services.calculation_service import CalculationService
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

    def is_configured(self) -> bool:
        """Return True if Gemini API key is configured and client initialized."""
        return self._client is not None and bool(self._api_key)

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
    # Grounded Conversational Financial Assistant
    # ------------------------------------------------------------------

    def query_financial_assistant(
        self,
        user_id: int,
        question: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """
        Answer a user's natural language financial question.

        Anti-Hallucination Guarantee:
        1. Gathers 100% verified deterministic numbers from the calculation engine.
        2. Supplies these figures as Ground Truth in the system prompt.
        3. Instructs Gemini to rely strictly on the data provided.
        4. Provides a smart local heuristic fallback if unconfigured.
        """
        context = self._gather_financial_context(user_id)

        if not self.is_configured():
            return self._local_financial_answer(question, context)

        system_instruction = (
            "You are Spendora Assistant, a friendly, insightful, and precise personal financial coach.\n"
            "CRITICAL INSTRUCTIONS:\n"
            "1. Ground all answers strictly in the Verified Financial Data provided below. NEVER invent or guess figures.\n"
            "2. If the user asks about an amount or category not found in the data, state clearly that no records exist for it.\n"
            f"3. Always quote exact figures with the user's currency symbol ({context['currency_sym']}).\n"
            "4. Keep answers concise, clear, and actionable (1 to 3 short paragraphs).\n"
            "5. The assistant is READ-ONLY and cannot modify, delete, or create transactions.\n\n"
            f"--- VERIFIED FINANCIAL DATA (GROUND TRUTH) ---\n"
            f"User: {context['user_name']}\n"
            f"Currency: {context['currency']} ({context['currency_sym']})\n"
            f"Monthly Income Baseline: {context['monthly_income_str']}\n"
            f"Fixed Expenses Baseline: {context['fixed_expenses_str']}\n\n"
            f"[THIS MONTH ({context['this_month_name']})]:\n"
            f"- Total Income: {context['cur_income']}\n"
            f"- Total Expenses: {context['cur_expense']}\n"
            f"- Net Balance: {context['cur_net']} ({context['cur_status']})\n"
            f"- Average Daily Expense: {context['cur_daily_burn']}/day\n"
            f"- Transaction Count: {context['cur_txns_count']}\n\n"
            f"[LAST MONTH ({context['last_month_name']})]:\n"
            f"- Total Income: {context['last_income']}\n"
            f"- Total Expenses: {context['last_expense']}\n"
            f"- Net Balance: {context['last_net']} ({context['last_status']})\n\n"
            f"[CATEGORY SPENDING THIS MONTH]:\n"
            f"{context['category_breakdown_text']}\n\n"
            f"[KEY INSIGHTS]:\n"
            f"- Top Expense Category: {context['top_category']}\n"
            f"- Peak Spending Day: {context['peak_day']}\n"
            f"- Largest Single Purchase: {context['largest_purchase']}\n"
            f"- Average Expense Transaction: {context['avg_txn_size']}\n\n"
            f"[RECENT TRANSACTIONS]:\n"
            f"{context['recent_txns_text']}\n"
        )

        try:
            from google.genai import types

            response = self._client.models.generate_content(
                model=GEMINI_MODEL,
                contents=question,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.3,
                ),
            )

            if response.text:
                return response.text.strip()

        except Exception as exc:
            logger.warning("Gemini financial assistant call failed (%s) — using local answer", exc)

        return self._local_financial_answer(question, context)

    # ------------------------------------------------------------------
    # Ground Truth Financial Context Gathering
    # ------------------------------------------------------------------

    def _gather_financial_context(self, user_id: int) -> Dict[str, Any]:
        """Gather verified real-time financial context for the user."""
        with get_session() as session:
            user = UserRepository(session).get_by_id(user_id)
            user_name = user.name if user else "User"
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

        # 3. Category Distribution This Month
        dist = self._analytics_service.get_category_spending_distribution(user_id, start_cur, end_cur)
        if dist:
            cat_lines = [
                f"• {item['name']}: {format_currency(item['amount_paise'], currency)} ({item['percentage']}%, {item['transaction_count']} txns)"
                for item in dist
            ]
            cat_text = "\n".join(cat_lines)
        else:
            cat_text = "No expenses recorded this month."

        # 4. Spending Insights
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

        # 5. Recent Transactions
        recent = self._transaction_service.get_recent_transactions(user_id, limit=6)
        if recent:
            recent_lines = [
                f"• {t.transaction_date}: {t.transaction_type.value} of {format_currency(t.amount_paise, currency)} - {t.description or 'No description'}"
                for t in recent
            ]
            recent_text = "\n".join(recent_lines)
        else:
            recent_text = "No recent transactions recorded."

        return {
            "user_name": user_name,
            "currency": currency,
            "currency_sym": currency_sym,
            "monthly_income_str": format_currency(monthly_inc, currency) if monthly_inc else "None set",
            "fixed_expenses_str": format_currency(fixed_exp, currency) if fixed_exp else "None set",
            "this_month_name": month_label(today()),
            "cur_income": format_currency(cur_summary["total_income_paise"], currency),
            "cur_expense": format_currency(cur_summary["total_expenses_paise"], currency),
            "cur_net": format_currency(cur_summary["net_paise"], currency),
            "cur_status": cur_summary["status"],
            "cur_daily_burn": format_currency(cur_summary["avg_daily_expense_paise"], currency),
            "cur_txns_count": cur_summary["transaction_count"],
            "cur_income_paise": cur_summary["total_income_paise"],
            "cur_expense_paise": cur_summary["total_expenses_paise"],
            "cur_net_paise": cur_summary["net_paise"],
            "last_month_name": month_label(start_last),
            "last_income": format_currency(last_summary["total_income_paise"], currency),
            "last_expense": format_currency(last_summary["total_expenses_paise"], currency),
            "last_net": format_currency(last_summary["net_paise"], currency),
            "last_status": last_summary["status"],
            "category_breakdown_text": cat_text,
            "top_category": top_cat,
            "peak_day": peak_day,
            "largest_purchase": largest,
            "avg_txn_size": avg_txn,
            "recent_txns_text": recent_text,
        }

    # ------------------------------------------------------------------
    # Local Deterministic Fallback Q&A
    # ------------------------------------------------------------------

    def _local_financial_answer(self, question: str, ctx: Dict[str, Any]) -> str:
        """
        Generate a precision-accurate, deterministic answer using calculation context
        when offline or when GEMINI_API_KEY is not configured.
        """
        q = question.lower()
        notice = "" if self.is_configured() else "\n\n*(💡 Set GEMINI_API_KEY in .env for full conversational AI)*"

        # 1. Deficit, surplus, or balance comparisons
        if "more than i earn" in q or "deficit" in q or "surplus" in q or "balance" in q or "net" in q:
            net_paise = ctx["cur_net_paise"]
            if net_paise > 0:
                return (
                    f"Good news! You are currently operating at a **surplus (GAIN)** of **{ctx['cur_net']}** this month. "
                    f"Your income ({ctx['cur_income']}) exceeds your expenses ({ctx['cur_expense']}).{notice}"
                )
            elif net_paise < 0:
                return (
                    f"⚠️ You are currently spending more than you earn this month by **{ctx['cur_net']}** (LOSS). "
                    f"Total expenses: {ctx['cur_expense']} vs Total income: {ctx['cur_income']}.{notice}"
                )
            else:
                return f"You are currently at **break-even** this month ({ctx['cur_net']}).{notice}"

        # 2. Category distribution & top spending
        if "category" in q or "where" in q or "most" in q or "biggest" in q:
            return (
                f"Here is where your money is going this month ({ctx['this_month_name']}):\n\n"
                f"{ctx['category_breakdown_text']}\n\n"
                f"Largest single purchase: {ctx['largest_purchase']}.{notice}"
            )

        # 3. Expenses / spending queries
        if "spend" in q or "expense" in q or "cost" in q:
            if "last month" in q:
                return f"Last month ({ctx['last_month_name']}), you spent a total of **{ctx['last_expense']}**.{notice}"
            return (
                f"So far this month ({ctx['this_month_name']}), your total expenses are **{ctx['cur_expense']}**, "
                f"averaging approximately **{ctx['cur_daily_burn']}/day** across {ctx['cur_txns_count']} transactions.\n\n"
                f"Top expense category: {ctx['top_category']}.{notice}"
            )

        # 4. Income queries
        if "income" in q or "earn" in q or "salary" in q:
            if "last month" in q:
                return f"Last month ({ctx['last_month_name']}), your recorded income was **{ctx['last_income']}**.{notice}"
            return f"So far this month ({ctx['this_month_name']}), your recorded income is **{ctx['cur_income']}**.{notice}"

        if "save" in q or "optimize" in q or "tip" in q or "advice" in q:
            return (
                f"Here are actionable suggestions based on your {ctx['this_month_name']} data:\n\n"
                f"1. **Monitor your top category**: You spent {ctx['top_category']}, your largest expense area.\n"
                f"2. **Daily burn rate**: You are averaging {ctx['cur_daily_burn']}/day. Reducing this by 10% would save you significant money over 30 days.\n"
                f"3. **Current net position**: Your net position is {ctx['cur_net']} ({ctx['cur_status']}).{notice}"
            )

        # Default overview answer
        return (
            f"Here is your financial summary for {ctx['this_month_name']}:\n\n"
            f"• **Income**: {ctx['cur_income']}\n"
            f"• **Expenses**: {ctx['cur_expense']}\n"
            f"• **Net Position**: {ctx['cur_net']} ({ctx['cur_status']})\n"
            f"• **Daily Average**: {ctx['cur_daily_burn']}/day\n"
            f"• **Top Spending Area**: {ctx['top_category']}{notice}"
        )
