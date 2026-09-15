"""
Spendora — Tests for CalculationService.

Validates deterministic arithmetic on integer paise:
- Period summaries (income, expense, net, status)
- Opening and closing balance calculations
- Daily average expense
- Status determination (GAIN, LOSS, BREAK-EVEN)
- Top expense categories breakdown
- All-time balance calculation
- Edge cases (empty periods, single-day periods, inverted dates)
"""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import patch
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.models import Base, Category, Transaction, TransactionType, User
from services.calculation_service import CalculationService


@pytest.fixture(scope="function")
def calc_test_db():
    """Isolated SQLite database in-memory for CalculationService testing."""
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

    with patch("services.calculation_service.get_session", side_effect=mock_get_session):
        yield Session

    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def sample_data(calc_test_db):
    """Seed sample user, categories, and transactions."""
    Session = calc_test_db
    with Session() as session:
        user = User(
            name="Test User",
            profession="Software Engineer",
            currency="INR",
            is_onboarding_complete=True,
        )
        session.add(user)
        session.flush()

        cat_food = Category(user_id=user.id, name="Food")
        cat_tech = Category(user_id=user.id, name="Technology")
        cat_transport = Category(user_id=user.id, name="Transport")
        session.add_all([cat_food, cat_tech, cat_transport])
        session.flush()

        # Prior period transactions (before 2026-09-01)
        # Net before Sept 1: +50,000 income - 20,000 expense = +30,000 paise
        t_prior_inc = Transaction(
            user_id=user.id,
            transaction_type=TransactionType.INCOME,
            amount_paise=50000_00,  # ₹50,000
            transaction_date=date(2026, 8, 15),
            description="August Salary",
        )
        t_prior_exp = Transaction(
            user_id=user.id,
            transaction_type=TransactionType.EXPENSE,
            amount_paise=20000_00,  # ₹20,000
            transaction_date=date(2026, 8, 20),
            category_id=cat_tech.id,
            description="Laptop Monitor",
        )

        # Current period transactions (2026-09-01 to 2026-09-10)
        t_cur_inc = Transaction(
            user_id=user.id,
            transaction_type=TransactionType.INCOME,
            amount_paise=10000_00,  # ₹10,000
            transaction_date=date(2026, 9, 1),
            description="Freelance project",
        )
        t_cur_exp1 = Transaction(
            user_id=user.id,
            transaction_type=TransactionType.EXPENSE,
            amount_paise=3000_00,  # ₹3,000
            category_id=cat_food.id,
            transaction_date=date(2026, 9, 2),
            description="Groceries",
        )
        t_cur_exp2 = Transaction(
            user_id=user.id,
            transaction_type=TransactionType.EXPENSE,
            amount_paise=1500_00,  # ₹1,500
            category_id=cat_transport.id,
            transaction_date=date(2026, 9, 5),
            description="Fuel",
        )
        t_cur_exp3 = Transaction(
            user_id=user.id,
            transaction_type=TransactionType.EXPENSE,
            amount_paise=500_00,  # ₹500
            category_id=cat_food.id,
            transaction_date=date(2026, 9, 8),
            description="Snacks",
        )

        session.add_all([t_prior_inc, t_prior_exp, t_cur_inc, t_cur_exp1, t_cur_exp2, t_cur_exp3])
        session.commit()

        return {
            "user_id": user.id,
            "cat_food_id": cat_food.id,
            "cat_tech_id": cat_tech.id,
            "cat_transport_id": cat_transport.id,
        }


class TestCalculationService:

    def test_calculate_period_summary_gain(self, sample_data):
        service = CalculationService()
        user_id = sample_data["user_id"]

        # Range: 2026-09-01 to 2026-09-10 (10 days inclusive)
        start = date(2026, 9, 1)
        end = date(2026, 9, 10)

        summary = service.calculate_period_summary(user_id, start, end)

        # Total income in Sept: 10,000.00
        assert summary["total_income_paise"] == 10000_00

        # Total expenses in Sept: 3000 + 1500 + 500 = 5,000.00
        assert summary["total_expenses_paise"] == 5000_00

        # Net: 10,000 - 5,000 = 5,000.00 (GAIN)
        assert summary["net_paise"] == 5000_00
        assert summary["status"] == "GAIN"

        # Opening balance before Sept 1: 50,000 - 20,000 = 30,000.00
        assert summary["opening_balance_paise"] == 30000_00

        # Closing balance: 30,000 + 5,000 = 35,000.00
        assert summary["closing_balance_paise"] == 35000_00

        # Average daily expense: 5,000 / 10 days = 500.00 paise
        assert summary["avg_daily_expense_paise"] == 500_00

        # Count: 1 income + 3 expenses = 4 transactions
        assert summary["transaction_count"] == 4

    def test_calculate_period_summary_loss(self, sample_data):
        service = CalculationService()
        user_id = sample_data["user_id"]

        # Period with expenses only: Sept 2 to Sept 8
        start = date(2026, 9, 2)
        end = date(2026, 9, 8)

        summary = service.calculate_period_summary(user_id, start, end)

        assert summary["total_income_paise"] == 0
        assert summary["total_expenses_paise"] == 5000_00
        assert summary["net_paise"] == -5000_00
        assert summary["status"] == "LOSS"

    def test_calculate_period_summary_break_even(self, sample_data):
        service = CalculationService()
        user_id = sample_data["user_id"]

        # A period with no transactions
        start = date(2026, 9, 15)
        end = date(2026, 9, 20)

        summary = service.calculate_period_summary(user_id, start, end)

        assert summary["total_income_paise"] == 0
        assert summary["total_expenses_paise"] == 0
        assert summary["net_paise"] == 0
        assert summary["status"] == "BREAK-EVEN"
        assert summary["transaction_count"] == 0
        assert summary["avg_daily_expense_paise"] == 0

    def test_calculate_period_summary_invalid_date_range(self, sample_data):
        service = CalculationService()
        user_id = sample_data["user_id"]

        start = date(2026, 9, 10)
        end = date(2026, 9, 1)

        with pytest.raises(ValueError, match="must not be after end date"):
            service.calculate_period_summary(user_id, start, end)

    def test_calculate_current_balance(self, sample_data):
        service = CalculationService()
        user_id = sample_data["user_id"]

        # All-time net:
        # Aug: +50,000 - 20,000 = +30,000
        # Sept: +10,000 - 5,000 = +5,000
        # Total = 35,000.00
        balance = service.calculate_current_balance(user_id)
        assert balance == 35000_00

    def test_get_top_expense_categories(self, sample_data):
        service = CalculationService()
        user_id = sample_data["user_id"]

        # All of Sept: Food (3000 + 500 = 3500), Transport (1500)
        start = date(2026, 9, 1)
        end = date(2026, 9, 30)

        top_cats = service.get_top_expense_categories(user_id, start, end, limit=5)

        assert len(top_cats) == 2
        assert top_cats[0] == ("Food", 3500_00)
        assert top_cats[1] == ("Transport", 1500_00)

    def test_get_top_expense_categories_limit(self, sample_data):
        service = CalculationService()
        user_id = sample_data["user_id"]

        start = date(2026, 9, 1)
        end = date(2026, 9, 30)

        top_cats = service.get_top_expense_categories(user_id, start, end, limit=1)

        assert len(top_cats) == 1
        assert top_cats[0][0] == "Food"
