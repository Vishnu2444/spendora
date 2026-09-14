"""
Spendora — Tests for financial calculations.

These tests verify that all arithmetic is deterministic and correct.
NO LLM is involved in any calculation tested here.
"""

from __future__ import annotations

import pytest
from decimal import Decimal
from datetime import date

from utils.validators import amount_to_paise, paise_to_amount
from utils.formatting import (
    format_currency,
    format_gain_loss_label,
    format_date_range,
    format_percentage,
)
from utils.date_utils import (
    days_in_range,
    date_range_this_month,
    date_range_last_month,
    date_range_today,
    date_range_yesterday,
)


# ---------------------------------------------------------------------------
# Core financial arithmetic (paise-based)
# ---------------------------------------------------------------------------

class TestFinancialArithmetic:
    """
    Test the fundamental financial calculations.
    All values are in integer paise to prevent floating-point errors.
    """

    def test_income_sum(self):
        """Total income = sum of all income transaction amounts."""
        incomes = [50_000_00, 5_000_00, 2_500_00]  # paise
        assert sum(incomes) == 57_500_00

    def test_expense_sum(self):
        """Total expenses = sum of all expense transaction amounts."""
        expenses = [10_000_00, 3_500_00, 750_00]
        assert sum(expenses) == 14_250_00

    def test_net_gain(self):
        """Net > 0 → GAIN."""
        total_income = 57_500_00
        total_expense = 14_250_00
        net = total_income - total_expense
        assert net == 43_250_00
        assert net > 0
        assert format_gain_loss_label(net) == "GAIN"

    def test_net_loss(self):
        """Net < 0 → LOSS."""
        total_income = 10_000_00
        total_expense = 15_000_00
        net = total_income - total_expense
        assert net == -5_000_00
        assert net < 0
        assert format_gain_loss_label(net) == "LOSS"

    def test_break_even(self):
        """Net == 0 → BREAK-EVEN."""
        total_income = 20_000_00
        total_expense = 20_000_00
        net = total_income - total_expense
        assert net == 0
        assert format_gain_loss_label(net) == "BREAK-EVEN"

    def test_zero_income_zero_expense(self):
        """Empty ledger → BREAK-EVEN."""
        assert format_gain_loss_label(0) == "BREAK-EVEN"

    def test_paise_arithmetic_no_float(self):
        """Verify no floating-point representation error in paise arithmetic."""
        # ₹0.10 + ₹0.20 should equal ₹0.30 exactly (no 0.30000000000000004).
        paise_010 = amount_to_paise(Decimal("0.10"))
        paise_020 = amount_to_paise(Decimal("0.20"))
        paise_030 = amount_to_paise(Decimal("0.30"))
        assert paise_010 + paise_020 == paise_030

    def test_large_amount_precision(self):
        """Large INR amounts should convert cleanly to paise."""
        amount = Decimal("99999.99")
        paise = amount_to_paise(amount)
        assert paise == 9_999_999
        assert paise_to_amount(paise) == amount


# ---------------------------------------------------------------------------
# gain/loss label
# ---------------------------------------------------------------------------

class TestGainLossLabel:

    def test_large_gain(self):
        assert format_gain_loss_label(1_000_000_00) == "GAIN"

    def test_one_paise_gain(self):
        assert format_gain_loss_label(1) == "GAIN"

    def test_one_paise_loss(self):
        assert format_gain_loss_label(-1) == "LOSS"

    def test_large_loss(self):
        assert format_gain_loss_label(-99_99_99_999) == "LOSS"


# ---------------------------------------------------------------------------
# Currency formatting
# ---------------------------------------------------------------------------

class TestCurrencyFormatting:

    def test_format_round_rupees(self):
        assert format_currency(100_00) == "₹100.00"

    def test_format_with_paise(self):
        assert format_currency(250_50) == "₹250.50"

    def test_format_thousands(self):
        assert format_currency(1_000_00) == "₹1,000.00"

    def test_format_lakhs_indian(self):
        # 1 lakh = ₹1,00,000 (Indian system)
        assert format_currency(1_00_000_00) == "₹1,00,000.00"

    def test_format_one_paise(self):
        assert format_currency(1) == "₹0.01"

    def test_format_zero(self):
        assert format_currency(0) == "₹0.00"

    def test_format_negative(self):
        result = format_currency(-500_00)
        assert "500.00" in result
        assert "₹" in result
        # Check minus sign (Unicode minus U+2212 or hyphen acceptable).
        assert result[0] in ("\u2212", "-")


# ---------------------------------------------------------------------------
# Date range helpers
# ---------------------------------------------------------------------------

class TestDaysInRange:

    def test_same_day(self):
        d = date(2026, 9, 14)
        assert days_in_range(d, d) == 1

    def test_full_month_september(self):
        assert days_in_range(date(2026, 9, 1), date(2026, 9, 30)) == 30

    def test_full_month_august(self):
        assert days_in_range(date(2026, 8, 1), date(2026, 8, 31)) == 31

    def test_invalid_range_returns_zero(self):
        assert days_in_range(date(2026, 9, 30), date(2026, 9, 1)) == 0

    def test_one_week(self):
        assert days_in_range(date(2026, 9, 1), date(2026, 9, 7)) == 7


class TestDateRangePresets:

    def test_today_range(self):
        start, end = date_range_today()
        assert start == end
        assert start == date.today()

    def test_yesterday_range(self):
        from datetime import timedelta
        start, end = date_range_yesterday()
        assert start == end
        assert start == date.today() - timedelta(days=1)

    def test_this_month_range(self):
        start, end = date_range_this_month()
        today = date.today()
        assert start.day == 1
        assert start.month == today.month
        assert start.year == today.year
        assert end == today

    def test_last_month_range(self):
        from datetime import timedelta
        start, end = date_range_last_month()
        assert start.day == 1
        assert start.month == end.month
        assert start.year == end.year
        # end + 1 day should be the 1st day of the next month
        next_day = end + timedelta(days=1)
        assert next_day.day == 1


# ---------------------------------------------------------------------------
# Percentage formatting
# ---------------------------------------------------------------------------

class TestPercentageFormatting:

    def test_half(self):
        assert format_percentage(0.5) == "50.0%"

    def test_full(self):
        assert format_percentage(1.0) == "100.0%"

    def test_zero(self):
        assert format_percentage(0.0) == "0.0%"

    def test_rounding(self):
        result = format_percentage(0.3333, decimals=1)
        assert result == "33.3%"

