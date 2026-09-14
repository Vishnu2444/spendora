"""
Spendora — Display formatting utilities.

Converts internal representations (paise integers, raw dates) into
user-facing strings. No business logic or database access here.
"""

from __future__ import annotations

from decimal import Decimal
from datetime import date, datetime
from typing import Optional


# ---------------------------------------------------------------------------
# Currency formatting
# ---------------------------------------------------------------------------

def format_currency(paise: int, currency: str = "INR") -> str:
    """
    Convert an integer paise value to a formatted currency string.

    Examples:
        format_currency(25050, "INR")  →  "₹250.50"
        format_currency(100000, "INR") →  "₹1,000.00"
        format_currency(-5000, "INR")  →  "−₹50.00"   (uses minus sign, not hyphen)
    """
    from config.settings import CURRENCY_SYMBOLS, CURRENCY_MINOR_UNITS

    symbol = CURRENCY_SYMBOLS.get(currency, currency)
    minor = CURRENCY_MINOR_UNITS.get(currency, 100)

    negative = paise < 0
    abs_paise = abs(paise)

    major = abs_paise // minor
    remainder = abs_paise % minor

    # Format major part with comma separators (Indian numbering for INR).
    if currency == "INR":
        major_str = _indian_number_format(major)
    else:
        major_str = f"{major:,}"

    amount_str = f"{major_str}.{remainder:02d}"
    formatted = f"{symbol}{amount_str}"

    if negative:
        # Use Unicode minus sign (U+2212) for clarity.
        formatted = f"\u2212{formatted}"

    return formatted


def _indian_number_format(n: int) -> str:
    """
    Format an integer using Indian numbering system.
    Examples: 1000 → "1,000", 100000 → "1,00,000", 10000000 → "1,00,00,000"
    """
    s = str(n)
    if len(s) <= 3:
        return s

    # Last 3 digits, then groups of 2.
    result = s[-3:]
    s = s[:-3]
    while s:
        result = s[-2:] + "," + result
        s = s[:-2]
    # Clean up leading comma if any.
    return result.lstrip(",")


def format_paise_as_decimal(paise: int, currency: str = "INR") -> str:
    """
    Return the numeric part only (no symbol), useful for editing fields.
    Example: 25050 → "250.50"
    """
    from config.settings import CURRENCY_MINOR_UNITS
    minor = CURRENCY_MINOR_UNITS.get(currency, 100)
    major = abs(paise) // minor
    remainder = abs(paise) % minor
    return f"{major}.{remainder:02d}"


# ---------------------------------------------------------------------------
# Date / time formatting
# ---------------------------------------------------------------------------

def format_date(d: date, style: str = "long") -> str:
    """
    Format a date object for display.

    Styles:
        "long"   → "14 September 2026"
        "short"  → "14 Sep 2026"
        "iso"    → "2026-09-14"
        "display"→ "Sep 14, 2026"
    """
    styles = {
        "long": "%d %B %Y",
        "short": "%d %b %Y",
        "iso": "%Y-%m-%d",
        "display": "%b %d, %Y",
    }
    fmt = styles.get(style, styles["display"])
    return d.strftime(fmt)


def format_datetime(dt: datetime, style: str = "display") -> str:
    """Format a datetime for display."""
    styles = {
        "display": "%b %d, %Y %I:%M %p",
        "iso": "%Y-%m-%dT%H:%M:%S",
        "time_only": "%I:%M %p",
    }
    fmt = styles.get(style, styles["display"])
    return dt.strftime(fmt)


def format_date_range(start: date, end: date) -> str:
    """Human-readable date range. E.g., '01–30 September 2026' or '28 Aug – 14 Sep 2026'."""
    if start.year == end.year and start.month == end.month:
        return f"{start.day:02d}–{end.day:02d} {start.strftime('%B %Y')}"
    if start.year == end.year:
        return f"{start.strftime('%d %b')} – {end.strftime('%d %b %Y')}"
    return f"{format_date(start, 'short')} – {format_date(end, 'short')}"


# ---------------------------------------------------------------------------
# Financial labels
# ---------------------------------------------------------------------------

def format_gain_loss_label(net_paise: int) -> str:
    """
    Return the correct financial status label.
        net > 0  → "GAIN"
        net < 0  → "LOSS"
        net == 0 → "BREAK-EVEN"
    """
    if net_paise > 0:
        return "GAIN"
    if net_paise < 0:
        return "LOSS"
    return "BREAK-EVEN"


def format_transaction_type(transaction_type: str) -> str:
    """Capitalize and return a display-friendly transaction type string."""
    return transaction_type.upper()


# ---------------------------------------------------------------------------
# Percentage formatting
# ---------------------------------------------------------------------------

def format_percentage(value: float, decimals: int = 1) -> str:
    """Format a float as a percentage string. E.g., 0.753 → '75.3%'."""
    return f"{value * 100:.{decimals}f}%"

