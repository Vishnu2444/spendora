"""
Spendora — Analytics Service.

High-level analytical computations over arbitrary date ranges:
- Period performance & comparison with preceding time windows
- Category spending distribution with exact percentage shares
- Time-series aggregation (daily/weekly trends)
- Spending pattern insights (peak days, largest purchases, velocity)

All monetary calculations remain 100% deterministic using integer paise.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

from database.database import get_session
from database.models import Category, Transaction, TransactionType
from database.repositories.transaction_repository import TransactionRepository
from services.calculation_service import CalculationService

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Service for financial performance analysis and visual distribution data."""

    def __init__(self) -> None:
        self._calculation_service = CalculationService()

    # ------------------------------------------------------------------
    # Date-Range Financial Performance & Period Comparison
    # ------------------------------------------------------------------

    def calculate_date_range_performance(
        self,
        user_id: int,
        start_date: date,
        end_date: date,
    ) -> Dict[str, Any]:
        """
        Compute comprehensive performance between ANY two dates (inclusive),
        along with comparison against the previous period of identical duration.
        """
        if start_date > end_date:
            raise ValueError(
                f"Start date ({start_date}) must not be after end date ({end_date})."
            )

        # Current period summary
        current = self._calculation_service.calculate_period_summary(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
        )

        # Calculate equivalent preceding time window
        days_in_period = (end_date - start_date).days + 1
        prev_end_date = start_date - timedelta(days=1)
        prev_start_date = prev_end_date - timedelta(days=days_in_period - 1)

        previous = self._calculation_service.calculate_period_summary(
            user_id=user_id,
            start_date=prev_start_date,
            end_date=prev_end_date,
        )

        # Period-over-period deltas
        income_delta = current["total_income_paise"] - previous["total_income_paise"]
        expense_delta = current["total_expenses_paise"] - previous["total_expenses_paise"]
        net_delta = current["net_paise"] - previous["net_paise"]

        # Percentage changes (safe division)
        expense_pct_change = self._compute_pct_change(
            previous["total_expenses_paise"], current["total_expenses_paise"]
        )
        income_pct_change = self._compute_pct_change(
            previous["total_income_paise"], current["total_income_paise"]
        )

        return {
            "start_date": start_date,
            "end_date": end_date,
            "days_count": days_in_period,
            "current": current,
            "previous": previous,
            "previous_period_range": (prev_start_date, prev_end_date),
            "deltas": {
                "income_delta_paise": income_delta,
                "expense_delta_paise": expense_delta,
                "net_delta_paise": net_delta,
                "expense_pct_change": expense_pct_change,
                "income_pct_change": income_pct_change,
            },
        }

    # ------------------------------------------------------------------
    # Category Spending Distribution
    # ------------------------------------------------------------------

    def get_category_spending_distribution(
        self,
        user_id: int,
        start_date: date,
        end_date: date,
    ) -> List[Dict[str, Any]]:
        """
        Return category-wise spending distribution with exact percentage shares,
        icon, and color details, ordered from highest expense to lowest.
        """
        if start_date > end_date:
            raise ValueError("start_date must not be after end_date")

        with get_session() as session:
            # Query all expense transactions in the period
            txns = (
                session.query(Transaction)
                .filter(Transaction.user_id == user_id)
                .filter(Transaction.transaction_type == TransactionType.EXPENSE)
                .filter(Transaction.transaction_date >= start_date)
                .filter(Transaction.transaction_date <= end_date)
                .all()
            )

            total_expenses_paise = sum(t.amount_paise for t in txns)

            # Group transactions by category
            category_data: Dict[Optional[int], Dict[str, Any]] = {}
            uncategorized_txns = []

            for t in txns:
                cat_id = t.category_id
                if cat_id is None:
                    uncategorized_txns.append(t)
                    continue

                if cat_id not in category_data:
                    cat = session.get(Category, cat_id)
                    category_data[cat_id] = {
                        "name": cat.name if cat else "Unknown",
                        "color": cat.color if cat and cat.color else "#9E9E9E",
                        "icon": cat.icon if cat and cat.icon else "tag",
                        "amount_paise": 0,
                        "transaction_count": 0,
                    }

                category_data[cat_id]["amount_paise"] += t.amount_paise
                category_data[cat_id]["transaction_count"] += 1

            results: List[Dict[str, Any]] = []

            for cat_id, data in category_data.items():
                pct = (
                    (data["amount_paise"] / total_expenses_paise * 100.0)
                    if total_expenses_paise > 0
                    else 0.0
                )
                results.append({
                    "category_id": cat_id,
                    "name": data["name"],
                    "color": data["color"],
                    "icon": data["icon"],
                    "amount_paise": data["amount_paise"],
                    "percentage": round(pct, 1),
                    "transaction_count": data["transaction_count"],
                })

            if uncategorized_txns:
                uncat_total = sum(t.amount_paise for t in uncategorized_txns)
                pct = (
                    (uncat_total / total_expenses_paise * 100.0)
                    if total_expenses_paise > 0
                    else 0.0
                )
                results.append({
                    "category_id": None,
                    "name": "Uncategorized",
                    "color": "#78909C",
                    "icon": "cash",
                    "amount_paise": uncat_total,
                    "percentage": round(pct, 1),
                    "transaction_count": len(uncategorized_txns),
                })

            # Sort by expenditure descending
            results.sort(key=lambda item: item["amount_paise"], reverse=True)
            return results

    # ------------------------------------------------------------------
    # Time-Series Aggregation
    # ------------------------------------------------------------------

    def get_time_series_trend(
        self,
        user_id: int,
        start_date: date,
        end_date: date,
    ) -> List[Dict[str, Any]]:
        """
        Return daily time series of income, expense, and net.
        """
        if start_date > end_date:
            raise ValueError("start_date must not be after end_date")

        with get_session() as session:
            repo = TransactionRepository(session)
            daily_rows = repo.get_daily_totals(user_id, start_date, end_date)

        # Build day map for all days in range
        day_map: Dict[date, Dict[str, int]] = {}
        curr = start_date
        while curr <= end_date:
            day_map[curr] = {"income_paise": 0, "expense_paise": 0, "net_paise": 0}
            curr += timedelta(days=1)

        for txn_date, txn_type, total_paise in daily_rows:
            if txn_date in day_map:
                if txn_type == TransactionType.INCOME:
                    day_map[txn_date]["income_paise"] = total_paise
                elif txn_type == TransactionType.EXPENSE:
                    day_map[txn_date]["expense_paise"] = total_paise

        series = []
        for d in sorted(day_map.keys()):
            inc = day_map[d]["income_paise"]
            exp = day_map[d]["expense_paise"]
            net = inc - exp
            series.append({
                "date": d,
                "income_paise": inc,
                "expense_paise": exp,
                "net_paise": net,
            })

        return series

    # ------------------------------------------------------------------
    # Spending Insights
    # ------------------------------------------------------------------

    def get_spending_insights(
        self,
        user_id: int,
        start_date: date,
        end_date: date,
    ) -> Dict[str, Any]:
        """
        Extract key financial insights for the selected date window:
        - Top category
        - Peak spending day
        - Largest single transaction
        - Average transaction size
        """
        if start_date > end_date:
            raise ValueError("start_date must not be after end_date")

        with get_session() as session:
            repo = TransactionRepository(session)

            # Largest expense
            largest_txn = repo.get_largest_expense(user_id, start_date, end_date)
            largest_dict = None
            if largest_txn:
                cat_name = largest_txn.category.name if largest_txn.category else "Uncategorized"
                largest_dict = {
                    "id": largest_txn.id,
                    "description": largest_txn.description or cat_name,
                    "amount_paise": largest_txn.amount_paise,
                    "date": largest_txn.transaction_date,
                    "category_name": cat_name,
                }

            # Peak spending day
            daily_rows = repo.get_daily_totals(user_id, start_date, end_date)
            peak_day: Optional[date] = None
            peak_amount = 0

            for txn_date, txn_type, total_paise in daily_rows:
                if txn_type == TransactionType.EXPENSE and total_paise > peak_amount:
                    peak_amount = total_paise
                    peak_day = txn_date

            # Top category
            top_cats = repo.get_category_breakdown(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date,
                transaction_type=TransactionType.EXPENSE,
                limit=1,
            )
            top_category_name = top_cats[0][0] if top_cats else None
            top_category_paise = top_cats[0][1] if top_cats else 0

            # Expense transaction count and average size
            expense_txns = repo.list_for_user(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date,
                transaction_type=TransactionType.EXPENSE,
            )
            total_exp = sum(t.amount_paise for t in expense_txns)
            avg_txn_size = (total_exp // len(expense_txns)) if expense_txns else 0

        return {
            "top_category_name": top_category_name,
            "top_category_paise": top_category_paise,
            "peak_day": peak_day,
            "peak_day_amount_paise": peak_amount,
            "largest_expense": largest_dict,
            "average_transaction_paise": avg_txn_size,
            "expense_transaction_count": len(expense_txns),
        }

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_pct_change(prior: int, current: int) -> Optional[float]:
        """
        Compute percentage change from prior to current.
        Returns None if prior was 0 and current > 0 (infinite increase),
        0.0 if both were 0, or signed float rounded to 1 decimal place.
        """
        if prior == 0:
            return 100.0 if current > 0 else 0.0
        pct = ((current - prior) / prior) * 100.0
        return round(pct, 1)

