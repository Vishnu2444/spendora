"""
Spendora — Transaction repository.

Encapsulates all database access for Transaction records.
Provides filtered queries used by the calculation and analytics services.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import List, Optional

from sqlalchemy import and_, or_, func, case
from sqlalchemy.orm import Session, joinedload

from database.models import Transaction, TransactionType, Category

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
        search_term: Optional[str] = None,
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
        if search_term:
            search_pattern = f"%{search_term}%"
            q = q.filter(
                or_(
                    Transaction.description.ilike(search_pattern),
                    Transaction.notes.ilike(search_pattern),
                )
            )

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
        search_term: Optional[str] = None,
    ) -> int:
        """Return the count matching the given filters."""
        q = self._session.query(Transaction).filter(Transaction.user_id == user_id)
        if start_date is not None:
            q = q.filter(Transaction.transaction_date >= start_date)
        if end_date is not None:
            q = q.filter(Transaction.transaction_date <= end_date)
        if transaction_type is not None:
            q = q.filter(Transaction.transaction_type == transaction_type)
        if search_term:
            search_pattern = f"%{search_term}%"
            q = q.filter(
                or_(
                    Transaction.description.ilike(search_pattern),
                    Transaction.notes.ilike(search_pattern),
                )
            )
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

    def get_balance_before(self, user_id: int, before_date: date) -> int:
        """Return net balance (in paise) for all transactions BEFORE the given date.
        
        Income adds, expense subtracts. Returns 0 if no transactions.
        """
        result = (
            self._session.query(
                func.coalesce(
                    func.sum(
                        case(
                            (Transaction.transaction_type == TransactionType.INCOME, Transaction.amount_paise),
                            else_=-Transaction.amount_paise
                        )
                    ),
                    0
                )
            )
            .filter(Transaction.user_id == user_id)
            .filter(Transaction.transaction_date < before_date)
            .scalar()
        )
        return result or 0

    def get_category_breakdown(
        self,
        user_id: int,
        start_date: date,
        end_date: date,
        transaction_type: Optional[TransactionType] = None,
        limit: Optional[int] = None,
    ) -> list[tuple[str, int]]:
        """Return (category_name, total_paise) tuples ordered by total descending.
        
        Groups transactions by category for the given period.
        Transactions without a category are grouped as 'Uncategorized'.
        """
        q = (
            self._session.query(
                func.coalesce(Category.name, 'Uncategorized').label('category_name'),
                func.sum(Transaction.amount_paise).label('total_paise')
            )
            .select_from(Transaction)
            .outerjoin(Category, Transaction.category_id == Category.id)
            .filter(Transaction.user_id == user_id)
            .filter(Transaction.transaction_date >= start_date)
            .filter(Transaction.transaction_date <= end_date)
        )
        
        if transaction_type is not None:
            q = q.filter(Transaction.transaction_type == transaction_type)
            
        q = q.group_by(func.coalesce(Category.name, 'Uncategorized'))
        q = q.order_by(func.sum(Transaction.amount_paise).desc())
        
        if limit is not None:
            q = q.limit(limit)
            
        return q.all()

    def get_daily_totals(
        self,
        user_id: int,
        start_date: date,
        end_date: date,
    ) -> list[tuple[date, TransactionType, int]]:
        """Return (transaction_date, transaction_type, sum_paise) ordered by date ASC."""
        q = (
            self._session.query(
                Transaction.transaction_date,
                Transaction.transaction_type,
                func.sum(Transaction.amount_paise).label("total_paise"),
            )
            .filter(Transaction.user_id == user_id)
            .filter(Transaction.transaction_date >= start_date)
            .filter(Transaction.transaction_date <= end_date)
            .group_by(Transaction.transaction_date, Transaction.transaction_type)
            .order_by(Transaction.transaction_date.asc())
        )
        return q.all()

    def get_largest_expense(
        self,
        user_id: int,
        start_date: date,
        end_date: date,
    ) -> Optional[Transaction]:
        """Return the single expense transaction with the highest amount in the period."""
        return (
            self._session.query(Transaction)
            .options(
                joinedload(Transaction.category),
                joinedload(Transaction.subcategory),
            )
            .filter(Transaction.user_id == user_id)
            .filter(Transaction.transaction_type == TransactionType.EXPENSE)
            .filter(Transaction.transaction_date >= start_date)
            .filter(Transaction.transaction_date <= end_date)
            .order_by(Transaction.amount_paise.desc())
            .first()
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
