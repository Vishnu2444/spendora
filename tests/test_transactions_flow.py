"""
Spendora — End-to-end integration test for Phase 2 Transactions & Calculations Flow.

Tests the full lifecycle:
1. User profile creation and category setup
2. Adding income and expense transactions
3. Deterministic calculation of period summary and all-time balances
4. Searching and filtering transactions
5. Updating transactions and verifying recomputed balances
6. Deleting transactions and verifying recomputed balances
"""

from __future__ import annotations

from datetime import date
from unittest.mock import patch
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.models import Base
from services.calculation_service import CalculationService
from services.category_service import CategoryService
from services.profile_service import ProfileService
from services.transaction_service import TransactionService


@pytest.fixture(scope="function")
def e2e_db():
    """Isolated SQLite database in-memory for E2E flow testing."""
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

    with patch("services.profile_service.get_session", side_effect=mock_get_session), \
         patch("services.category_service.get_session", side_effect=mock_get_session), \
         patch("services.transaction_service.get_session", side_effect=mock_get_session), \
         patch("services.calculation_service.get_session", side_effect=mock_get_session):
        yield Session

    Base.metadata.drop_all(engine)
    engine.dispose()


def test_full_phase2_transaction_and_calculation_flow(e2e_db):
    profile_service = ProfileService()
    cat_service = CategoryService()
    txn_service = TransactionService()
    calc_service = CalculationService()

    # Step 1: Create user profile and categories
    user = profile_service.create_user(
        name="Vishnu",
        profession="Software Engineer",
        monthly_income_str="80000",
        currency="INR",
    )
    profile_service.mark_onboarding_complete(user.id)

    food_cat = cat_service.create_category(user.id, "Food & Dining")
    rent_cat = cat_service.create_category(user.id, "Rent & Housing")
    tech_cat = cat_service.create_category(user.id, "Technology")

    # Step 2: Add transactions across two months (August & September 2026)
    # Aug 25: Income ₹80,000 (salary)
    txn_service.create_transaction(
        user_id=user.id,
        transaction_type="INCOME",
        amount_str="80000.00",
        transaction_date=date(2026, 8, 25),
        description="August Monthly Salary",
    )
    # Aug 26: Rent expense ₹25,000
    txn_service.create_transaction(
        user_id=user.id,
        transaction_type="EXPENSE",
        amount_str="25000.00",
        transaction_date=date(2026, 8, 26),
        category_id=rent_cat.id,
        description="Apartment rent for August",
    )

    # Balance as of end of August should be +₹55,000 (5,500,000 paise)
    aug_summary = calc_service.calculate_period_summary(
        user_id=user.id,
        start_date=date(2026, 8, 1),
        end_date=date(2026, 8, 31),
    )
    assert aug_summary["total_income_paise"] == 80000_00
    assert aug_summary["total_expenses_paise"] == 25000_00
    assert aug_summary["net_paise"] == 55000_00
    assert aug_summary["status"] == "GAIN"
    assert aug_summary["opening_balance_paise"] == 0
    assert aug_summary["closing_balance_paise"] == 55000_00

    # Step 3: September transactions
    # Sept 1: Groceries ₹3,200.50
    t_groc = txn_service.create_transaction(
        user_id=user.id,
        transaction_type="EXPENSE",
        amount_str="3200.50",
        transaction_date=date(2026, 9, 1),
        category_id=food_cat.id,
        description="Fresh supermarket groceries",
    )
    # Sept 5: Keyboard purchase ₹4,500.00
    t_kb = txn_service.create_transaction(
        user_id=user.id,
        transaction_type="EXPENSE",
        amount_str="4500.00",
        transaction_date=date(2026, 9, 5),
        category_id=tech_cat.id,
        description="Mechanical keyboard for coding",
    )
    # Sept 10: Freelance income ₹15,000.00
    t_free = txn_service.create_transaction(
        user_id=user.id,
        transaction_type="INCOME",
        amount_str="15000.00",
        transaction_date=date(2026, 9, 10),
        description="Freelance bug fix",
    )

    # Step 4: Verify September calculations
    sept_summary = calc_service.calculate_period_summary(
        user_id=user.id,
        start_date=date(2026, 9, 1),
        end_date=date(2026, 9, 30),
    )
    # Opening balance should equal closing balance from August (+₹55,000)
    assert sept_summary["opening_balance_paise"] == 55000_00
    assert sept_summary["total_income_paise"] == 15000_00
    assert sept_summary["total_expenses_paise"] == 7700_50
    assert sept_summary["net_paise"] == 7299_50
    assert sept_summary["status"] == "GAIN"
    # Closing balance: 55,000 + 7,299.50 = 62,299.50
    assert sept_summary["closing_balance_paise"] == 62299_50
    assert sept_summary["transaction_count"] == 3

    # All-time balance check
    all_time = calc_service.calculate_current_balance(user.id)
    assert all_time == 62299_50

    # Step 5: Test search and filters
    search_keyboard = txn_service.list_transactions(user_id=user.id, search_term="keyboard")
    assert len(search_keyboard) == 1
    assert search_keyboard[0].id == t_kb.id

    expense_only = txn_service.list_transactions(
        user_id=user.id,
        start_date=date(2026, 9, 1),
        end_date=date(2026, 9, 30),
        transaction_type="EXPENSE",
    )
    assert len(expense_only) == 2

    # Step 6: Update transaction (keyboard discounted to ₹4,000.00)
    txn_service.update_transaction(
        transaction_id=t_kb.id,
        user_id=user.id,
        amount_str="4000.00",
        description="Mechanical keyboard (discount applied)",
    )

    # Recheck Sept summary after update
    sept_updated = calc_service.calculate_period_summary(
        user_id=user.id,
        start_date=date(2026, 9, 1),
        end_date=date(2026, 9, 30),
    )
    # Expenses went down by ₹500 (50,000 paise): 7,700.50 -> 7,200.50
    assert sept_updated["total_expenses_paise"] == 7200_50
    assert sept_updated["net_paise"] == 7799_50
    assert sept_updated["closing_balance_paise"] == 62799_50

    # Step 7: Delete transaction (remove groceries)
    txn_service.delete_transaction(transaction_id=t_groc.id, user_id=user.id)

    # Recheck Sept summary after deletion
    sept_post_delete = calc_service.calculate_period_summary(
        user_id=user.id,
        start_date=date(2026, 9, 1),
        end_date=date(2026, 9, 30),
    )
    assert sept_post_delete["total_expenses_paise"] == 4000_00
    assert sept_post_delete["net_paise"] == 11000_00
    assert sept_post_delete["closing_balance_paise"] == 66000_00
    assert sept_post_delete["transaction_count"] == 2
