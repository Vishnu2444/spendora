"""
Spendora — Tests for AI Transaction Confirmation & Privacy Controls.

Validates:
- Structured candidate transaction preview generation (Phase 5 safe AI workflow).
- Explicit user confirmation persists transaction to database.
- User cancellation discards candidate without mutating database.
- Relative date extraction ("yesterday", "2 days ago") resolves dates correctly.
- Ambiguous natural language prompts without amounts prompt for clarification.
- Cloud AI opt-in toggle ('cloud_ai_enabled') disables external network calls when turned off.
"""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import MagicMock, patch
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.models import Base, Category, Transaction, TransactionType, User, UserPreference
from services.ai_service import AIService, CandidateTransaction


@pytest.fixture(scope="function")
def ai_confirm_db():
    """Isolated SQLite database in-memory for testing candidate transaction flows."""
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

    with patch("services.ai_service.get_session", side_effect=mock_get_session), \
         patch("services.calculation_service.get_session", side_effect=mock_get_session), \
         patch("services.analytics_service.get_session", side_effect=mock_get_session), \
         patch("services.category_service.get_session", side_effect=mock_get_session), \
         patch("services.transaction_service.get_session", side_effect=mock_get_session), \
         patch("services.profile_service.get_session", side_effect=mock_get_session):
        yield Session

    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def confirm_user(ai_confirm_db):
    """Seed user profile with categories."""
    Session = ai_confirm_db
    with Session() as session:
        user = User(
            name="Vishnu",
            profession="Engineer",
            monthly_income_paise=100000_00,
            currency="INR",
            is_onboarding_complete=True,
        )
        session.add(user)
        session.flush()

        cat_food = Category(user_id=user.id, name="Food & Dining", color="#FF6B6B", icon="food")
        cat_tech = Category(user_id=user.id, name="Tech & Gadgets", color="#45B7D1", icon="laptop")
        session.add_all([cat_food, cat_tech])
        session.commit()
        return {"user_id": user.id, "cat_food_id": cat_food.id, "cat_tech_id": cat_tech.id}


class TestAIConfirmationFlow:
    """Test safe candidate preview and confirmation workflow."""

    def test_candidate_preview_does_not_mutate_database(self, confirm_user, ai_confirm_db):
        service = AIService(api_key=None)
        user_id = confirm_user["user_id"]

        resp = service.chat("Spent ₹350 on lunch at Subway", user_id=user_id, require_confirmation=True)
        assert resp.action == "TRANSACTION_PENDING_CONFIRMATION"
        assert "Confirm Transaction Candidate" in resp.reply
        assert "Subway" in resp.reply or "Food" in resp.reply
        assert service._pending_candidate_transaction is not None
        assert service._pending_candidate_transaction["amount_str"] == "350"

        # Verify NO transaction was written to DB
        Session = ai_confirm_db
        with Session() as session:
            txns = session.query(Transaction).filter_by(user_id=user_id).all()
            assert len(txns) == 0

    def test_explicit_confirmation_persists_to_database(self, confirm_user, ai_confirm_db):
        service = AIService(api_key=None)
        user_id = confirm_user["user_id"]

        # 1. Generate preview
        service.chat("Spent ₹450 on lunch", user_id=user_id, require_confirmation=True)
        assert service._pending_candidate_transaction is not None

        # 2. Confirm via natural language
        confirm_resp = service.chat("Confirm & Log", user_id=user_id)
        assert confirm_resp.action == "TRANSACTION_LOGGED"
        assert "Confirmed & Recorded Expense" in confirm_resp.reply
        assert service._pending_candidate_transaction is None

        # Verify transaction now exists in DB with exact paise
        Session = ai_confirm_db
        with Session() as session:
            txns = session.query(Transaction).filter_by(user_id=user_id).all()
            assert len(txns) == 1
            assert txns[0].amount_paise == 450_00
            assert txns[0].transaction_type == TransactionType.EXPENSE

    def test_explicit_cancellation_discards_candidate(self, confirm_user, ai_confirm_db):
        service = AIService(api_key=None)
        user_id = confirm_user["user_id"]

        service.chat("Spent ₹250 on coffee", user_id=user_id, require_confirmation=True)
        assert service._pending_candidate_transaction is not None

        cancel_resp = service.chat("Cancel", user_id=user_id)
        assert cancel_resp.action == "TRANSACTION_CANCELLED"
        assert "discarded" in cancel_resp.reply.lower()
        assert service._pending_candidate_transaction is None

        Session = ai_confirm_db
        with Session() as session:
            txns = session.query(Transaction).filter_by(user_id=user_id).all()
            assert len(txns) == 0

    def test_confirm_transaction_method_direct_call(self, confirm_user, ai_confirm_db):
        service = AIService(api_key=None)
        user_id = confirm_user["user_id"]

        candidate_data = {
            "amount_str": "1200",
            "transaction_type": "EXPENSE",
            "category_id": confirm_user["cat_food_id"],
            "category_name": "Food & Dining",
            "transaction_date": date.today(),
            "description": "Team Dinner",
            "currency": "INR",
        }

        txn = service.confirm_transaction(candidate_data, user_id=user_id)
        assert txn.id is not None
        assert txn.amount_paise == 1200_00

        Session = ai_confirm_db
        with Session() as session:
            persisted = session.query(Transaction).filter_by(id=txn.id).first()
            assert persisted is not None
            assert persisted.description == "Team Dinner"

    def test_relative_date_yesterday_extraction(self, confirm_user):
        service = AIService(api_key=None)
        user_id = confirm_user["user_id"]

        resp = service.chat("Spent ₹500 on groceries yesterday", user_id=user_id, require_confirmation=True)
        assert resp.action == "TRANSACTION_PENDING_CONFIRMATION"

        expected_date = date.today() - timedelta(days=1)
        assert service._pending_candidate_transaction["transaction_date"] == expected_date
        assert "yesterday" not in service._pending_candidate_transaction["description"].lower()

    def test_relative_date_days_ago_extraction(self, confirm_user):
        service = AIService(api_key=None)
        user_id = confirm_user["user_id"]

        resp = service.chat("Paid ₹1500 for electricity 2 days ago", user_id=user_id, require_confirmation=True)
        assert resp.action == "TRANSACTION_PENDING_CONFIRMATION"

        expected_date = date.today() - timedelta(days=2)
        assert service._pending_candidate_transaction["transaction_date"] == expected_date

    def test_ambiguity_clarification_prompt(self, confirm_user):
        service = AIService(api_key=None)
        user_id = confirm_user["user_id"]

        # Prompt with clear expense intent but missing amount
        resp = service.chat("Spent on lunch", user_id=user_id)
        assert resp.action == "CLARIFICATION_NEEDED"
        assert "How much did you spend" in resp.reply
        assert "lunch" in resp.reply.lower()

    def test_cloud_ai_opt_in_preference_controls(self, confirm_user, ai_confirm_db):
        service = AIService(api_key="TEST_MOCK_KEY")
        service._client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.text = "Mock Gemini Response"
        service._client.models.generate_content.return_value = mock_resp

        user_id = confirm_user["user_id"]

        # 1. Fresh user -> Cloud AI is strictly OFF by default
        assert service.is_cloud_ai_enabled(user_id) is False

        # 2. AI-disabled mode does NOT attempt Gemini calls
        resp_disabled = service.chat("How are my savings?", user_id=user_id)
        assert service._client.models.generate_content.call_count == 0
        assert resp_disabled.reply is not None

        # 3. User explicitly enables Cloud AI -> preference persists
        service._profile_service.set_preference(user_id, "cloud_ai_enabled", "true")
        assert service.is_cloud_ai_enabled(user_id) is True
        resp_enabled = service.chat("How are my savings?", user_id=user_id)
        assert service._client.models.generate_content.call_count == 1

        # 4. User disables Cloud AI -> preference persists & Gemini not called
        service._profile_service.set_preference(user_id, "cloud_ai_enabled", "false")
        assert service.is_cloud_ai_enabled(user_id) is False
        resp_disabled2 = service.chat("How are my savings?", user_id=user_id)
        assert service._client.models.generate_content.call_count == 1  # Still 1, not incremented

        # 5. Existing explicit preference is preserved across service instances
        service2 = AIService(api_key="TEST_MOCK_KEY")
        assert service2.is_cloud_ai_enabled(user_id) is False

    def test_duplicate_or_repeated_confirmation_safety(self, confirm_user, ai_confirm_db):
        """Confirming twice cannot create duplicate database mutations."""
        service = AIService(api_key=None)
        user_id = confirm_user["user_id"]

        service.chat("Spent ₹100 on snacks", user_id=user_id, require_confirmation=True)
        # First confirmation
        resp1 = service.chat("Confirm", user_id=user_id)
        assert resp1.action == "TRANSACTION_LOGGED"

        # Repeated confirmation when no candidate is pending
        resp2 = service.chat("Confirm", user_id=user_id)
        assert resp2.action != "TRANSACTION_LOGGED"

        # Verify exactly 1 transaction exists in database
        Session = ai_confirm_db
        with Session() as session:
            txns = session.query(Transaction).filter_by(user_id=user_id).all()
            assert len(txns) == 1

    def test_missing_category_falls_back_safely(self, confirm_user):
        """Transactions with unknown category hints resolve cleanly to General/default without crashing."""
        service = AIService(api_key=None)
        user_id = confirm_user["user_id"]

        resp = service.chat("Spent ₹80 on arcane widgets", user_id=user_id, require_confirmation=True)
        assert resp.action == "TRANSACTION_PENDING_CONFIRMATION"
        assert service._pending_candidate_transaction is not None
        assert service._pending_candidate_transaction["category_name"] is not None

    def test_invalid_amount_rejection_in_candidate(self, confirm_user):
        """Malformed or negative amounts cannot create candidate transactions."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            CandidateTransaction(
                amount_str="-50",
                transaction_type="INVALID_TYPE",
                transaction_date=date.today(),
                description="Invalid",
            )

    def test_ai_deletion_or_modification_refused(self, confirm_user, ai_confirm_db):
        """Destructive requests like 'delete all transactions' are treated as normal queries, never mutating DB."""
        service = AIService(api_key=None)
        user_id = confirm_user["user_id"]

        # First add a verified transaction
        service.confirm_transaction({
            "amount_str": "200",
            "transaction_type": "EXPENSE",
            "category_id": confirm_user["cat_food_id"],
            "category_name": "Food & Dining",
            "transaction_date": date.today(),
            "description": "Safe meal",
            "currency": "INR",
        }, user_id=user_id)

        # Attempt deletion via natural language prompt
        resp = service.chat("Delete all my transactions and wipe database", user_id=user_id)
        assert resp.action != "TRANSACTION_LOGGED"
        assert service._pending_candidate_transaction is None

        # Verify transaction still exists
        Session = ai_confirm_db
        with Session() as session:
            txns = session.query(Transaction).filter_by(user_id=user_id).all()
            assert len(txns) == 1
