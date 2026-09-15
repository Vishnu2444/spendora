"""
Spendora — Tests for the full onboarding UI flow and routing.
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.models import Base
from services.profile_service import ProfileService
from services.category_service import CategoryService


@pytest.fixture(scope="function")
def isolated_db():
    """Isolated SQLite in-memory database for full onboarding testing."""
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

    with patch("database.database.get_session", side_effect=mock_get_session), \
         patch("services.profile_service.get_session", side_effect=mock_get_session), \
         patch("services.category_service.get_session", side_effect=mock_get_session), \
         patch("screens.onboarding.welcome_screen.ProfileService") as mock_ws_profile, \
         patch("screens.onboarding.category_setup_screen.CategoryService") as mock_cs_cat, \
         patch("screens.onboarding.category_setup_screen.ProfileService") as mock_cs_profile:

        # Wire up real service instances that point to our mock session
        real_profile = ProfileService()
        real_category = CategoryService()
        mock_ws_profile.return_value = real_profile
        mock_cs_profile.return_value = real_profile
        mock_cs_cat.return_value = real_category

        yield engine

    Base.metadata.drop_all(engine)
    engine.dispose()


def test_complete_onboarding_pipeline(isolated_db):
    profile_service = ProfileService()
    category_service = CategoryService()

    # 1. No user initially
    assert profile_service.has_user() is False
    assert profile_service.get_current_user() is None

    # 2. User fills onboarding form
    user = profile_service.create_user(
        name="Vichu",
        profession="Software Engineer",
        monthly_income_str="120000",
        fixed_expenses_str="40000",
        currency="INR",
    )
    assert user.id == 1
    assert user.is_onboarding_complete is False

    # 3. Suggestions retrieved for profession
    suggestions = category_service.get_suggestions_for_profession(user.profession)
    assert len(suggestions) > 0

    # 4. User accepts subset or all suggestions
    accepted = suggestions[:5]
    saved_cats = category_service.accept_suggestions(user.id, accepted)
    assert len(saved_cats) == 5

    # 5. Mark onboarding complete
    profile_service.mark_onboarding_complete(user.id)
    current_user = profile_service.get_current_user()
    assert current_user.is_onboarding_complete is True

    # 6. Verify stored categories
    user_cats = category_service.list_categories(user.id)
    assert len(user_cats) == 5

