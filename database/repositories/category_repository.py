"""
Spendora — Category repository.

Encapsulates all database access for Category and Subcategory models.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from sqlalchemy.orm import Session, joinedload

from database.models import Category, CategorySource, Subcategory

logger = logging.getLogger(__name__)


class CategoryRepository:
    """Data access object for Category and Subcategory records."""

    def __init__(self, session: Session) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Category reads
    # ------------------------------------------------------------------

    def get_by_id(self, category_id: int) -> Optional[Category]:
        return self._session.get(Category, category_id)

    def list_for_user(self, user_id: int, active_only: bool = True) -> List[Category]:
        """Return all categories for a user, eagerly loading subcategories."""
        q = (
            self._session.query(Category)
            .options(joinedload(Category.subcategories))
            .filter(Category.user_id == user_id)
        )
        if active_only:
            q = q.filter(Category.is_active == True)  # noqa: E712
        return q.order_by(Category.name).all()

    def get_by_name(self, user_id: int, name: str) -> Optional[Category]:
        """Case-insensitive lookup by name for a given user."""
        return (
            self._session.query(Category)
            .filter(
                Category.user_id == user_id,
                Category.name.ilike(name),
                Category.is_active == True,  # noqa: E712
            )
            .first()
        )

    # ------------------------------------------------------------------
    # Category writes
    # ------------------------------------------------------------------

    def create(self, category: Category) -> Category:
        self._session.add(category)
        self._session.flush()
        logger.info("Created category id=%d name=%r user_id=%d", category.id, category.name, category.user_id)
        return category

    def bulk_create(self, categories: List[Category]) -> List[Category]:
        """Insert multiple categories in a single flush."""
        for cat in categories:
            self._session.add(cat)
        self._session.flush()
        return categories

    def update(self, category: Category) -> Category:
        self._session.flush()
        return category

    def soft_delete(self, category: Category) -> None:
        """Mark a category as inactive rather than physically deleting it."""
        category.is_active = False
        self._session.flush()

    def hard_delete(self, category: Category) -> None:
        """Physically delete a category (cascades to subcategories)."""
        self._session.delete(category)
        self._session.flush()

    # ------------------------------------------------------------------
    # Subcategory reads
    # ------------------------------------------------------------------

    def get_subcategory_by_id(self, subcategory_id: int) -> Optional[Subcategory]:
        return self._session.get(Subcategory, subcategory_id)

    def list_subcategories(self, category_id: int, active_only: bool = True) -> List[Subcategory]:
        q = self._session.query(Subcategory).filter(Subcategory.category_id == category_id)
        if active_only:
            q = q.filter(Subcategory.is_active == True)  # noqa: E712
        return q.order_by(Subcategory.name).all()

    # ------------------------------------------------------------------
    # Subcategory writes
    # ------------------------------------------------------------------

    def create_subcategory(self, subcategory: Subcategory) -> Subcategory:
        self._session.add(subcategory)
        self._session.flush()
        return subcategory

    def bulk_create_subcategories(self, subcategories: List[Subcategory]) -> List[Subcategory]:
        for sub in subcategories:
            self._session.add(sub)
        self._session.flush()
        return subcategories

    def update_subcategory(self, subcategory: Subcategory) -> Subcategory:
        self._session.flush()
        return subcategory

    def soft_delete_subcategory(self, subcategory: Subcategory) -> None:
        subcategory.is_active = False
        self._session.flush()

    def hard_delete_subcategory(self, subcategory: Subcategory) -> None:
        self._session.delete(subcategory)
        self._session.flush()

