"""
Spendora — Profile service.

Manages user profile creation, retrieval, and updates.
The service coordinates between repositories and performs validation.
All database access goes through the repository layer.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Optional

from database.database import get_session
from database.models import User
from database.repositories.user_repository import UserRepository
from utils.validators import (
    validate_name,
    validate_profession_text,
    validate_amount_string,
    amount_to_paise,
)
from config.settings import PROFESSIONS, DEFAULT_CURRENCY

logger = logging.getLogger(__name__)


class ProfileService:
    """
    Service for user profile operations.

    Example usage:
        service = ProfileService()
        user = service.create_user(
            name="Vichu",
            profession="Software Engineer",
        )
    """

    def get_current_user(self) -> Optional[User]:
        """
        Return the active user, or None if no profile exists yet.

        In Phase 1 the app is single-user. This returns the first user record.
        """
        with get_session() as session:
            repo = UserRepository(session)
            return repo.get_first_user()

    def has_user(self) -> bool:
        """Return True if at least one user profile exists."""
        with get_session() as session:
            repo = UserRepository(session)
            return repo.count() > 0

    def create_user(
        self,
        name: str,
        profession: str,
        profession_custom: Optional[str] = None,
        monthly_income_str: Optional[str] = None,
        fixed_expenses_str: Optional[str] = None,
        currency: str = DEFAULT_CURRENCY,
    ) -> User:
        """
        Create and persist a new user profile.

        Validates all inputs before writing to the database.
        Raises ValueError with user-facing messages on invalid input.
        """
        # Validate name.
        clean_name = validate_name(name, field="Name")

        # Validate profession.
        if profession not in PROFESSIONS:
            raise ValueError(
                f"'{profession}' is not a recognised profession. "
                f"Choose from: {', '.join(PROFESSIONS)}"
            )

        # Validate custom profession if "Other" was selected.
        clean_profession_custom: Optional[str] = None
        if profession == "Other":
            if not profession_custom or not profession_custom.strip():
                raise ValueError("Please specify your profession.")
            clean_profession_custom = validate_profession_text(profession_custom, field="Custom profession")

        # Validate optional monetary fields.
        monthly_income_paise: Optional[int] = None
        if monthly_income_str and monthly_income_str.strip():
            amount = validate_amount_string(monthly_income_str, currency)
            monthly_income_paise = amount_to_paise(amount, currency)

        fixed_expenses_paise: Optional[int] = None
        if fixed_expenses_str and fixed_expenses_str.strip():
            amount = validate_amount_string(fixed_expenses_str, currency)
            fixed_expenses_paise = amount_to_paise(amount, currency)

        # Validate currency.
        from config.settings import CURRENCY_MINOR_UNITS
        if currency not in CURRENCY_MINOR_UNITS:
            raise ValueError(f"Unsupported currency: {currency}")

        user = User(
            name=clean_name,
            profession=profession,
            profession_custom=clean_profession_custom,
            monthly_income_paise=monthly_income_paise,
            fixed_expenses_paise=fixed_expenses_paise,
            currency=currency,
            is_onboarding_complete=False,
        )

        with get_session() as session:
            repo = UserRepository(session)
            repo.create(user)
            session.commit()
            # Refresh to get populated id and timestamps.
            session.refresh(user)
            # Expunge so the object is usable outside the session.
            session.expunge(user)

        logger.info("Profile created for user id=%d", user.id)
        return user

    def mark_onboarding_complete(self, user_id: int) -> None:
        """Mark the user's onboarding as finished."""
        with get_session() as session:
            repo = UserRepository(session)
            user = repo.get_by_id(user_id)
            if user is None:
                raise ValueError(f"User {user_id} not found.")
            user.is_onboarding_complete = True
            session.commit()

    def update_profile(
        self,
        user_id: int,
        name: Optional[str] = None,
        currency: Optional[str] = None,
        monthly_income_str: Optional[str] = None,
        fixed_expenses_str: Optional[str] = None,
    ) -> User:
        """
        Update editable profile fields.
        Only fields passed as non-None are updated.
        """
        with get_session() as session:
            repo = UserRepository(session)
            user = repo.get_by_id(user_id)
            if user is None:
                raise ValueError(f"User {user_id} not found.")

            if name is not None:
                user.name = validate_name(name, field="Name")

            if currency is not None:
                from config.settings import CURRENCY_MINOR_UNITS
                if currency not in CURRENCY_MINOR_UNITS:
                    raise ValueError(f"Unsupported currency: {currency}")
                user.currency = currency

            cur = user.currency
            if monthly_income_str is not None:
                if monthly_income_str.strip():
                    user.monthly_income_paise = amount_to_paise(
                        validate_amount_string(monthly_income_str, cur), cur
                    )
                else:
                    user.monthly_income_paise = None

            if fixed_expenses_str is not None:
                if fixed_expenses_str.strip():
                    user.fixed_expenses_paise = amount_to_paise(
                        validate_amount_string(fixed_expenses_str, cur), cur
                    )
                else:
                    user.fixed_expenses_paise = None

            repo.update(user)
            session.commit()
            session.refresh(user)
            session.expunge(user)

        return user

