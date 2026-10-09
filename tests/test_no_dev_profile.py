"""
Regression tests: production startup must NOT create hardcoded development profiles.

Verifies that the WelcomeView onboarding screen initializes with empty form fields
and does not silently inject development/test profile data such as "Vishnu",
"Software Engineer", "60000", "Bengaluru, India", or "26 yrs".
"""

from __future__ import annotations

import inspect
import re
import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.models import Base
from services.profile_service import ProfileService

# ---------------------------------------------------------------------------
# Development values that MUST NOT appear as pre-filled form defaults
# ---------------------------------------------------------------------------
_DEV_VALUES = {
    "Vishnu",
    "26 yrs",
    "₹ 60,000 / mo",
    "60,000",
    "Bengaluru, India",
}


@pytest.fixture(scope="function")
def isolated_db():
    """Isolated SQLite in-memory database."""
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
         patch("services.transaction_service.get_session", side_effect=mock_get_session), \
         patch("services.calculation_service.get_session", side_effect=mock_get_session), \
         patch("services.analytics_service.get_session", side_effect=mock_get_session):
        yield engine

    Base.metadata.drop_all(engine)
    engine.dispose()


class TestNoHardcodedDevProfile:
    """Ensure production onboarding does not contain development profile data."""

    def test_welcome_form_fields_are_empty(self):
        """WelcomeView form fields must start empty — no pre-filled dev values."""
        from screens.onboarding.welcome_screen import WelcomeView

        mock_complete = MagicMock()
        view = WelcomeView(on_complete=mock_complete)

        assert view._name_field.value == "", \
            f"Name field pre-filled with '{view._name_field.value}' — must be empty"
        assert view._age_field.value == "", \
            f"Age field pre-filled with '{view._age_field.value}' — must be empty"
        assert view._income_field.value == "", \
            f"Income field pre-filled with '{view._income_field.value}' — must be empty"
        assert view._city_field.value == "", \
            f"City field pre-filled with '{view._city_field.value}' — must be empty"
        assert view._custom_prof_field.value == "", \
            f"Custom profession field pre-filled with '{view._custom_prof_field.value}' — must be empty"
        assert view._custom_prof_container.visible is False, \
            "Custom profession container must start hidden"

    def test_welcome_others_shows_custom_input_text_box(self):
        """Selecting 'Others' in WelcomeView must show the custom input text box."""
        from screens.onboarding.welcome_screen import WelcomeView

        mock_complete = MagicMock()
        view = WelcomeView(on_complete=mock_complete)
        view.build()

        assert view._custom_prof_container.visible is False

        # Select 'Others'
        view._select_profession("Others")
        assert view._custom_prof_container.visible is True

        # Switch to another profession
        view._select_profession("Doctor")
        assert view._custom_prof_container.visible is False

        # Switch back to 'Others'
        view._select_profession("Others")
        assert view._custom_prof_container.visible is True

    def test_welcome_others_requires_custom_text_on_submit(self):
        """Submitting with 'Others' selected requires typing in the custom profession field."""
        from screens.onboarding.welcome_screen import WelcomeView

        mock_complete = MagicMock()
        view = WelcomeView(on_complete=mock_complete)
        view.build()

        view._name_field.value = "Karthik"
        view._select_profession("Others")
        view._custom_prof_field.value = ""

        view._on_submit(None)
        mock_complete.assert_not_called()
        assert view._error_text.visible is True
        assert "custom profession" in view._error_text.value.lower()

    def test_welcome_others_saves_custom_profession(self, isolated_db):
        """Submitting with 'Others' and custom profession text persists successfully."""
        from screens.onboarding.welcome_screen import WelcomeView

        mock_complete = MagicMock()
        view = WelcomeView(on_complete=mock_complete)
        view.build()

        view._name_field.value = "Maya"
        view._select_profession("Others")
        view._custom_prof_field.value = "Architect"

        view._on_submit(None)
        mock_complete.assert_called_once()

        ps = ProfileService()
        user = ps.get_current_user()
        assert user is not None
        assert user.profession == "Other"
        assert user.profession_custom == "Architect"

    def test_welcome_no_preselected_profession(self):
        """WelcomeView must not pre-select any profession chip."""
        from screens.onboarding.welcome_screen import WelcomeView

        mock_complete = MagicMock()
        view = WelcomeView(on_complete=mock_complete)

        assert view._selected_profession is None, \
            f"Profession pre-selected as '{view._selected_profession}' — must be None"

    def test_skip_requires_name(self):
        """Pressing skip with an empty name must NOT create a profile."""
        from screens.onboarding.welcome_screen import WelcomeView

        mock_complete = MagicMock()
        view = WelcomeView(on_complete=mock_complete)

        # Simulate skip with empty name
        view._on_skip(None)

        # on_complete should NOT have been called
        mock_complete.assert_not_called()
        # Error text should be visible
        assert view._error_text.visible is True

    def test_skip_does_not_inject_dev_profile(self, isolated_db):
        """Skip with a user-provided name must NOT inject hardcoded dev values."""
        from screens.onboarding.welcome_screen import WelcomeView

        mock_complete = MagicMock()
        view = WelcomeView(on_complete=mock_complete)

        # User types their own name
        view._name_field.value = "TestUser"
        view._on_skip(None)

        # Profile should be created with the user's name, not "Vishnu"
        ps = ProfileService()
        user = ps.get_current_user()
        assert user is not None
        assert user.name == "TestUser"
        assert user.name != "Vishnu"

    def test_fresh_db_has_no_profile(self, isolated_db):
        """A freshly initialized database must contain zero user profiles."""
        ps = ProfileService()
        assert ps.has_profile() is False
        assert ps.get_current_user() is None

    def test_welcome_source_no_hardcoded_dev_defaults(self):
        """
        Static analysis: the WelcomeView __init__ source code must not contain
        hardcoded development values as field defaults.
        """
        from screens.onboarding.welcome_screen import WelcomeView

        source = inspect.getsource(WelcomeView.__init__)

        for dev_val in _DEV_VALUES:
            # Look for value="<dev_val>" patterns in the source
            pattern = re.compile(rf'value\s*=\s*["\'].*{re.escape(dev_val)}.*["\']')
            assert not pattern.search(source), \
                f"WelcomeView.__init__ still contains hardcoded dev value: '{dev_val}'"

    def test_on_skip_source_no_hardcoded_vishnu(self):
        """
        Static analysis: _on_skip must not contain hardcoded name='Vishnu'
        or monthly_income_str='60000'.
        """
        from screens.onboarding.welcome_screen import WelcomeView

        source = inspect.getsource(WelcomeView._on_skip)

        assert 'name="Vishnu"' not in source, \
            "_on_skip still creates a hardcoded 'Vishnu' profile"
        assert "name='Vishnu'" not in source, \
            "_on_skip still creates a hardcoded 'Vishnu' profile"
        assert 'monthly_income_str="60000"' not in source, \
            "_on_skip still uses hardcoded income '60000'"

    def test_dashboard_starts_with_zero_balance_income_expenses(self, isolated_db):
        """Dashboard must initialize and refresh with Balance ₹0.00, Income ₹0.00, Expenses ₹0.00."""
        from screens.dashboard.dashboard_screen import DashboardView

        dash = DashboardView()
        # Initial control values
        assert dash._balance_text.value == "₹0.00"
        assert "₹0.00" in dash._deduction_text.value
        assert "Income: ₹0.00" in dash._deduction_text.value
        assert "Expenses: ₹0.00" in dash._deduction_text.value

        # After refresh with empty database
        dash.refresh()
        assert dash._balance_text.value == "₹0.00"
        assert "Income: ₹0.00" in dash._deduction_text.value
        assert "Expenses: ₹0.00" in dash._deduction_text.value

    def test_dashboard_empty_spending_breakdown_and_recent_expenses(self, isolated_db):
        """Spending Breakdown and Recent Expenses must show 'No expenses yet' when no transactions exist."""
        from screens.dashboard.dashboard_screen import DashboardView

        dash = DashboardView()
        dash.refresh()

        # Legend column in spending breakdown should show "No expenses yet"
        legend_texts = [
            c.content.value if hasattr(c, "content") and hasattr(c.content, "value") else ""
            for c in dash._legend_column.controls
        ]
        assert any("No expenses yet" in t for t in legend_texts)

        # Recent transactions list should show "No expenses yet"
        recent_texts = []
        for c in dash._recent_list.controls:
            if hasattr(c, "content") and hasattr(c.content, "controls"):
                for sub in c.content.controls:
                    if hasattr(sub, "value"):
                        recent_texts.append(sub.value)
        assert any("No expenses yet" in t for t in recent_texts)

    def test_no_hardcoded_stitch_or_showcase_samples(self):
        """Static analysis: no demo transactions (Lunch, Uber, CNG, etc.) or salary fallbacks in dashboard."""
        import screens.dashboard.dashboard_screen as dash_mod
        source = inspect.getsource(dash_mod)

        assert "stitch_samples" not in source, "Dashboard still references stitch_samples"
        assert "showcase_items" not in source, "Dashboard still references showcase_items"
        assert "6628000" not in source, "Dashboard still references 6628000 fallback salary"
        assert "4228000" not in source, "Dashboard still references 4228000 fallback balance"
        assert "2400000" not in source, "Dashboard still references 2400000 fallback expenses"
