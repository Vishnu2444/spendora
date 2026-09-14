"""
Spendora — Transaction repository.

Encapsulates all database access for Transaction records.
Provides filtered queries used by the calculation and analytics services.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import List, Optional

from sqlalchemy import and_
from sqlalchemy.orm import Session, joinedload

from database.models import Transaction, TransactionType

logger = logging.getLogger(__name__)


class TransactionRepository:
    """Data access object for Transaction records."""

    def __init__(self, session: Session) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    def get_by_id(self, transaction_id: int) -> Optional[Transaction]:
        return self._session.get(Transaction, transaction_id)

    def list_for_user(
        self,
        user_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        transaction_type: Optional[TransactionType] = None,
        category_id: Optional[int] = None,
        subcategory_id: Optional[int] = None,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[Transaction]:
        """
        Flexible query for transactions with optional filters.

        Date boundaries are INCLUSIVE on both ends.
        Results are ordered by transaction_date DESC, then id DESC.
        """
        q = (
            self._session.query(Transaction)
            .options(
                joinedload(Transaction.category),
                joinedload(Transaction.subcategory),
            )
            .filter(Transaction.user_id == user_id)
        )

        if start_date is not None:
            q = q.filter(Transaction.transaction_date >= start_date)
        if end_date is not None:
            q = q.filter(Transaction.transaction_date <= end_date)
        if transaction_type is not None:
            q = q.filter(Transaction.transaction_type == transaction_type)
        if category_id is not None:
            q = q.filter(Transaction.category_id == category_id)
        if subcategory_id is not None:
            q = q.filter(Transaction.subcategory_id == subcategory_id)

        q = q.order_by(Transaction.transaction_date.desc(), Transaction.id.desc())

        if offset:
            q = q.offset(offset)
        if limit is not None:
            q = q.limit(limit)

        return q.all()

    def count_for_user(
        self,
        user_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        transaction_type: Optional[TransactionType] = None,
    ) -> int:
        """Return the count matching the given filters."""
        q = self._session.query(Transaction).filter(Transaction.user_id == user_id)
        if start_date is not None:
            q = q.filter(Transaction.transaction_date >= start_date)
        if end_date is not None:
            q = q.filter(Transaction.transaction_date <= end_date)
        if transaction_type is not None:
            q = q.filter(Transaction.transaction_type == transaction_type)
        return q.count()

    def get_recent(self, user_id: int, limit: int = 10) -> List[Transaction]:
        """Return the most recent N transactions for the dashboard."""
        return (
            self._session.query(Transaction)
            .options(
                joinedload(Transaction.category),
                joinedload(Transaction.subcategory),
            )
            .filter(Transaction.user_id == user_id)
            .order_by(Transaction.transaction_date.desc(), Transaction.id.desc())
            .limit(limit)
            .all()
        )

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    def create(self, transaction: Transaction) -> Transaction:
        self._session.add(transaction)
        self._session.flush()
        # NOTE: amount is intentionally NOT logged to avoid leaking financial data.
        logger.info(
            "Created transaction id=%d type=%s date=%s user_id=%d",
            transaction.id,
            transaction.transaction_type.value,
            transaction.transaction_date,
            transaction.user_id,
        )
        return transaction

    def update(self, transaction: Transaction) -> Transaction:
        self._session.flush()
        return transaction

    def delete(self, transaction: Transaction) -> None:
        self._session.delete(transaction)
        self._session.flush()
        logger.info("Deleted transaction id=%d", transaction.id)

