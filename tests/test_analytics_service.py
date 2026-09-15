"""
Spendora — Tests for AnalyticsService.

Validates analytical computations across arbitrary date ranges:
- Period performance and preceding window calculations
- Period-over-period deltas and percentage change metrics
- Category spending distribution and exact share calculations
- Daily time series generation
- Financial insights extraction (peak day, largest purchase, average size)
- Boundary and edge case handling
"""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import patch
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.models import Base, Category, Transaction, TransactionType, User
from services.analytics_service import AnalyticsService


@pytest.fixture(scope="function")
def analytics_test_db():
    """Isolated SQLite database in-memory for AnalyticsService testing."""
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

    with patch("services.analytics_service.get_session", side_effect=mock_get_session), \
         patch("services.calculation_service.get_session", side_effect=mock_get_session):
        yield Session

    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def analytics_seed_data(analytics_test_db):
    """Seed multi-period data for analytics testing."""
    Session = analytics_test_db
    with Session() as session:
        user = User(
            name="Diana",
            profession="Doctor",
            currency="INR",
            is_onboarding_complete=True,
        )
        session.add(user)
        session.flush()

        cat_food = Category(user_id=user.id, name="Food", color="#FF5722", icon="food")
        cat_tech = Category(user_id=user.id, name="Tech", color="#2196F3", icon="laptop")
        cat_health = Category(user_id=user.id, name="Health", color="#4CAF50", icon="heart-pulse")
        session.add_all([cat_food, cat_tech, cat_health])
        session.flush()

        # Prior Period: 2026-08-01 to 2026-08-10 (10 days)
        # Income: ₹50,000 | Expenses: ₹10,000 (Food: 6k, Tech: 4k)
        t1 = Transaction(
            user_id=user.id,
            transaction_type=TransactionType.INCOME,
            amount_paise=50000_00,
            transaction_date=date(2026, 8, 1),
            description="August Salary",
        )
        t2 = Transaction(
            user_id=user.id,
            transaction_type=TransactionType.EXPENSE,
            amount_paise=6000_00,
            category_id=cat_food.id,
            transaction_date=date(2026, 8, 3),
            description="August Groceries",
        )
        t3 = Transaction(
            user_id=user.id,
            transaction_type=TransactionType.EXPENSE,
            amount_paise=4000_00,
            category_id=cat_tech.id,
            transaction_date=date(2026, 8, 5),
            description="Software subscription",
        )

        # Current Period: 2026-08-11 to 2026-08-20 (10 days)
        # Income: ₹20,000
        # Expenses:
        # 2026-08-12: Food ₹2,000
        # 2026-08-15: Health ₹15,000 (Largest single purchase & Peak Day!)
        # 2026-08-15: Food ₹1,000
        # 2026-08-18: Uncategorized ₹2,000
        # Total current expenses = 20,000_00 (Food: 3k, Health: 15k, Uncategorized: 2k)
        t4 = Transaction(
            user_id=user.id,
            transaction_type=TransactionType.INCOME,
            amount_paise=20000_00,
            transaction_date=date(2026, 8, 11),
            description="Bonus",
        )
        t5 = Transaction(
            user_id=user.id,
            transaction_type=TransactionType.EXPENSE,
            amount_paise=2000_00,
            category_id=cat_food.id,
            transaction_date=date(2026, 8, 12),
            description="Dinner out",
        )
        t6 = Transaction(
            user_id=user.id,
            transaction_type=TransactionType.EXPENSE,
            amount_paise=15000_00,
            category_id=cat_health.id,
            transaction_date=date(2026, 8, 15),
            description="Medical Equipment",
        )
        t7 = Transaction(
            user_id=user.id,
            transaction_type=TransactionType.EXPENSE,
            amount_paise=1000_00,
            category_id=cat_food.id,
            transaction_date=date(2026, 8, 15),
            description="Pharmacy snacks",
        )
        t8 = Transaction(
            user_id=user.id,
            transaction_type=TransactionType.EXPENSE,
            amount_paise=2000_00,
            category_id=None,  # Uncategorized
            transaction_date=date(2026, 8, 18),
            description="Cash withdrawal",
        )

        session.add_all([t1, t2, t3, t4, t5, t6, t7, t8])
        session.commit()

        return {
            "user_id": user.id,
            "cat_food_id": cat_food.id,
            "cat_tech_id": cat_tech.id,
            "cat_health_id": cat_health.id,
        }


class TestAnalyticsService:

    def test_calculate_date_range_performance(self, analytics_seed_data):
        service = AnalyticsService()
        user_id = analytics_seed_data["user_id"]

        # Current window: 10 days (2026-08-11 to 2026-08-20)
        # Preceding window should automatically be 2026-08-01 to 2026-08-10 (10 days)
        start = date(2026, 8, 11)
        end = date(2026, 8, 20)

        perf = service.calculate_date_range_performance(user_id, start, end)

        assert perf["days_count"] == 10
        assert perf["previous_period_range"] == (date(2026, 8, 1), date(2026, 8, 10))

        cur = perf["current"]
        assert cur["total_income_paise"] == 20000_00
        assert cur["total_expenses_paise"] == 20000_00
        assert cur["net_paise"] == 0
        assert cur["status"] == "BREAK-EVEN"

        prev = perf["previous"]
        assert prev["total_income_paise"] == 50000_00
        assert prev["total_expenses_paise"] == 10000_00
        assert prev["net_paise"] == 40000_00

        # Deltas
        deltas = perf["deltas"]
        # Expenses went up from 10,000 to 20,000 (+100.0%)
        assert deltas["expense_delta_paise"] == 10000_00
        assert deltas["expense_pct_change"] == 100.0

        # Income went down from 50,000 to 20,000 (-60.0%)
        assert deltas["income_delta_paise"] == -30000_00
        assert deltas["income_pct_change"] == -60.0

    def test_calculate_date_range_performance_invalid_dates(self, analytics_seed_data):
        service = AnalyticsService()
        user_id = analytics_seed_data["user_id"]
        with pytest.raises(ValueError, match="must not be after end date"):
            service.calculate_date_range_performance(user_id, date(2026, 8, 20), date(2026, 8, 10))

    def test_get_category_spending_distribution(self, analytics_seed_data):
        service = AnalyticsService()
        user_id = analytics_seed_data["user_id"]

        start = date(2026, 8, 11)
        end = date(2026, 8, 20)

        # Total expenses in this period:
        # Health: ₹15,000 (75.0%)
        # Food: ₹3,000 (15.0%)
        # Uncategorized: ₹2,000 (10.0%)
        dist = service.get_category_spending_distribution(user_id, start, end)

        assert len(dist) == 3
        # Sorted descending by amount
        assert dist[0]["name"] == "Health"
        assert dist[0]["amount_paise"] == 15000_00
        assert dist[0]["percentage"] == 75.0
        assert dist[0]["transaction_count"] == 1

        assert dist[1]["name"] == "Food"
        assert dist[1]["amount_paise"] == 3000_00
        assert dist[1]["percentage"] == 15.0
        assert dist[1]["transaction_count"] == 2

        assert dist[2]["name"] == "Uncategorized"
        assert dist[2]["amount_paise"] == 2000_00
        assert dist[2]["percentage"] == 10.0
        assert dist[2]["transaction_count"] == 1

    def test_get_category_spending_distribution_empty_period(self, analytics_seed_data):
        service = AnalyticsService()
        user_id = analytics_seed_data["user_id"]

        start = date(2026, 9, 1)
        end = date(2026, 9, 10)

        dist = service.get_category_spending_distribution(user_id, start, end)
        assert dist == []

    def test_get_time_series_trend(self, analytics_seed_data):
        service = AnalyticsService()
        user_id = analytics_seed_data["user_id"]

        start = date(2026, 8, 11)
        end = date(2026, 8, 15)  # 5 days

        series = service.get_time_series_trend(user_id, start, end)
        assert len(series) == 5

        # Aug 11: Income 20,000
        s11 = next(s for s in series if s["date"] == date(2026, 8, 11))
        assert s11["income_paise"] == 20000_00
        assert s11["expense_paise"] == 0

        # Aug 12: Expense 2,000
        s12 = next(s for s in series if s["date"] == date(2026, 8, 12))
        assert s12["income_paise"] == 0
        assert s12["expense_paise"] == 2000_00

        # Aug 13: Zero
        s13 = next(s for s in series if s["date"] == date(2026, 8, 13))
        assert s13["income_paise"] == 0
        assert s13["expense_paise"] == 0

        # Aug 15: Expense 16,000 (15,000 health + 1,000 food)
        s15 = next(s for s in series if s["date"] == date(2026, 8, 15))
        assert s15["expense_paise"] == 16000_00

    def test_get_spending_insights(self, analytics_seed_data):
        service = AnalyticsService()
        user_id = analytics_seed_data["user_id"]

        start = date(2026, 8, 11)
        end = date(2026, 8, 20)

        insights = service.get_spending_insights(user_id, start, end)

        # Top category: Health (15,000)
        assert insights["top_category_name"] == "Health"
        assert insights["top_category_paise"] == 15000_00

        # Peak day: Aug 15 with ₹16,000 total expenses
        assert insights["peak_day"] == date(2026, 8, 15)
        assert insights["peak_day_amount_paise"] == 16000_00

        # Largest single purchase: Medical Equipment (₹15,000)
        largest = insights["largest_expense"]
        assert largest is not None
        assert largest["description"] == "Medical Equipment"
        assert largest["amount_paise"] == 15000_00
        assert largest["category_name"] == "Health"

        # 4 expense transactions, total = 20,000_00 -> average = 5,000_00
        assert insights["expense_transaction_count"] == 4
        assert insights["average_transaction_paise"] == 5000_00

    def test_get_spending_insights_empty_period(self, analytics_seed_data):
        service = AnalyticsService()
        user_id = analytics_seed_data["user_id"]

        start = date(2026, 9, 1)
        end = date(2026, 9, 10)

        insights = service.get_spending_insights(user_id, start, end)

        assert insights["top_category_name"] is None
        assert insights["top_category_paise"] == 0
        assert insights["peak_day"] is None
        assert insights["peak_day_amount_paise"] == 0
        assert insights["largest_expense"] is None
        assert insights["expense_transaction_count"] == 0
        assert insights["average_transaction_paise"] == 0

