"""
Spendora — Tests for Personalization and Category Customization.

Validates:
- Custom category creation with color and icon
- Updating category attributes (name, color, icon)
- Duplicate prevention during category updates
- Subcategory creation, renaming, and soft-deletion
- User profile updates (name, baselines, currency switching)
- Referential integrity with transactions upon category soft-deletion
"""

from __future__ import annotations

from datetime import date
from unittest.mock import patch
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.models import Base, Category, CategorySource, Transaction, TransactionType, User
from services.category_service import CategoryService
from services.profile_service import ProfileService
from services.transaction_service import TransactionService


@pytest.fixture(scope="function")
def pers_test_db():
    """Isolated SQLite database in-memory for Personalization testing."""
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
         patch("services.transaction_service.get_session", side_effect=mock_get_session):
        yield Session

    Base.metadata.drop_all(engine)
    engine.dispose()


class TestPersonalization:

    def test_create_and_update_category_customization(self, pers_test_db):
        prof_service = ProfileService()
        cat_service = CategoryService()

        user = prof_service.create_user(name="Maya", profession="Freelancer")

        # Create custom category
        cat = cat_service.create_category(
            user_id=user.id,
            name="Subscriptions",
            color="#FF6B6B",
            icon="television-play",
        )
        assert cat.id is not None
        assert cat.name == "Subscriptions"
        assert cat.color == "#FF6B6B"
        assert cat.icon == "television-play"
        assert cat.source == CategorySource.USER

        # Update category: name, color, and icon
        updated = cat_service.update_category(
            category_id=cat.id,
            name="Digital Subscriptions",
            color="#9C27B0",
            icon="wifi",
        )
        assert updated.name == "Digital Subscriptions"
        assert updated.color == "#9C27B0"
        assert updated.icon == "wifi"

    def test_update_category_duplicate_name_rejected(self, pers_test_db):
        prof_service = ProfileService()
        cat_service = CategoryService()

        user = prof_service.create_user(name="Maya", profession="Freelancer")
        cat1 = cat_service.create_category(user.id, "Food")
        cat2 = cat_service.create_category(user.id, "Travel")

        with pytest.raises(ValueError, match="already exists"):
            cat_service.update_category(category_id=cat2.id, name="Food")

    def test_subcategory_lifecycle(self, pers_test_db):
        prof_service = ProfileService()
        cat_service = CategoryService()

        user = prof_service.create_user(name="Maya", profession="Freelancer")
        cat = cat_service.create_category(user.id, "Food")

        # Create subcategory
        sub = cat_service.create_subcategory(category_id=cat.id, name="Dining Out")
        assert sub.name == "Dining Out"
        assert sub.category_id == cat.id

        # Rename subcategory
        renamed = cat_service.rename_subcategory(sub.id, "Fine Dining")
        assert renamed.name == "Fine Dining"

        # Delete subcategory
        cat_service.delete_subcategory(sub.id, soft=True)
        # Verify it is no longer listed in active categories
        cats = cat_service.list_categories(user.id)
        assert len(cats[0].subcategories) == 0

    def test_soft_delete_category_preserves_transactions(self, pers_test_db):
        prof_service = ProfileService()
        cat_service = CategoryService()
        txn_service = TransactionService()

        user = prof_service.create_user(name="Maya", profession="Freelancer")
        cat = cat_service.create_category(user.id, "Entertainment")

        # Create transaction linked to this category
        txn = txn_service.create_transaction(
            user_id=user.id,
            transaction_type="EXPENSE",
            amount_str="500",
            transaction_date=date.today(),
            category_id=cat.id,
            description="Concert Ticket",
        )

        # Soft delete category
        cat_service.delete_category(cat.id, soft=True)

        # Category is no longer in active categories list
        active_cats = cat_service.list_categories(user.id)
        assert not any(c.id == cat.id for c in active_cats)

        # But the transaction still exists and references the category id
        fetched_txn = txn_service.get_transaction(txn.id)
        assert fetched_txn is not None
        assert fetched_txn.category_id == cat.id

    def test_profile_update_and_currency_switch(self, pers_test_db):
        prof_service = ProfileService()

        user = prof_service.create_user(
            name="Maya",
            profession="Freelancer",
            monthly_income_str="50000",
            currency="INR",
        )
        assert user.currency == "INR"
        assert user.monthly_income_paise == 50000_00

        # Update profile with USD and new income
        updated = prof_service.update_profile(
            user_id=user.id,
            name="Maya Angel",
            currency="USD",
            monthly_income_str="2500.00",
            fixed_expenses_str="800.00",
        )
        assert updated.name == "Maya Angel"
        assert updated.currency == "USD"
        assert updated.monthly_income_paise == 2500_00
        assert updated.fixed_expenses_paise == 800_00
