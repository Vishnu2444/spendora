"""
Spendora — Tests for ORM models (schema integrity, constraints, enums).

Uses an in-memory SQLite database — no disk access, fast, isolated.
"""

from __future__ import annotations

import pytest
from datetime import date, datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.models import (
    Base,
    User,
    Category,
    CategorySource,
    Subcategory,
    Transaction,
    TransactionType,
    UserPreference,
    utcnow,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def engine():
    """In-memory SQLite engine per test function."""
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture(scope="function")
def session(engine):
    """Session bound to the in-memory engine."""
    Session = sessionmaker(bind=engine)
    sess = Session()
    yield sess
    sess.close()


@pytest.fixture
def sample_user(session) -> User:
    user = User(
        name="Vichu",
        profession="Software Engineer",
        currency="INR",
        is_onboarding_complete=False,
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    session.add(user)
    session.commit()
    return user


@pytest.fixture
def sample_category(session, sample_user) -> Category:
    cat = Category(
        user_id=sample_user.id,
        name="Food",
        color="#FF6B6B",
        icon="food",
        source=CategorySource.SYSTEM,
        is_active=True,
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    session.add(cat)
    session.commit()
    return cat


# ---------------------------------------------------------------------------
# User model tests
# ---------------------------------------------------------------------------

class TestUserModel:

    def test_create_user(self, session):
        user = User(
            name="Test User",
            profession="Teacher",
            currency="INR",
            is_onboarding_complete=False,
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        session.add(user)
        session.commit()
        assert user.id is not None
        assert user.id > 0

    def test_user_defaults(self, session):
        user = User(
            name="Default Test",
            profession="Student",
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        session.add(user)
        session.commit()
        assert user.currency == "INR"
        assert user.is_onboarding_complete == False

    def test_user_monthly_income_paise(self, session):
        user = User(
            name="Income User",
            profession="Developer",
            monthly_income_paise=50_000_00,  # ₹50,000
            currency="INR",
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        session.add(user)
        session.commit()
        fetched = session.get(User, user.id)
        assert fetched.monthly_income_paise == 50_000_00

    def test_user_repr(self, sample_user):
        r = repr(sample_user)
        assert "User" in r
        assert "Vichu" in r

    def test_mark_onboarding_complete(self, session, sample_user):
        sample_user.is_onboarding_complete = True
        session.commit()
        fetched = session.get(User, sample_user.id)
        assert fetched.is_onboarding_complete == True


# ---------------------------------------------------------------------------
# Category model tests
# ---------------------------------------------------------------------------

class TestCategoryModel:

    def test_create_category(self, session, sample_user):
        cat = Category(
            user_id=sample_user.id,
            name="Transport",
            color="#4ECDC4",
            icon="car",
            source=CategorySource.USER,
            is_active=True,
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        session.add(cat)
        session.commit()
        assert cat.id is not None

    def test_category_sources(self, session, sample_user):
        """All three CategorySource values should be storable."""
        for source in CategorySource:
            cat = Category(
                user_id=sample_user.id,
                name=f"Cat_{source.value}",
                source=source,
                is_active=True,
                created_at=utcnow(),
                updated_at=utcnow(),
            )
            session.add(cat)
        session.commit()

    def test_category_soft_delete(self, session, sample_category):
        sample_category.is_active = False
        session.commit()
        fetched = session.get(Category, sample_category.id)
        assert fetched.is_active == False

    def test_category_cascade_delete_removes_subcategories(self, session, sample_category):
        sub = Subcategory(
            category_id=sample_category.id,
            name="Restaurant",
            source=CategorySource.SYSTEM,
            is_active=True,
            created_at=utcnow(),
        )
        session.add(sub)
        session.commit()
        sub_id = sub.id

        # Delete the parent category.
        session.delete(sample_category)
        session.commit()

        # Subcategory should also be gone.
        assert session.get(Subcategory, sub_id) is None


# ---------------------------------------------------------------------------
# Transaction model tests
# ---------------------------------------------------------------------------

class TestTransactionModel:

    def test_create_income_transaction(self, session, sample_user, sample_category):
        tx = Transaction(
            user_id=sample_user.id,
            category_id=sample_category.id,
            amount_paise=5_000_00,  # ₹5,000
            transaction_type=TransactionType.INCOME,
            transaction_date=date(2026, 9, 14),
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        session.add(tx)
        session.commit()
        assert tx.id is not None
        assert tx.amount_paise == 5_000_00
        assert tx.transaction_type == TransactionType.INCOME

    def test_create_expense_transaction(self, session, sample_user, sample_category):
        tx = Transaction(
            user_id=sample_user.id,
            category_id=sample_category.id,
            amount_paise=1_500_00,  # ₹1,500
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date(2026, 9, 14),
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        session.add(tx)
        session.commit()
        assert tx.transaction_type == TransactionType.EXPENSE

    def test_transaction_without_category(self, session, sample_user):
        """Transactions should be valid with no category assigned."""
        tx = Transaction(
            user_id=sample_user.id,
            amount_paise=100_00,
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date(2026, 9, 14),
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        session.add(tx)
        session.commit()
        assert tx.category_id is None

    def test_transaction_types_enum(self):
        assert TransactionType.INCOME.value == "INCOME"
        assert TransactionType.EXPENSE.value == "EXPENSE"

    def test_transaction_repr(self, session, sample_user):
        tx = Transaction(
            user_id=sample_user.id,
            amount_paise=100_00,
            transaction_type=TransactionType.EXPENSE,
            transaction_date=date(2026, 9, 14),
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        session.add(tx)
        session.commit()
        r = repr(tx)
        assert "Transaction" in r
        assert "EXPENSE" in r


# ---------------------------------------------------------------------------
# UserPreference model tests
# ---------------------------------------------------------------------------

class TestUserPreferenceModel:

    def test_create_preference(self, session, sample_user):
        pref = UserPreference(
            user_id=sample_user.id,
            key="dashboard_period",
            value="this_month",
            updated_at=utcnow(),
        )
        session.add(pref)
        session.commit()
        assert pref.id is not None

    def test_preference_null_value(self, session, sample_user):
        pref = UserPreference(
            user_id=sample_user.id,
            key="some_flag",
            value=None,
            updated_at=utcnow(),
        )
        session.add(pref)
        session.commit()
        assert pref.value is None

