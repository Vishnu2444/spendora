"""
Pytest configuration and test setup for Spendora.
"""

import utils.flet_compat  # Ensure Flet 1.0 compatibility layer is active for all tests
import pytest
from database.database import init_db, get_session
from database.models import User
from services.category_service import CategoryService


@pytest.fixture(scope="session", autouse=True)
def setup_test_session():
    """Ensure database tables and baseline test user exist for tests."""
    init_db()
    with get_session() as session:
        user = session.get(User, 1)
        if not user:
            user = User(id=1, name="Test User", profession="Engineer", currency="INR")
            session.add(user)
            session.commit()
            cat_service = CategoryService()
            suggestions = cat_service.get_suggestions_for_profession("Engineer")
            cat_service.accept_suggestions(1, suggestions)
