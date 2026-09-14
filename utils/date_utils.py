"""
Spendora — Date utilities.

All date handling is timezone-naive and operates in local calendar dates.
This avoids timezone-related off-by-one bugs in financial period calculations.

The application records transaction_date as a Python date (no time component).
Timestamps (created_at, updated_at) use UTC datetime, but are for audit
purposes only — they do NOT affect financial period calculations.
"""

from __future__ import annotations

from datetime import date, timedelta, datetime, timezone
from typing import Tuple


# ---------------------------------------------------------------------------
# Today's date
# ---------------------------------------------------------------------------

def today() -> date:
    """Return today's local date. Central function makes mocking easy in tests."""
    return date.today()


def now_utc() -> datetime:
    """Return the current UTC datetime (timezone-naive, for DB storage)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ---------------------------------------------------------------------------
# Preset date ranges
# ---------------------------------------------------------------------------

def date_range_today() -> Tuple[date, date]:
    """Today only."""
    d = today()
    return d, d


def date_range_yesterday() -> Tuple[date, date]:
    """Yesterday only."""
    d = today() - timedelta(days=1)
    return d, d


def date_range_this_week() -> Tuple[date, date]:
    """Monday through today of the current ISO week."""
    d = today()
    start = d - timedelta(days=d.weekday())  # Monday
    return start, d


def date_range_this_month() -> Tuple[date, date]:
    """First day of the current month through today."""
    d = today()
    start = d.replace(day=1)
    return start, d


def date_range_last_month() -> Tuple[date, date]:
    """Full previous calendar month (1st to last day)."""
    d = today()
    first_this_month = d.replace(day=1)
    last_last_month = first_this_month - timedelta(days=1)
    first_last_month = last_last_month.replace(day=1)
    return first_last_month, last_last_month


def date_range_this_year() -> Tuple[date, date]:
    """1 January through today of the current year."""
    d = today()
    start = d.replace(month=1, day=1)
    return start, d


# ---------------------------------------------------------------------------
# Range validation helpers
# ---------------------------------------------------------------------------

def clamp_date_to_today(d: date) -> date:
    """Ensure a date is not in the future. Returns today if d is in the future."""
    return min(d, today())


def days_in_range(start: date, end: date) -> int:
    """Return the number of calendar days in the range [start, end], inclusive."""
    if end < start:
        return 0
    return (end - start).days + 1


def month_label(d: date) -> str:
    """Return a short label like 'Sep 2026' for grouping."""
    return d.strftime("%b %Y")


def week_label(d: date) -> str:
    """Return an ISO week label like 'W37 2026'."""
    iso = d.isocalendar()
    return f"W{iso[1]:02d} {iso[0]}"


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def parse_date(s: str) -> date:
    """
    Parse a date from a string. Accepts YYYY-MM-DD.
    Raises ValueError with a user-facing message on failure.

    For user input validation, prefer utils.validators.validate_date_string
    which returns a more user-friendly error message.
    """
    try:
        return datetime.strptime(s.strip(), "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"Invalid date '{s}'. Expected YYYY-MM-DD.")

