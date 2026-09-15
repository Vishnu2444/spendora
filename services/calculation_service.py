"""
Spendora — Calculation service.

Deterministic financial calculation engine. All arithmetic uses integer
paise to prevent floating-point errors. This module NEVER touches the
database directly — it operates on data fetched by repositories.

Design decisions:
- Opening balance = net of all transactions BEFORE the period start.
- Closing balance = opening balance + net of the period.
- Average daily expense = total_expenses / days_in_period (integer division in paise).
- Status: GAIN if net > 0, LOSS if net < 0, BREAK-EVEN if net == 0.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

from database.database import get_session
from database.models import TransactionType
from database.repositories.transaction_repository import TransactionRepository

logger = logging.getLogger(__name__)


class CalculationService:
    """Deterministic financial summary calculations."""

    def calculate_period_summary(
        self,
        user_id: int,
        start_date: date,
        end_date: date,
    ) -> Dict[str, Any]:
        """
        Calculate a full financial summary for a date range.

        Returns a dict with:
            total_income_paise: int
            total_expenses_paise: int
            net_paise: int  (income - expenses)
            status: str  ("GAIN" | "LOSS" | "BREAK-EVEN")
            opening_balance_paise: int  (net of all transactions before start_date)
            closing_balance_paise: int  (opening + net)
            avg_daily_expense_paise: int
            transaction_count: int
        """
        if start_date > end_date:
            raise ValueError(
                f"Start date ({start_date}) must not be after end date ({end_date})."
            )

        with get_session() as session:
            repo = TransactionRepository(session)

            # Fetch all transactions in the period.
            income_txns = repo.list_for_user(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date,
                transaction_type=TransactionType.INCOME,
            )
            expense_txns = repo.list_for_user(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date,
                transaction_type=TransactionType.EXPENSE,
            )

            total_income = sum(t.amount_paise for t in income_txns)
            total_expenses = sum(t.amount_paise for t in expense_txns)
            net = total_income - total_expenses

            # Opening balance = net of everything before start_date.
            opening_balance = repo.get_balance_before(user_id, start_date)
            closing_balance = opening_balance + net

            # Count all transactions in the period.
            transaction_count = repo.count_for_user(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date,
            )

            # Average daily expense.
            days_in_period = (end_date - start_date).days + 1  # inclusive
            avg_daily_expense = total_expenses // days_in_period if days_in_period > 0 else 0

            # Status classification.
            if net > 0:
                status = "GAIN"
            elif net < 0:
                status = "LOSS"
            else:
                status = "BREAK-EVEN"

        return {
            "total_income_paise": total_income,
            "total_expenses_paise": total_expenses,
            "net_paise": net,
            "status": status,
            "opening_balance_paise": opening_balance,
            "closing_balance_paise": closing_balance,
            "avg_daily_expense_paise": avg_daily_expense,
            "transaction_count": transaction_count,
        }

    def calculate_current_balance(self, user_id: int) -> int:
        """
        Return the all-time net balance in paise.

        Equivalent to get_balance_before(user_id, far_future_date).
        Positive = surplus, negative = deficit.
        """
        # Use a date far in the future to include ALL transactions.
        far_future = date(9999, 12, 31)
        with get_session() as session:
            repo = TransactionRepository(session)
            return repo.get_balance_before(user_id, far_future)

    def get_top_expense_categories(
        self,
        user_id: int,
        start_date: date,
        end_date: date,
        limit: int = 5,
    ) -> List[Tuple[str, int]]:
        """
        Return top expense categories as (category_name, total_paise) tuples.

        Ordered by total descending. Useful for pie charts and summaries.
        """
        if start_date > end_date:
            raise ValueError(
                f"Start date ({start_date}) must not be after end date ({end_date})."
            )

        with get_session() as session:
            repo = TransactionRepository(session)
            return repo.get_category_breakdown(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date,
                transaction_type=TransactionType.EXPENSE,
                limit=limit,
            )
