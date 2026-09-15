"""
Spendora — Tests for TransactionService.

Validates CRUD operations, business rules, and input validations:
- Creation of income and expenses
- Categorization and subcategorization
- Input constraints (positive amounts, valid dates, ownership)
- Retrieval, filtering, search, and counts
- Update semantics (partial updates, clearing categories)
- Deletion and ownership security
"""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import patch
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.models import Base, Category, Subcategory, Transaction, TransactionType, User
from services.transaction_service import TransactionService


@pytest.fixture(scope="function")
def txn_test_db():
    """Isolated SQLite database in-memory for TransactionService testing."""
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

    with patch("services.transaction_service.get_session", side_effect=mock_get_session):
        yield Session

    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def user_and_categories(txn_test_db):
    """Seed user and categories."""
    Session = txn_test_db
    with Session() as session:
        user = User(
            name="Alice",
            profession="Freelancer",
            currency="INR",
            is_onboarding_complete=True,
        )
        user2 = User(
            name="Bob",
            profession="Doctor",
            currency="INR",
            is_onboarding_complete=True,
        )
        session.add_all([user, user2])
        session.flush()

        cat_food = Category(user_id=user.id, name="Food")
        cat_tech = Category(user_id=user.id, name="Tech")
        cat_bob = Category(user_id=user2.id, name="Medical")
        session.add_all([cat_food, cat_tech, cat_bob])
        session.flush()

        sub_groceries = Subcategory(category_id=cat_food.id, name="Groceries")
        sub_dining = Subcategory(category_id=cat_food.id, name="Dining")
        session.add_all([sub_groceries, sub_dining])
        session.commit()

        return {
            "user_id": user.id,
            "user2_id": user2.id,
            "cat_food_id": cat_food.id,
            "cat_tech_id": cat_tech.id,
            "cat_bob_id": cat_bob.id,
            "sub_groceries_id": sub_groceries.id,
            "sub_dining_id": sub_dining.id,
        }


class TestTransactionService:

    def test_create_transaction_success(self, user_and_categories):
        service = TransactionService()
        u_id = user_and_categories["user_id"]
        cat_id = user_and_categories["cat_food_id"]
        sub_id = user_and_categories["sub_groceries_id"]

        txn = service.create_transaction(
            user_id=u_id,
            transaction_type="EXPENSE",
            amount_str="450.75",
            transaction_date=date(2026, 9, 14),
            category_id=cat_id,
            subcategory_id=sub_id,
            description="Weekly veggies",
            notes="Bought from local vendor",
        )

        assert txn.id is not None
        assert txn.user_id == u_id
        assert txn.transaction_type == TransactionType.EXPENSE
        assert txn.amount_paise == 45075
        assert txn.transaction_date == date(2026, 9, 14)
        assert txn.category_id == cat_id
        assert txn.subcategory_id == sub_id
        assert txn.description == "Weekly veggies"
        assert txn.notes == "Bought from local vendor"

    def test_create_income_transaction(self, user_and_categories):
        service = TransactionService()
        u_id = user_and_categories["user_id"]

        txn = service.create_transaction(
            user_id=u_id,
            transaction_type="INCOME",
            amount_str="10000",
            transaction_date=date(2026, 9, 1),
            description="Consulting fee",
        )

        assert txn.transaction_type == TransactionType.INCOME
        assert txn.amount_paise == 10000_00
        assert txn.category_id is None

    def test_create_transaction_invalid_type(self, user_and_categories):
        service = TransactionService()
        u_id = user_and_categories["user_id"]

        with pytest.raises(ValueError, match="Invalid transaction type"):
            service.create_transaction(
                user_id=u_id,
                transaction_type="INVESTMENT",
                amount_str="500",
                transaction_date=date.today(),
            )

    def test_create_transaction_invalid_amount(self, user_and_categories):
        service = TransactionService()
        u_id = user_and_categories["user_id"]

        with pytest.raises(ValueError, match="not a valid amount"):
            service.create_transaction(
                user_id=u_id,
                transaction_type="EXPENSE",
                amount_str="abc",
                transaction_date=date.today(),
            )

        with pytest.raises(ValueError, match="greater than zero"):
            service.create_transaction(
                user_id=u_id,
                transaction_type="EXPENSE",
                amount_str="-50",
                transaction_date=date.today(),
            )

    def test_create_transaction_far_future_date_rejected(self, user_and_categories):
        service = TransactionService()
        u_id = user_and_categories["user_id"]
        far_future = date.today() + timedelta(days=400)

        with pytest.raises(ValueError, match="more than 1 year in the future"):
            service.create_transaction(
                user_id=u_id,
                transaction_type="EXPENSE",
                amount_str="100",
                transaction_date=far_future,
            )

    def test_create_transaction_other_users_category_rejected(self, user_and_categories):
        service = TransactionService()
        u_id = user_and_categories["user_id"]
        other_cat_id = user_and_categories["cat_bob_id"]

        with pytest.raises(ValueError, match="does not belong to this user"):
            service.create_transaction(
                user_id=u_id,
                transaction_type="EXPENSE",
                amount_str="100",
                transaction_date=date.today(),
                category_id=other_cat_id,
            )

    def test_create_transaction_mismatched_subcategory_rejected(self, user_and_categories):
        service = TransactionService()
        u_id = user_and_categories["user_id"]
        tech_cat_id = user_and_categories["cat_tech_id"]
        food_sub_id = user_and_categories["sub_groceries_id"]

        with pytest.raises(ValueError, match="does not belong to the selected category"):
            service.create_transaction(
                user_id=u_id,
                transaction_type="EXPENSE",
                amount_str="100",
                transaction_date=date.today(),
                category_id=tech_cat_id,
                subcategory_id=food_sub_id,
            )

    def test_get_transaction(self, user_and_categories):
        service = TransactionService()
        u_id = user_and_categories["user_id"]

        txn = service.create_transaction(
            user_id=u_id,
            transaction_type="EXPENSE",
            amount_str="120",
            transaction_date=date(2026, 9, 10),
            description="Coffee",
        )

        fetched = service.get_transaction(txn.id)
        assert fetched is not None
        assert fetched.id == txn.id
        assert fetched.description == "Coffee"

        assert service.get_transaction(99999) is None

    def test_list_and_search_transactions(self, user_and_categories):
        service = TransactionService()
        u_id = user_and_categories["user_id"]

        service.create_transaction(
            user_id=u_id,
            transaction_type="EXPENSE",
            amount_str="100",
            transaction_date=date(2026, 9, 1),
            description="Starbucks coffee",
        )
        service.create_transaction(
            user_id=u_id,
            transaction_type="EXPENSE",
            amount_str="500",
            transaction_date=date(2026, 9, 2),
            description="Book purchase",
            notes="Coffee table book",
        )
        service.create_transaction(
            user_id=u_id,
            transaction_type="INCOME",
            amount_str="2000",
            transaction_date=date(2026, 9, 3),
            description="Refund from vendor",
        )

        # Search matching description
        results = service.list_transactions(user_id=u_id, search_term="coffee")
        assert len(results) == 2  # One with coffee in desc, one with coffee in notes

        # Filter by type
        income_results = service.list_transactions(user_id=u_id, transaction_type="INCOME")
        assert len(income_results) == 1
        assert income_results[0].description == "Refund from vendor"

        # Count
        assert service.count_transactions(user_id=u_id) == 3
        assert service.count_transactions(user_id=u_id, transaction_type="EXPENSE") == 2
        assert service.count_transactions(user_id=u_id, search_term="book") == 1

    def test_get_recent_transactions(self, user_and_categories):
        service = TransactionService()
        u_id = user_and_categories["user_id"]

        for i in range(5):
            service.create_transaction(
                user_id=u_id,
                transaction_type="EXPENSE",
                amount_str=f"10{i}",
                transaction_date=date(2026, 9, 10 + i),
                description=f"Txn {i}",
            )

        recent = service.get_recent_transactions(user_id=u_id, limit=3)
        assert len(recent) == 3
        # Most recent first
        assert recent[0].description == "Txn 4"
        assert recent[1].description == "Txn 3"
        assert recent[2].description == "Txn 2"

    def test_update_transaction(self, user_and_categories):
        service = TransactionService()
        u_id = user_and_categories["user_id"]
        cat_id = user_and_categories["cat_food_id"]

        txn = service.create_transaction(
            user_id=u_id,
            transaction_type="EXPENSE",
            amount_str="100",
            transaction_date=date(2026, 9, 5),
            category_id=cat_id,
            description="Lunch",
        )

        updated = service.update_transaction(
            transaction_id=txn.id,
            user_id=u_id,
            amount_str="150.50",
            description="Deluxe Lunch",
        )

        assert updated.amount_paise == 15050
        assert updated.description == "Deluxe Lunch"
        assert updated.category_id == cat_id  # Unchanged

        # Clear category
        cleared = service.update_transaction(
            transaction_id=txn.id,
            user_id=u_id,
            clear_category=True,
        )
        assert cleared.category_id is None

    def test_update_other_user_transaction_rejected(self, user_and_categories):
        service = TransactionService()
        u_id = user_and_categories["user_id"]
        u2_id = user_and_categories["user2_id"]

        txn = service.create_transaction(
            user_id=u_id,
            transaction_type="EXPENSE",
            amount_str="100",
            transaction_date=date.today(),
        )

        with pytest.raises(ValueError, match="Cannot modify another user"):
            service.update_transaction(
                transaction_id=txn.id,
                user_id=u2_id,
                amount_str="200",
            )

    def test_delete_transaction(self, user_and_categories):
        service = TransactionService()
        u_id = user_and_categories["user_id"]

        txn = service.create_transaction(
            user_id=u_id,
            transaction_type="EXPENSE",
            amount_str="80",
            transaction_date=date.today(),
        )

        service.delete_transaction(txn.id, user_id=u_id)
        assert service.get_transaction(txn.id) is None

    def test_delete_other_user_transaction_rejected(self, user_and_categories):
        service = TransactionService()
        u_id = user_and_categories["user_id"]
        u2_id = user_and_categories["user2_id"]

        txn = service.create_transaction(
            user_id=u_id,
            transaction_type="EXPENSE",
            amount_str="80",
            transaction_date=date.today(),
        )

        with pytest.raises(ValueError, match="Cannot delete another user"):
            service.delete_transaction(txn.id, user_id=u2_id)
