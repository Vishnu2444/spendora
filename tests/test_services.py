"""
Spendora — Tests for ProfileService and CategoryService.

Tests user onboarding, profile creation, duplicate validation,
profession category suggestions, and category accept/reject logic.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch

from database.models import Base, User, Category, CategorySource
from services.profile_service import ProfileService
from services.category_service import CategoryService


@pytest.fixture(scope="function")
def test_db():
    """Isolated SQLite database in-memory for service testing."""
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
         patch("services.category_service.get_session", side_effect=mock_get_session):
        yield engine

    Base.metadata.drop_all(engine)
    engine.dispose()


class TestProfileService:

    def test_create_user_success(self, test_db):
        service = ProfileService()
        user = service.create_user(
            name="Vichu",
            profession="Software Engineer",
            monthly_income_str="75000",
            fixed_expenses_str="25000",
            currency="INR",
        )
        assert user.id is not None
        assert user.name == "Vichu"
        assert user.profession == "Software Engineer"
        assert user.monthly_income_paise == 75_000_00
        assert user.fixed_expenses_paise == 25_000_00
        assert user.is_onboarding_complete is False

    def test_create_user_invalid_profession(self, test_db):
        service = ProfileService()
        with pytest.raises(ValueError, match="not a recognised profession"):
            service.create_user(name="Vichu", profession="Astronaut")

    def test_create_user_other_without_custom_raises(self, test_db):
        service = ProfileService()
        with pytest.raises(ValueError, match="specify your profession"):
            service.create_user(name="Vichu", profession="Other")

    def test_create_user_other_with_custom_success(self, test_db):
        service = ProfileService()
        user = service.create_user(
            name="Vichu",
            profession="Other",
            profession_custom="UI/UX Designer",
        )
        assert user.profession == "Other"
        assert user.profession_custom == "UI/UX Designer"

    def test_mark_onboarding_complete(self, test_db):
        service = ProfileService()
        user = service.create_user(name="Vichu", profession="Freelancer")
        service.mark_onboarding_complete(user.id)
        current = service.get_current_user()
        assert current is not None
        assert current.is_onboarding_complete is True


class TestCategoryService:

    def test_get_suggestions_for_profession(self, test_db):
        service = CategoryService()
        suggestions = service.get_suggestions_for_profession("Software Engineer")
        assert len(suggestions) > 0
        names = [s["name"] for s in suggestions]
        assert "Food" in names
        assert "Technology" in names

    def test_accept_suggestions_creates_categories_and_subcategories(self, test_db):
        profile_service = ProfileService()
        user = profile_service.create_user(name="Vichu", profession="Doctor")

        cat_service = CategoryService()
        suggestions = [
            {
                "name": "Food",
                "icon": "food",
                "color": "#FF6B6B",
                "subcategories": ["Groceries", "Dining Out"],
            },
            {
                "name": "Transport",
                "icon": "car",
                "color": "#4ECDC4",
                "subcategories": ["Fuel", "Cab"],
            },
        ]

        created = cat_service.accept_suggestions(user.id, suggestions, source=CategorySource.SYSTEM)
        assert len(created) == 2

        all_cats = cat_service.list_categories(user.id)
        assert len(all_cats) == 2
        food_cat = next(c for c in all_cats if c.name == "Food")
        sub_names = [s.name for s in food_cat.subcategories]
        assert "Groceries" in sub_names
        assert "Dining Out" in sub_names

    def test_accept_suggestions_prevents_duplicates(self, test_db):
        profile_service = ProfileService()
        user = profile_service.create_user(name="Vichu", profession="Student")

        cat_service = CategoryService()
        suggestions = [{"name": "Food", "icon": "food", "color": "#FF6B6B", "subcategories": ["Canteen"]}]

        cat_service.accept_suggestions(user.id, suggestions)
        # Second call with same category should not create duplicate
        cat_service.accept_suggestions(user.id, suggestions)

        all_cats = cat_service.list_categories(user.id)
        assert len(all_cats) == 1

    def test_create_and_rename_category(self, test_db):
        profile_service = ProfileService()
        user = profile_service.create_user(name="Vichu", profession="Developer")

        cat_service = CategoryService()
        cat = cat_service.create_category(user.id, "Gadgets")
        assert cat.name == "Gadgets"
        assert cat.source == CategorySource.USER

        updated = cat_service.rename_category(cat.id, "Tech Gadgets")
        assert updated.name == "Tech Gadgets"

    def test_create_duplicate_category_raises(self, test_db):
        profile_service = ProfileService()
        user = profile_service.create_user(name="Vichu", profession="Developer")

        cat_service = CategoryService()
        cat_service.create_category(user.id, "Shopping")
        with pytest.raises(ValueError, match="already exists"):
            cat_service.create_category(user.id, "Shopping")

    def test_get_user_categories_alias(self, test_db):
        profile_service = ProfileService()
        user = profile_service.create_user(name="Vichu", profession="Developer")

        cat_service = CategoryService()
        cat_service.create_category(user.id, "Electronics")
        cats = cat_service.get_user_categories(user.id)
        assert len(cats) == 1
        assert cats[0].name == "Electronics"

