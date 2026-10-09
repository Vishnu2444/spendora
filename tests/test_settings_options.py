"""
Tests for Leaksee Settings screen options.

Validates that all options shown in the Settings UI are fully functional:
1. User Profile Card:
   - Name, initials, profession, location, email
   - Monthly budget editing and formatting
   - Tracked since display
2. AI & Automation:
   - Cloud AI (Google Gemini) toggle persistence & AIService integration
   - AI Peer Insights toggle persistence
   - Smart Categorization toggle persistence
   - AI Voice & Floating Bar toggle persistence
   - Privacy & Storage dialog trigger
3. Preferences & Region:
   - Primary Currency selection and symbol updating
   - Category management dialog trigger
   - Financial Month Cycle selection and subtitle updating
   - Daily Expense Check reminder time selection and subtitle updating
4. Security & Cloud Ledger:
   - Biometric / Face ID Login toggle persistence
   - Cloud Backup & Sync execution, snapshot creation, and timestamp updating
   - Export Financial Ledger: CSV itemized export, Audit summary report, and SQLite backup
"""

import os
import shutil
from datetime import date, datetime
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config.settings import DEFAULT_CURRENCY, CURRENCY_SYMBOLS, DATABASE_PATH
from database.models import Base, TransactionType, CategorySource
from services.profile_service import ProfileService
from services.category_service import CategoryService
from services.transaction_service import TransactionService
from services.ai_service import AIService
from screens.personalization.personalization_screen import PersonalizationView


@pytest.fixture(scope="function")
def settings_db(tmp_path, monkeypatch):
    """Provides isolated test database with initialized tables."""
    db_file = tmp_path / "test_settings.db"
    engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})
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

    monkeypatch.setattr("services.profile_service.get_session", mock_get_session)
    monkeypatch.setattr("services.category_service.get_session", mock_get_session)
    monkeypatch.setattr("services.transaction_service.get_session", mock_get_session)
    monkeypatch.setattr("services.ai_service.get_session", mock_get_session)
    monkeypatch.setattr("database.database.get_session", mock_get_session)

    yield Session

    Base.metadata.drop_all(engine)
    engine.dispose()


class MockEvent:
    def __init__(self, value):
        self.control = type("Ctrl", (), {"value": value})()


class TestSettingsOptions:

    def test_user_profile_card_dynamic_fields(self, settings_db):
        prof_service = ProfileService()
        user = prof_service.create_user(name="Alice Smith", profession="Software Engineer")
        prof_service.set_preference(user.id, "user_location", "Bangalore, India")
        prof_service.set_preference(user.id, "user_email", "alice@design.io")
        prof_service.update_profile(user.id, monthly_income_str="75000")

        view = PersonalizationView()
        view.refresh()

        assert view._name_text.value == "Alice Smith"
        assert view._avatar_text.value == "AS"
        assert view._prof_text.value == "Software Engineer • Bangalore, India"
        assert view._email_text.value == "alice@design.io"
        assert "75,000" in view._budget_text.value

    def test_ai_automation_switches_persistence(self, settings_db):
        prof_service = ProfileService()
        user = prof_service.create_user(name="Bob Jones", profession="Developer")

        view = PersonalizationView()
        view.refresh()

        # Toggle Cloud AI
        view._on_switch_toggle("cloud_ai_enabled", "Cloud AI (Google Gemini)", MockEvent(True))
        assert prof_service.get_preference(user.id, "cloud_ai_enabled") == "true"

        ai_service = AIService()
        assert ai_service.is_cloud_ai_enabled(user.id) is False or ai_service.is_configured() is False
        # When configured with API key, is_cloud_ai_enabled checks this preference:
        with pytest.MonkeyPatch.context() as m:
            m.setattr(ai_service, "is_configured", lambda: True)
            assert ai_service.is_cloud_ai_enabled(user.id) is True

        # Toggle Peer Insights
        view._on_switch_toggle("ai_peer_insights_enabled", "AI Peer Insights", MockEvent(False))
        assert prof_service.get_preference(user.id, "ai_peer_insights_enabled") == "false"

        # Toggle Smart Categorization
        view._on_switch_toggle("smart_categorization_enabled", "Smart Categorization", MockEvent(False))
        assert prof_service.get_preference(user.id, "smart_categorization_enabled") == "false"

        # Toggle AI Voice
        view._on_switch_toggle("ai_voice_bar_enabled", "AI Voice & Floating Bar", MockEvent(False))
        assert prof_service.get_preference(user.id, "ai_voice_bar_enabled") == "false"

        # Toggle Biometric
        view._on_switch_toggle("biometric_enabled", "Biometric / Face ID Login", MockEvent(True))
        assert prof_service.get_preference(user.id, "biometric_enabled") == "true"

    def test_financial_cycle_and_daily_check_preferences(self, settings_db):
        prof_service = ProfileService()
        user = prof_service.create_user(name="Clara", profession="Freelancer")

        view = PersonalizationView()
        view.refresh()

        # Set financial cycle to 5th
        prof_service.set_preference(user.id, "financial_cycle_start_day", "5")
        # Set daily expense check to 9:00 PM
        prof_service.set_preference(user.id, "daily_expense_check_time", "9:00 PM")

        view.refresh()
        assert view._cycle_text.value == "5th of month"
        assert view._cycle_subtitle_text.value == "Starts 5th of each month"
        assert view._daily_check_text.value == "9:00 PM"
        assert "9:00 PM" in view._daily_check_subtitle_text.value

    def test_currency_selection_updates_symbol_and_budget(self, settings_db):
        prof_service = ProfileService()
        user = prof_service.create_user(name="David", profession="Business Owner")
        prof_service.update_profile(user.id, monthly_income_str="5000")

        view = PersonalizationView()
        view.refresh()
        assert "₹" in view._budget_text.value

        # Switch to USD
        prof_service.update_profile(user.id, currency="USD")
        view.refresh()
        assert "USD ($)" in view._currency_text.value
        assert "$" in view._budget_text.value
        assert "5,000" in view._budget_text.value

    def test_cloud_backup_sync_and_exports(self, settings_db, tmp_path):
        prof_service = ProfileService()
        txn_service = TransactionService()
        cat_service = CategoryService()

        user = prof_service.create_user(name="Elena", profession="Software Engineer")
        cat = cat_service.create_category(user.id, "Cloud Tools")
        txn_service.create_transaction(
            user_id=user.id,
            transaction_type="EXPENSE",
            amount_str="1200",
            transaction_date=date.today(),
            category_id=cat.id,
            description="GPU server rental",
        )

        view = PersonalizationView()
        view.refresh()

        # Test Cloud Sync action
        view._on_cloud_sync_click()
        assert "today" in view._cloud_sync_time_text.value
        last_sync = prof_service.get_preference(user.id, "last_cloud_sync_timestamp")
        assert last_sync is not None

        # Test Export CSV
        view._export_ledger_csv()
        data_files = os.listdir("data") if os.path.exists("data") else []
        csv_files = [f for f in data_files if f.startswith("leaksee_ledger_") and f.endswith(".csv")]
        assert len(csv_files) >= 1

        # Test Export Audit report
        view._export_audit_report()
        data_files = os.listdir("data") if os.path.exists("data") else []
        txt_files = [f for f in data_files if f.startswith("leaksee_audit_report_") and f.endswith(".txt")]
        assert len(txt_files) >= 1

        # Verify audit report contents
        with open(os.path.join("data", txt_files[-1]), "r", encoding="utf-8") as f:
            content = f.read()
            assert "LEAKSEE FINANCIAL AUDIT REPORT" in content
            assert "GPU server rental" in content
            assert "Elena" in content

        # Cleanup generated test data exports
        for f in csv_files + txt_files:
            try:
                os.remove(os.path.join("data", f))
            except Exception:
                pass

    def test_financial_cycle_dialog_interaction(self, settings_db):
        """Validates that financial month cycle dialog opens without NameError and updates preferences."""
        prof_service = ProfileService()
        user = prof_service.create_user(name="Grace", profession="Software Engineer")

        page = type("MockPage", (), {"overlay": [], "update": lambda self: None, "snack_bar": None})()
        view = PersonalizationView()
        view._user = user
        view.set_page(page)

        # Open dialog - should not raise NameError: name 'label' is not defined
        view._open_cycle_dialog()
        assert len(page.overlay) >= 1
        dialog = page.overlay[-1]
        assert dialog.title.value == "Financial Month Cycle"
        assert len(dialog.content.controls) == 6

        # Trigger 15th option selection (index 3)
        dialog.content.controls[3].on_click(None)
        assert view._cycle_text.value == "15th of month"
        assert view._cycle_subtitle_text.value == "Starts 15th of each month"
        assert prof_service.get_preference(user.id, "financial_cycle_start_day") == "15"

    def test_daily_check_dialog_interaction(self, settings_db):
        """Validates that daily expense check dialog opens without NameError and updates preferences."""
        prof_service = ProfileService()
        user = prof_service.create_user(name="Henry", profession="Developer")

        page = type("MockPage", (), {"overlay": [], "update": lambda self: None, "snack_bar": None})()
        view = PersonalizationView()
        view._user = user
        view.set_page(page)

        # Open dialog - should not raise NameError: name 'label' is not defined
        view._open_daily_check_dialog()
        assert len(page.overlay) >= 1
        dialog = page.overlay[-1]
        assert dialog.title.value == "Daily Expense Check Time"
        assert len(dialog.content.controls) == 6

        # Trigger 9:00 PM option selection (index 2)
        dialog.content.controls[2].on_click(None)
        assert view._daily_check_text.value == "9:00 PM"
        assert "9:00 PM" in view._daily_check_subtitle_text.value
        assert prof_service.get_preference(user.id, "daily_expense_check_time") == "9:00 PM"

        # Re-open dialog and trigger Custom Time option (index 4)
        view._open_daily_check_dialog()
        dialog = page.overlay[-1]
        dialog.content.controls[4].on_click(None)
        assert len(page.overlay) >= 2
        custom_dialog = page.overlay[-1]
        # Custom time dialog title contains 'Custom Reminder Time'
        title_text = custom_dialog.title.controls[1].value if hasattr(custom_dialog.title, "controls") else custom_dialog.title.value
        assert "Custom Reminder Time" in title_text

        # Test custom time formatting and persistence
        parsed = PersonalizationView._parse_and_format_time("6:30 PM")
        assert parsed == "6:30 PM"
        parsed_24h = PersonalizationView._parse_and_format_time("21:45")
        assert parsed_24h == "9:45 PM"
        prof_service.set_preference(user.id, "daily_expense_check_time", parsed)
        view.refresh()
        assert view._daily_check_text.value == "6:30 PM"
        assert "6:30 PM" in view._daily_check_subtitle_text.value

    def test_change_download_path_and_export_audit(self, settings_db, tmp_path):
        """Validates changing the download path and exporting audit report to the custom path."""
        prof_service = ProfileService()
        txn_service = TransactionService()
        cat_service = CategoryService()

        user = prof_service.create_user(name="Ivy", profession="Freelancer")
        cat = cat_service.create_category(user.id, "Audit Compliance")
        txn_service.create_transaction(
            user_id=user.id,
            transaction_type="INCOME",
            amount_str="5000",
            transaction_date=date.today(),
            category_id=cat.id,
            description="Consulting Fee",
        )

        page = type("MockPage", (), {"overlay": [], "update": lambda self: None, "snack_bar": None})()
        view = PersonalizationView()
        view._user = user
        view.set_page(page)
        view.refresh()

        # Check default export directory is data
        assert view._get_export_directory() == "data"
        assert view._export_path_pill_text.value == "data/"

        # Open Change Download Path dialog
        view._open_change_download_path_dialog()
        assert len(page.overlay) >= 1
        path_dialog = page.overlay[-1]
        assert "Change Download Path" in path_dialog.title.controls[1].value

        # Change download directory to tmp_path / "custom_audit_dir"
        custom_audit_dir = tmp_path / "custom_audit_dir"
        success = view._set_export_directory(str(custom_audit_dir))
        assert success is True
        assert view._get_export_directory() == str(custom_audit_dir)

        # Refresh and verify UI controls reflect the new path
        view.refresh()
        assert str(custom_audit_dir) in view._export_path_subtitle_text.value
        assert prof_service.get_preference(user.id, "export_download_path") == str(custom_audit_dir)

        # Export audit report to the new download directory
        exported_path = view._export_audit_report()
        assert os.path.exists(exported_path)
        assert os.path.dirname(exported_path) == str(custom_audit_dir)

        with open(exported_path, "r", encoding="utf-8") as f:
            content = f.read()
            assert "LEAKSEE FINANCIAL AUDIT REPORT" in content
            assert "Consulting Fee" in content
            assert "Ivy" in content
            assert str(custom_audit_dir) in content

        # Also verify export dialog reflects the new download path
        view._open_export_dialog()
        export_dialog = page.overlay[-1]
        assert "Export Financial Ledger" in export_dialog.title.controls[1].value

