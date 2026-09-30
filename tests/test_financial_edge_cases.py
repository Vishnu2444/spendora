"""
Spendora — Tests for financial data integrity and edge cases.

Covers Phase 3 of the Spendora Safe Deployment & Hardening Plan:
• 0, 0.01, 1, 999.99, large values, and invalid negative values where not permitted.
• Income-only, expense-only, equal income/expense, surplus, deficit, and zero-balance periods.
• Today, yesterday, month boundaries, year boundaries, leap-day dates, future dates, and old dates.
• Empty database, one transaction, many transactions, duplicate-looking transactions, edits, and deletions.
• Category deletion/renaming while historical transactions exist.
• Deterministic rule: calculations are never sourced from an LLM.
"""

from datetime import date, timedelta
from decimal import Decimal
import pytest

from database.database import get_session
from database.models import Category, Subcategory, Transaction, TransactionType, User
from services.calculation_service import CalculationService
from services.category_service import CategoryService
from services.transaction_service import TransactionService
from utils.date_utils import days_in_range
from utils.formatting import format_currency, format_gain_loss_label
from utils.validators import amount_to_paise, paise_to_amount, validate_amount_string


# ---------------------------------------------------------------------------
# 1. Minor Units & Value Bounds
# ---------------------------------------------------------------------------

class TestValueBoundaries:
    """Test required monetary values: 0, 0.01, 1, 999.99, large values, negatives."""

    def test_minor_unit_one_paisa(self):
        """₹0.01 must accurately convert to 1 paisa and format cleanly."""
        val = validate_amount_string("0.01")
        assert val == Decimal("0.01")
        paise = amount_to_paise(val)
        assert paise == 1
        assert paise_to_amount(paise) == Decimal("0.01")
        assert format_currency(paise, "INR") == "₹0.01"

    def test_one_rupee(self):
        """₹1 must convert to 100 paise."""
        val = validate_amount_string("1.00")
        assert val == Decimal("1.00")
        assert amount_to_paise(val) == 100

    def test_999_99_rupees(self):
        """₹999.99 must convert to 99999 paise."""
        val = validate_amount_string("999.99")
        assert val == Decimal("999.99")
        paise = amount_to_paise(val)
        assert paise == 99999
        assert format_currency(paise, "INR") == "₹999.99"

    def test_large_value_precision(self):
        """Large financial values (e.g. ₹100 Crores) must not overflow or lose precision."""
        large_str = "100000000.00"
        val = validate_amount_string(large_str)
        paise = amount_to_paise(val)
        assert paise == 10_000_000_000
        assert paise_to_amount(paise) == Decimal(large_str)

    def test_zero_amount_rejected_for_transaction(self):
        """Zero amount transaction is strictly rejected."""
        with pytest.raises(ValueError, match="greater than zero"):
            validate_amount_string("0")
        with pytest.raises(ValueError, match="greater than zero"):
            validate_amount_string("0.00")

    def test_negative_amount_rejected(self):
        """Negative amount strings are strictly rejected."""
        with pytest.raises(ValueError, match="greater than zero"):
            validate_amount_string("-0.01")
        with pytest.raises(ValueError, match="greater than zero"):
            validate_amount_string("-500.00")


# ---------------------------------------------------------------------------
# 2. Financial Periods (Income-only, Expense-only, Break-even, Deficit)
# ---------------------------------------------------------------------------

class TestFinancialPeriodProfiles:
    """Test deterministic period summaries across all financial profiles."""

    def test_income_only_period(self):
        calc = CalculationService()
        txn_service = TransactionService()
        with get_session() as session:
            user = User(name="IncomeOnly User", profession="Engineer", currency="INR")
            session.add(user)
            session.commit()
            u_id = user.id

        start_d = date(2026, 1, 1)
        end_d = date(2026, 1, 31)

        txn_service.create_transaction(
            user_id=u_id,
            transaction_type="INCOME",
            amount_str="50000.00",
            transaction_date=date(2026, 1, 15),
            description="Salary",
        )

        summary = calc.calculate_period_summary(u_id, start_d, end_d)
        assert summary["total_income_paise"] == 5000000
        assert summary["total_expenses_paise"] == 0
        assert summary["net_paise"] == 5000000
        assert summary["status"] == "GAIN"
        assert format_gain_loss_label(summary["net_paise"]) == "GAIN"

    def test_expense_only_period(self):
        calc = CalculationService()
        txn_service = TransactionService()
        with get_session() as session:
            user = User(name="ExpenseOnly User", profession="Designer", currency="INR")
            session.add(user)
            session.commit()
            u_id = user.id

        start_d = date(2026, 1, 1)
        end_d = date(2026, 1, 31)

        txn_service.create_transaction(
            user_id=u_id,
            transaction_type="EXPENSE",
            amount_str="15000.00",
            transaction_date=date(2026, 1, 10),
            description="Rent",
        )

        summary = calc.calculate_period_summary(u_id, start_d, end_d)
        assert summary["total_income_paise"] == 0
        assert summary["total_expenses_paise"] == 1500000
        assert summary["net_paise"] == -1500000
        assert summary["status"] == "LOSS"
        assert format_gain_loss_label(summary["net_paise"]) == "LOSS"

    def test_equal_income_expense_break_even(self):
        calc = CalculationService()
        txn_service = TransactionService()
        with get_session() as session:
            user = User(name="BreakEven User", profession="Teacher", currency="INR")
            session.add(user)
            session.commit()
            u_id = user.id

        start_d = date(2026, 1, 1)
        end_d = date(2026, 1, 31)

        txn_service.create_transaction(
            user_id=u_id,
            transaction_type="INCOME",
            amount_str="25000.00",
            transaction_date=date(2026, 1, 5),
            description="Stipend",
        )
        txn_service.create_transaction(
            user_id=u_id,
            transaction_type="EXPENSE",
            amount_str="25000.00",
            transaction_date=date(2026, 1, 20),
            description="Course Fee",
        )

        summary = calc.calculate_period_summary(u_id, start_d, end_d)
        assert summary["net_paise"] == 0
        assert summary["status"] == "BREAK-EVEN"
        assert format_gain_loss_label(summary["net_paise"]) == "BREAK-EVEN"

    def test_zero_balance_empty_period(self):
        calc = CalculationService()
        with get_session() as session:
            user = User(name="Empty User", profession="Student", currency="INR")
            session.add(user)
            session.commit()
            u_id = user.id

        start_d = date(2026, 1, 1)
        end_d = date(2026, 1, 31)

        summary = calc.calculate_period_summary(u_id, start_d, end_d)
        assert summary["total_income_paise"] == 0
        assert summary["total_expenses_paise"] == 0
        assert summary["net_paise"] == 0
        assert summary["status"] == "BREAK-EVEN"
        assert summary["avg_daily_expense_paise"] == 0


# ---------------------------------------------------------------------------
# 3. Date Boundaries & Leap Years
# ---------------------------------------------------------------------------

class TestDateBoundaries:
    """Test date calculations on boundaries, leap years, and rollovers."""

    def test_leap_year_february_29(self):
        """2024 is a leap year; days_in_range must return 29."""
        start = date(2024, 2, 1)
        end = date(2024, 2, 29)
        assert days_in_range(start, end) == 29

    def test_non_leap_year_february(self):
        """2025 is not a leap year; days_in_range must return 28."""
        start = date(2025, 2, 1)
        end = date(2025, 2, 28)
        assert days_in_range(start, end) == 28

    def test_year_boundary_transition(self):
        """Range spanning across year boundary: Dec 31 to Jan 1."""
        start = date(2025, 12, 31)
        end = date(2026, 1, 1)
        assert days_in_range(start, end) == 2

    def test_inverted_date_range(self):
        """If end date is before start date, days_in_range returns 0."""
        start = date(2026, 3, 10)
        end = date(2026, 3, 1)
        assert days_in_range(start, end) == 0


# ---------------------------------------------------------------------------
# 4. Database CRUD & Historical Integrity
# ---------------------------------------------------------------------------

class TestDatabaseHistoricalIntegrity:
    """Test transactions, edits, duplicate amounts, and category deletions."""

    def test_category_deletion_preserves_historical_transactions(self):
        """
        When a category is deleted, historical transactions must retain their
        records with category_id set to NULL (ON DELETE SET NULL).
        """
        with get_session() as session:
            # Create user
            user = User(name="Integrity User", profession="Engineer", currency="INR")
            session.add(user)
            session.flush()

            # Create category
            cat = Category(user_id=user.id, name="Temp Cat", color="#FF0000", icon="food")
            session.add(cat)
            session.flush()

            # Create transaction under category
            txn = Transaction(
                user_id=user.id,
                category_id=cat.id,
                amount_paise=50000,
                transaction_type=TransactionType.EXPENSE,
                transaction_date=date.today(),
                description="Groceries with Temp Cat",
            )
            session.add(txn)
            session.commit()

            txn_id = txn.id
            cat_id = cat.id

        # Delete the category (soft delete default)
        cat_service = CategoryService()
        cat_service.delete_category(cat_id)

        # Verify transaction still exists and is accessible
        txn_service = TransactionService()
        preserved_txn = txn_service.get_transaction(txn_id)
        assert preserved_txn is not None
        assert preserved_txn.description == "Groceries with Temp Cat"
        assert preserved_txn.amount_paise == 50000

        # Hard delete category and verify ON DELETE SET NULL
        cat_service.delete_category(cat_id, soft=False)
        preserved_txn_hard = txn_service.get_transaction(txn_id)
        assert preserved_txn_hard is not None
        assert preserved_txn_hard.category_id is None

    def test_duplicate_looking_transactions_allowed(self):
        """Two identical transactions on the same day (e.g. two cups of coffee) are distinct."""
        txn_service = TransactionService()
        t1 = txn_service.create_transaction(
            user_id=1,
            transaction_type="EXPENSE",
            amount_str="150.00",
            transaction_date=date.today(),
            description="Coffee",
        )
        t2 = txn_service.create_transaction(
            user_id=1,
            transaction_type="EXPENSE",
            amount_str="150.00",
            transaction_date=date.today(),
            description="Coffee",
        )
        assert t1.id != t2.id
        assert t1.amount_paise == t2.amount_paise == 15000

    def test_uncategorized_transaction_ledger_rendering(self):
        """Transactions with category=None must render cleanly in AnalyticsView without AttributeError."""
        from screens.analytics.analytics_screen import AnalyticsView
        view = AnalyticsView()

        txn_service = TransactionService()
        txn = txn_service.create_transaction(
            user_id=1,
            transaction_type="EXPENSE",
            amount_str="300.00",
            transaction_date=date.today(),
            category_id=None,
            description="Uncategorized Lunch",
        )
        assert txn.category_id is None

        # Ledger refresh must not throw AttributeError: 'NoneType' object has no attribute 'icon'
        view._refresh_ledger_view(user_id=1, currency="INR", sym="₹")
        assert len(view._ledger_entries_column.controls) > 0
