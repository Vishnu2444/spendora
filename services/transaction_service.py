"""
Spendora — Transaction service.

Complete CRUD API for financial transactions. Handles input validation,
business rules, and database coordination.

All amounts are validated and converted to paise internally.
"""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal
from typing import List, Optional

from database.database import get_session
from database.models import Category, Subcategory, Transaction, TransactionType
from database.repositories.transaction_repository import TransactionRepository
from utils.validators import (
    validate_amount_string,
    amount_to_paise,
    validate_description,
)

logger = logging.getLogger(__name__)


class TransactionService:
    """Service for transaction CRUD operations with full validation."""

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    def create_transaction(
        self,
        user_id: int,
        transaction_type: str,
        amount_str: str,
        transaction_date: date,
        category_id: Optional[int] = None,
        subcategory_id: Optional[int] = None,
        description: Optional[str] = None,
        notes: Optional[str] = None,
        currency: str = "INR",
    ) -> Transaction:
        """
        Create a new transaction with full validation.

        Args:
            user_id: The owning user's ID.
            transaction_type: "INCOME" or "EXPENSE" (case-insensitive).
            amount_str: User-entered amount string (e.g., "250.50").
            transaction_date: Date of the transaction.
            category_id: Optional category foreign key.
            subcategory_id: Optional subcategory foreign key.
            description: Optional short description.
            notes: Optional longer notes.
            currency: Currency code for amount parsing.

        Returns:
            The persisted Transaction with a valid ID.

        Raises:
            ValueError: On invalid input.
        """
        # Validate transaction type.
        txn_type = self._validate_transaction_type(transaction_type)

        # Validate and convert amount.
        amount_decimal = validate_amount_string(amount_str, currency)
        amount_paise = amount_to_paise(amount_decimal, currency)

        # Validate description and notes.
        clean_description = validate_description(description, max_length=255)
        clean_notes = validate_description(notes, max_length=1000)

        # Validate date is not absurdly in the future (>1 year).
        self._validate_transaction_date(transaction_date)

        with get_session() as session:
            repo = TransactionRepository(session)

            # Validate category and subcategory exist and belong to the user.
            if category_id is not None:
                self._validate_category(session, category_id, user_id)
            if subcategory_id is not None:
                self._validate_subcategory(session, subcategory_id, category_id)

            txn = Transaction(
                user_id=user_id,
                transaction_type=txn_type,
                amount_paise=amount_paise,
                transaction_date=transaction_date,
                category_id=category_id,
                subcategory_id=subcategory_id,
                description=clean_description,
                notes=clean_notes,
            )
            repo.create(txn)
            session.commit()
            session.refresh(txn)
            session.expunge(txn)

        logger.info(
            "Transaction created: id=%d type=%s date=%s",
            txn.id, txn.transaction_type.value, txn.transaction_date,
        )
        return txn

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_transaction(self, transaction_id: int) -> Optional[Transaction]:
        """Fetch a single transaction by ID, or None."""
        with get_session() as session:
            repo = TransactionRepository(session)
            txn = repo.get_by_id(transaction_id)
            if txn is not None:
                session.expunge(txn)
            return txn

    def list_transactions(
        self,
        user_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        transaction_type: Optional[str] = None,
        category_id: Optional[int] = None,
        search_term: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[Transaction]:
        """
        List transactions with optional filters.

        Returns transactions ordered by date DESC, id DESC.
        """
        txn_type = None
        if transaction_type is not None:
            txn_type = self._validate_transaction_type(transaction_type)

        with get_session() as session:
            repo = TransactionRepository(session)
            txns = repo.list_for_user(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date,
                transaction_type=txn_type,
                category_id=category_id,
                search_term=search_term,
                limit=limit,
                offset=offset,
            )
            # Expunge all so they're usable outside the session.
            for txn in txns:
                session.expunge(txn)
            return txns

    def get_recent_transactions(
        self, user_id: int, limit: int = 10
    ) -> List[Transaction]:
        """Return the most recent N transactions for the dashboard."""
        with get_session() as session:
            repo = TransactionRepository(session)
            txns = repo.get_recent(user_id, limit=limit)
            for txn in txns:
                session.expunge(txn)
            return txns

    def count_transactions(
        self,
        user_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        transaction_type: Optional[str] = None,
        search_term: Optional[str] = None,
    ) -> int:
        """Return the count of transactions matching the filters."""
        txn_type = None
        if transaction_type is not None:
            txn_type = self._validate_transaction_type(transaction_type)

        with get_session() as session:
            repo = TransactionRepository(session)
            return repo.count_for_user(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date,
                transaction_type=txn_type,
                search_term=search_term,
            )

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update_transaction(
        self,
        transaction_id: int,
        user_id: int,
        transaction_type: Optional[str] = None,
        amount_str: Optional[str] = None,
        transaction_date: Optional[date] = None,
        category_id: Optional[int] = None,
        subcategory_id: Optional[int] = None,
        description: Optional[str] = None,
        notes: Optional[str] = None,
        currency: str = "INR",
        clear_category: bool = False,
        clear_subcategory: bool = False,
    ) -> Transaction:
        """
        Update an existing transaction. Only non-None fields are modified.

        Set clear_category=True to explicitly remove the category.
        Set clear_subcategory=True to explicitly remove the subcategory.

        Raises ValueError if the transaction doesn't exist or belongs to
        a different user.
        """
        with get_session() as session:
            repo = TransactionRepository(session)
            txn = repo.get_by_id(transaction_id)

            if txn is None:
                raise ValueError(f"Transaction {transaction_id} not found.")
            if txn.user_id != user_id:
                raise ValueError("Cannot modify another user's transaction.")

            if transaction_type is not None:
                txn.transaction_type = self._validate_transaction_type(transaction_type)

            if amount_str is not None:
                amount_decimal = validate_amount_string(amount_str, currency)
                txn.amount_paise = amount_to_paise(amount_decimal, currency)

            if transaction_date is not None:
                self._validate_transaction_date(transaction_date)
                txn.transaction_date = transaction_date

            if clear_category:
                txn.category_id = None
                txn.subcategory_id = None  # Subcategory depends on category.
            elif category_id is not None:
                self._validate_category(session, category_id, user_id)
                txn.category_id = category_id
                # Clear subcategory if category changed and new subcategory not specified.
                if subcategory_id is None and not clear_subcategory:
                    txn.subcategory_id = None

            if clear_subcategory:
                txn.subcategory_id = None
            elif subcategory_id is not None:
                effective_cat_id = category_id if category_id is not None else txn.category_id
                self._validate_subcategory(session, subcategory_id, effective_cat_id)
                txn.subcategory_id = subcategory_id

            # Description: pass explicit empty string "" to clear, None to keep.
            if description is not None:
                txn.description = validate_description(description, max_length=255)

            if notes is not None:
                txn.notes = validate_description(notes, max_length=1000)

            repo.update(txn)
            session.commit()
            session.refresh(txn)
            session.expunge(txn)

        logger.info("Transaction updated: id=%d", txn.id)
        return txn

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    def delete_transaction(self, transaction_id: int, user_id: int) -> None:
        """
        Delete a transaction by ID.

        Raises ValueError if the transaction doesn't exist or belongs
        to a different user.
        """
        with get_session() as session:
            repo = TransactionRepository(session)
            txn = repo.get_by_id(transaction_id)

            if txn is None:
                raise ValueError(f"Transaction {transaction_id} not found.")
            if txn.user_id != user_id:
                raise ValueError("Cannot delete another user's transaction.")

            repo.delete(txn)
            session.commit()

        logger.info("Transaction deleted: id=%d", transaction_id)

    # ------------------------------------------------------------------
    # Private validation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_transaction_type(raw: str) -> TransactionType:
        """Parse and validate a transaction type string."""
        upper = raw.strip().upper()
        try:
            return TransactionType(upper)
        except ValueError:
            raise ValueError(
                f"Invalid transaction type: '{raw}'. Must be 'INCOME' or 'EXPENSE'."
            )

    @staticmethod
    def _validate_transaction_date(d: date) -> None:
        """Ensure the date is not absurdly far in the future (>1 year)."""
        from datetime import timedelta
        from utils.date_utils import today

        max_future = today() + timedelta(days=365)
        if d > max_future:
            raise ValueError(
                f"Transaction date {d} is more than 1 year in the future."
            )

    @staticmethod
    def _validate_category(session, category_id: int, user_id: int) -> None:
        """Ensure the category exists and belongs to the user."""
        cat = session.get(Category, category_id)
        if cat is None:
            raise ValueError(f"Category {category_id} not found.")
        if cat.user_id != user_id:
            raise ValueError("Category does not belong to this user.")

    @staticmethod
    def _validate_subcategory(
        session, subcategory_id: int, category_id: Optional[int]
    ) -> None:
        """Ensure the subcategory exists and belongs to the expected category."""
        sub = session.get(Subcategory, subcategory_id)
        if sub is None:
            raise ValueError(f"Subcategory {subcategory_id} not found.")
        if category_id is not None and sub.category_id != category_id:
            raise ValueError(
                "Subcategory does not belong to the selected category."
            )
