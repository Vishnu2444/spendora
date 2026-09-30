"""
Spendora — Tests for AI Data Minimization (Phase 3).

Validates the Minimum Necessary Data Principle:
- Generic questions (e.g. 'What is the 50/30/20 rule?', 'Hello') include 0 personal financial records.
- Category questions (e.g. 'What did I spend on food this month?') include only the requested category.
- Affordability questions ('Can I afford ₹5,000?') include only surplus and safe burn.
- Sensitive fields not needed by a query (e.g. raw itemized transaction lists) are excluded.
- Context classifier correctly identifies minimal data scope.
"""

from __future__ import annotations

from unittest.mock import MagicMock
import pytest

from services.ai_service import AIContextScope, AIService


@pytest.fixture
def sample_financial_context():
    """Mock comprehensive financial context dictionary."""
    return {
        "user_name": "Alex",
        "profession": "Engineer",
        "currency": "INR",
        "currency_sym": "₹",
        "monthly_income_str": "₹1,00,000.00",
        "fixed_expenses_str": "₹30,000.00",
        "this_month_name": "September 2026",
        "cur_income": "₹1,00,000.00",
        "cur_expense": "₹45,000.00",
        "cur_net": "₹55,000.00",
        "cur_status": "SURPLUS",
        "cur_daily_burn": "₹1,500.00",
        "safe_daily_spend": "₹5,500.00",
        "days_left": 10,
        "opening_balance": "₹0.00",
        "closing_balance": "₹55,000.00",
        "cur_txns_count": 12,
        "needs_pct": 30.0,
        "wants_pct": 15.0,
        "savings_pct": 55.0,
        "category_breakdown_text": "• Food & Dining: ₹15,000.00 (33.3%, 8 txns)\n• Tech: ₹30,000.00 (66.7%, 4 txns)",
        "categories_raw": [
            {"name": "Food & Dining", "amount_paise": 15000_00, "percentage": 33.3, "transaction_count": 8},
            {"name": "Tech & Gadgets", "amount_paise": 30000_00, "percentage": 66.7, "transaction_count": 4},
        ],
        "top_category": "Tech & Gadgets",
        "peak_day": "15 September",
        "largest_purchase": "Laptop Monitor (₹25,000.00)",
        "avg_txn_size": "₹3,750.00",
        "recent_txns_text": "• 2026-09-28: EXPENSE of ₹15,000.00 - Secret Purchase at Private Store",
    }


class TestAIDataMinimization:
    """Test suite verifying minimal necessary financial data transfer."""

    def test_classify_generic_question_zero_context(self):
        """Generic educational or conversational questions require ZERO financial context."""
        scope, _ = AIService.classify_context_scope("What is the 50/30/20 budgeting rule?")
        assert scope == AIContextScope.NONE

        scope2, _ = AIService.classify_context_scope("Explain how compound interest works")
        assert scope2 == AIContextScope.NONE

        scope3, _ = AIService.classify_context_scope("Hello! Who are you?")
        assert scope3 == AIContextScope.NONE

    def test_classify_category_question(self):
        """Category inquiry requests only category context."""
        scope, meta = AIService.classify_context_scope("What did I spend on food this month?")
        assert scope == AIContextScope.CATEGORY
        assert meta.get("category_hint") == "food"

    def test_classify_affordability_question(self):
        """Affordability check requests only affordability context."""
        scope, _ = AIService.classify_context_scope("Can I afford to buy a ₹15,000 phone?")
        assert scope == AIContextScope.AFFORDABILITY

    def test_classify_recent_transactions_question(self):
        """Recent transactions query requests only recent transactions scope."""
        scope, _ = AIService.classify_context_scope("Show my recent transactions")
        assert scope == AIContextScope.RECENT_TXNS

    def test_generic_question_omits_all_financial_records(self, sample_financial_context):
        """Generic questions must not contain income, expenses, transactions, or account balances."""
        service = AIService(api_key=None)
        prompt = service._build_gemini_system_instruction(
            sample_financial_context,
            scope=AIContextScope.NONE,
        )

        assert "DATA MINIMIZATION ENFORCED" in prompt
        # Verify strictly NO personal financial figures or names exist
        assert "₹1,00,000" not in prompt
        assert "₹45,000" not in prompt
        assert "₹55,000" not in prompt
        assert "Secret Purchase" not in prompt
        assert "Alex" not in prompt

    def test_category_scope_omits_unrelated_categories_and_recent_txns(self, sample_financial_context):
        """Category question must only include the matching category aggregate."""
        service = AIService(api_key=None)
        prompt = service._build_gemini_system_instruction(
            sample_financial_context,
            scope=AIContextScope.CATEGORY,
            scope_meta={"category_hint": "food"},
        )

        assert "CATEGORY SCOPE ONLY" in prompt
        assert "Food & Dining" in prompt
        assert "₹15,000.00" in prompt
        # Must omit unrelated categories, income baseline, and raw recent transactions
        assert "Tech & Gadgets" not in prompt
        assert "Secret Purchase" not in prompt
        assert "Monthly Income Baseline" not in prompt

    def test_affordability_scope_omits_itemized_transactions(self, sample_financial_context):
        """Affordability question includes surplus and daily burn, omitting itemized transactions."""
        service = AIService(api_key=None)
        prompt = service._build_gemini_system_instruction(
            sample_financial_context,
            scope=AIContextScope.AFFORDABILITY,
        )

        assert "AFFORDABILITY SCOPE ONLY" in prompt
        assert "Net Surplus: ₹55,000.00" in prompt
        assert "Safe Daily Spend: ₹5,500.00" in prompt
        # Must omit raw transaction descriptions and category breakdowns
        assert "Secret Purchase" not in prompt
        assert "Food & Dining" not in prompt

    def test_summary_scope_omits_raw_itemized_transaction_descriptions(self, sample_financial_context):
        """Default summary includes high-level totals but omits itemized transaction descriptions."""
        service = AIService(api_key=None)
        prompt = service._build_gemini_system_instruction(
            sample_financial_context,
            scope=AIContextScope.SUMMARY,
        )

        assert "GROUND TRUTH SUMMARY" in prompt
        assert "Total Income: ₹1,00,000.00" in prompt
        assert "Total Expenses: ₹45,000.00" in prompt
        # Raw itemized transaction list omitted
        assert "Secret Purchase" not in prompt
