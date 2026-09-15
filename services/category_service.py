"""
Spendora — Category service.

Manages category and subcategory CRUD, seeding from profession suggestions,
and the AI-suggestion acceptance flow.

Key invariant: AI suggestions and system-seeded categories are NEVER applied
automatically. The user must explicitly accept them (via the onboarding flow
or the Personalization screen).
"""

from __future__ import annotations

import logging
from typing import List, Optional

from database.database import get_session
from database.models import Category, CategorySource, Subcategory
from database.repositories.category_repository import CategoryRepository
from utils.validators import validate_category_name
from config.settings import PROFESSION_CATEGORY_SUGGESTIONS

logger = logging.getLogger(__name__)


class CategoryService:
    """Service for category and subcategory operations."""

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    def list_categories(self, user_id: int) -> List[Category]:
        """Return all active categories for a user (with subcategories loaded)."""
        with get_session() as session:
            repo = CategoryRepository(session)
            cats = repo.list_for_user(user_id, active_only=True)
            # Expunge all to make usable outside session, filtering to active subcategories.
            for cat in cats:
                active_subs = [s for s in cat.subcategories if s.is_active]
                session.expunge(cat)
                cat.subcategories = active_subs
            return cats

    def get_category(self, category_id: int) -> Optional[Category]:
        """Return a single category by id, or None."""
        with get_session() as session:
            repo = CategoryRepository(session)
            cat = repo.get_by_id(category_id)
            if cat:
                session.expunge(cat)
            return cat

    # ------------------------------------------------------------------
    # Suggestions
    # ------------------------------------------------------------------

    def get_suggestions_for_profession(self, profession: str) -> List[dict]:
        """
        Return the list of category suggestion dicts for a given profession.

        Returns suggestion metadata only — nothing is written to the DB here.
        The user must explicitly accept suggestions via accept_suggestions().
        """
        return PROFESSION_CATEGORY_SUGGESTIONS.get(
            profession,
            PROFESSION_CATEGORY_SUGGESTIONS.get("Other", [])
        )

    def accept_suggestions(
        self,
        user_id: int,
        accepted_suggestions: List[dict],
        source: CategorySource = CategorySource.SYSTEM,
    ) -> List[Category]:
        """
        Persist accepted category suggestions.

        Each item in accepted_suggestions should be a dict matching the
        PROFESSION_CATEGORY_SUGGESTIONS format:
            {
                "name": str,
                "icon": str,
                "color": str,
                "subcategories": List[str],
            }

        Subcategory strings that were accepted are also persisted.
        """
        if not accepted_suggestions:
            return []

        categories: List[Category] = []

        with get_session() as session:
            repo = CategoryRepository(session)

            for suggestion in accepted_suggestions:
                name = validate_category_name(suggestion.get("name", ""))

                # Avoid duplicates: skip if a category with this name already exists.
                existing = repo.get_by_name(user_id, name)
                if existing is not None:
                    logger.info("Category %r already exists for user %d — skipping.", name, user_id)
                    categories.append(existing)
                    continue

                cat = Category(
                    user_id=user_id,
                    name=name,
                    color=suggestion.get("color"),
                    icon=suggestion.get("icon"),
                    source=source,
                    is_active=True,
                )
                repo.create(cat)

                # Persist accepted subcategories.
                sub_names: List[str] = suggestion.get("subcategories", [])
                for sub_name_raw in sub_names:
                    try:
                        sub_name = validate_category_name(sub_name_raw)
                    except ValueError:
                        logger.warning("Skipping invalid subcategory name %r", sub_name_raw)
                        continue

                    sub = Subcategory(
                        category_id=cat.id,
                        name=sub_name,
                        source=source,
                        is_active=True,
                    )
                    repo.create_subcategory(sub)

                categories.append(cat)

            session.commit()

            # Expunge for use outside session.
            for cat in categories:
                try:
                    for sub in cat.subcategories:
                        session.expunge(sub)
                    session.expunge(cat)
                except Exception:
                    pass  # Already expunged (duplicate branch).

        logger.info("Accepted %d category suggestions for user %d", len(categories), user_id)
        return categories

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    def create_category(
        self,
        user_id: int,
        name: str,
        color: Optional[str] = None,
        icon: Optional[str] = None,
    ) -> Category:
        """Create a user-defined category."""
        clean_name = validate_category_name(name)

        with get_session() as session:
            repo = CategoryRepository(session)

            existing = repo.get_by_name(user_id, clean_name)
            if existing is not None:
                raise ValueError(f"A category named '{clean_name}' already exists.")

            cat = Category(
                user_id=user_id,
                name=clean_name,
                color=color,
                icon=icon,
                source=CategorySource.USER,
                is_active=True,
            )
            repo.create(cat)
            session.commit()
            session.refresh(cat)
            session.expunge(cat)

        return cat

    def create_subcategory(self, category_id: int, name: str) -> Subcategory:
        """Create a user-defined subcategory under an existing category."""
        clean_name = validate_category_name(name)

        with get_session() as session:
            repo = CategoryRepository(session)

            cat = repo.get_by_id(category_id)
            if cat is None:
                raise ValueError(f"Category {category_id} not found.")

            sub = Subcategory(
                category_id=category_id,
                name=clean_name,
                source=CategorySource.USER,
                is_active=True,
            )
            repo.create_subcategory(sub)
            session.commit()
            session.refresh(sub)
            session.expunge(sub)

        return sub

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update_category(
        self,
        category_id: int,
        name: Optional[str] = None,
        color: Optional[str] = None,
        icon: Optional[str] = None,
    ) -> Category:
        """Update category name, color, and/or icon."""
        with get_session() as session:
            repo = CategoryRepository(session)
            cat = repo.get_by_id(category_id)
            if cat is None:
                raise ValueError(f"Category {category_id} not found.")

            if name is not None:
                clean_name = validate_category_name(name)
                existing = repo.get_by_name(cat.user_id, clean_name)
                if existing is not None and existing.id != category_id:
                    raise ValueError(f"A category named '{clean_name}' already exists.")
                cat.name = clean_name

            if color is not None:
                cat.color = color

            if icon is not None:
                cat.icon = icon

            repo.update(cat)
            session.commit()
            session.refresh(cat)
            session.expunge(cat)

        return cat

    def rename_category(self, category_id: int, new_name: str) -> Category:
        """Rename an existing category."""
        return self.update_category(category_id, name=new_name)

    def rename_subcategory(self, subcategory_id: int, new_name: str) -> Subcategory:
        """Rename an existing subcategory."""
        clean_name = validate_category_name(new_name)

        with get_session() as session:
            repo = CategoryRepository(session)
            sub = repo.get_subcategory_by_id(subcategory_id)
            if sub is None:
                raise ValueError(f"Subcategory {subcategory_id} not found.")
            sub.name = clean_name
            repo.update_subcategory(sub)
            session.commit()
            session.refresh(sub)
            session.expunge(sub)

        return sub

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    def delete_category(self, category_id: int, soft: bool = True) -> None:
        """
        Delete (or soft-delete) a category.
        Soft-delete preserves transaction history; hard-delete removes the record.
        """
        with get_session() as session:
            repo = CategoryRepository(session)
            cat = repo.get_by_id(category_id)
            if cat is None:
                raise ValueError(f"Category {category_id} not found.")
            if soft:
                repo.soft_delete(cat)
            else:
                repo.hard_delete(cat)
            session.commit()

    def delete_subcategory(self, subcategory_id: int, soft: bool = True) -> None:
        """Delete (or soft-delete) a subcategory."""
        with get_session() as session:
            repo = CategoryRepository(session)
            sub = repo.get_subcategory_by_id(subcategory_id)
            if sub is None:
                raise ValueError(f"Subcategory {subcategory_id} not found.")
            if soft:
                repo.soft_delete_subcategory(sub)
            else:
                repo.hard_delete_subcategory(sub)
            session.commit()

