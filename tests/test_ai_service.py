"""
Spendora — Tests for AIService.

Validates:
- Category prediction parsing and schema validation
- Offline fallback category suggestions
- Financial context gathering (100% grounded in calculation engine)
- Anti-hallucination prompt construction
- Mocked Gemini assistant responses
- Local deterministic fallback answers for common financial queries
"""

from __future__ import annotations

import json
from datetime import date
from unittest.mock import MagicMock, patch
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.models import Base, Category, Transaction, TransactionType, User
from services.ai_service import AIService


@pytest.fixture(scope="function")
def ai_test_db():
    """Isolated SQLite database in-memory for AIService testing."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)

    from contextlib import contextmanager

    @contextmanager
    def mock_get_session():
        session = Session()
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    with patch("services.ai_service.get_session", side_effect=mock_get_session), \
         patch("services.calculation_service.get_session", side_effect=mock_get_session), \
         patch("services.analytics_service.get_session", side_effect=mock_get_session), \
         patch("services.transaction_service.get_session", side_effect=mock_get_session):
        yield Session

    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def ai_seed_user(ai_test_db):
    """Seed user profile and transactions for financial context tests."""
    Session = ai_test_db
    with Session() as session:
        user = User(
            name="Alex",
            profession="Software Engineer",
            monthly_income_paise=75000_00,
            fixed_expenses_paise=25000_00,
            currency="INR",
            is_onboarding_complete=True,
        )
        session.add(user)
        session.flush()

        cat_food = Category(user_id=user.id, name="Food & Dining", color="#FF6B6B", icon="food")
        cat_tech = Category(user_id=user.id, name="Tech & Gadgets", color="#45B7D1", icon="laptop")
        session.add_all([cat_food, cat_tech])
        session.flush()

        # Add income and expense in current month
        t_inc = Transaction(
            user_id=user.id,
            transaction_type=TransactionType.INCOME,
            amount_paise=75000_00,
            transaction_date=date.today(),
            description="Salary",
        )
        t_exp1 = Transaction(
            user_id=user.id,
            transaction_type=TransactionType.EXPENSE,
            amount_paise=4000_00,
            category_id=cat_food.id,
            transaction_date=date.today(),
            description="Restaurant dinner",
        )
        t_exp2 = Transaction(
            user_id=user.id,
            transaction_type=TransactionType.EXPENSE,
            amount_paise=15000_00,
            category_id=cat_tech.id,
            transaction_date=date.today(),
            description="External Monitor",
        )
        session.add_all([t_inc, t_exp1, t_exp2])
        session.commit()

        return {"user_id": user.id, "cat_food_id": cat_food.id, "cat_tech_id": cat_tech.id}


class TestAIService:

    def test_predict_categories_offline_fallback(self):
        service = AIService(api_key=None)
        assert service.is_configured() is False

        suggestions = service.predict_categories(profession="Developer")
        assert len(suggestions) > 0
        names = [s["name"] for s in suggestions]
        assert "Food" in names
        assert "Technology" in names

    def test_predict_categories_with_gemini_mock(self):
        service = AIService(api_key="MOCK_KEY")
        service._client = MagicMock()

        mock_json_response = json.dumps([
            {
                "name": "Cloud Infrastructure",
                "icon": "laptop",
                "color": "#45B7D1",
                "subcategories": ["AWS", "Vercel", "Domains"],
            },
            {
                "name": "Specialty Coffee",
                "icon": "food",
                "color": "#FF6B6B",
                "subcategories": ["Beans", "Cafes"],
            },
        ])

        mock_response = MagicMock()
        mock_response.text = mock_json_response
        service._client.models.generate_content.return_value = mock_response

        categories = service.predict_categories(
            profession="Software Engineer",
            monthly_income_str="120000",
        )

        assert len(categories) == 2
        assert categories[0]["name"] == "Cloud Infrastructure"
        assert categories[0]["subcategories"] == ["AWS", "Vercel", "Domains"]
        assert categories[1]["name"] == "Specialty Coffee"

    def test_gather_financial_context(self, ai_seed_user):
        service = AIService(api_key=None)
        user_id = ai_seed_user["user_id"]

        ctx = service._gather_financial_context(user_id)

        assert ctx["user_name"] == "Alex"
        assert ctx["currency"] == "INR"
        assert ctx["currency_sym"] == "₹"
        assert ctx["cur_income_paise"] == 75000_00
        assert ctx["cur_expense_paise"] == 19000_00  # 4k food + 15k tech
        assert ctx["cur_net_paise"] == 56000_00  # 75k - 19k = 56k
        assert ctx["cur_status"] == "GAIN"
        assert "Tech & Gadgets" in ctx["top_category"]
        assert "External Monitor" in ctx["largest_purchase"]

    def test_local_financial_assistant_queries(self, ai_seed_user):
        service = AIService(api_key=None)
        user_id = ai_seed_user["user_id"]

        # 1. Expense query
        ans_spend = service.query_financial_assistant(user_id, "How much did I spend this month?")
        assert "₹190.00" in ans_spend or "19,000" in ans_spend or "19000" in ans_spend
        assert "Tech & Gadgets" in ans_spend

        # 2. Income query
        ans_income = service.query_financial_assistant(user_id, "What is my income so far?")
        assert "75,000" in ans_income or "75000" in ans_income

        # 3. Surplus / Deficit check
        ans_surplus = service.query_financial_assistant(user_id, "Am I spending more than I earn?")
        assert "surplus" in ans_surplus.lower() or "gain" in ans_surplus.lower()

        # 4. Top category check
        ans_cat = service.query_financial_assistant(user_id, "Where is most of my money going?")
        assert "Tech & Gadgets" in ans_cat

    def test_gemini_assistant_query_with_mock(self, ai_seed_user):
        service = AIService(api_key="MOCK_KEY")
        service._client = MagicMock()

        mock_resp = MagicMock()
        mock_resp.text = "You have saved ₹56,000 this month, which is 74.6% of your income! Great job."
        service._client.models.generate_content.return_value = mock_resp

        user_id = ai_seed_user["user_id"]
        result = service.query_financial_assistant(user_id, "How are my savings looking?")

        assert "₹56,000" in result
        service._client.models.generate_content.assert_called_once()
        # Verify system instruction was passed and contains ground truth
        call_kwargs = service._client.models.generate_content.call_args[1]
        cfg = call_kwargs["config"]
        assert "VERIFIED FINANCIAL DATA" in cfg.system_instruction
        assert "Alex" in cfg.system_instruction

