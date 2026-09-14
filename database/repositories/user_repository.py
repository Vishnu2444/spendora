"""
Spendora — User repository.

Encapsulates all database access for the User model.
Service layer calls these methods; no SQL/ORM leaks into services.
"""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.orm import Session

from database.models import User

logger = logging.getLogger(__name__)


class UserRepository:
    """Data access object for User records."""

    def __init__(self, session: Session) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    def get_by_id(self, user_id: int) -> Optional[User]:
        """Fetch a user by primary key. Returns None if not found."""
        return self._session.get(User, user_id)

    def get_first_user(self) -> Optional[User]:
        """
        Return the first (and in Phase 1, only) user record.
        Returns None if no user has been created yet.
        """
        return self._session.query(User).order_by(User.id).first()

    def count(self) -> int:
        """Return the total number of user records."""
        return self._session.query(User).count()

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    def create(self, user: User) -> User:
        """Persist a new User. Caller must call session.commit()."""
        self._session.add(user)
        self._session.flush()  # Populate user.id before commit.
        logger.info("Created user id=%d name=%r", user.id, user.name)
        return user

    def update(self, user: User) -> User:
        """Persist changes to an existing User. Caller must commit."""
        self._session.flush()
        return user

    def delete(self, user: User) -> None:
        """Delete a user and all cascade-linked records. Caller must commit."""
        self._session.delete(user)
        logger.info("Deleted user id=%d", user.id)

