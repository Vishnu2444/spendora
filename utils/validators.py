"""
Spendora — Input validators.

All validators operate on Python primitives and return clean values
or raise ValueError with user-facing messages.

No database or UI imports allowed here — pure business logic only.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from datetime import date, datetime
from typing import Optional


# ---------------------------------------------------------------------------
# Money validation
# ---------------------------------------------------------------------------

def validate_amount_string(raw: str, currency: str = "INR") -> Decimal:
    """
    Validate and parse a monetary amount string supplied by the user.

    Accepts:  "250", "250.50", "1,500.00", "1500"
    Rejects:  negative numbers, zero, non-numeric strings, excessively
              large values.

    Returns a Decimal with at most 2 decimal places.
    Raises ValueError with a user-facing message on failure.
    """
    if not raw or not raw.strip():
        raise ValueError("Amount cannot be empty.")

    # Remove thousands separators for convenience.
    cleaned = raw.strip().replace(",", "")

    try:
        amount = Decimal(cleaned)
    except InvalidOperation:
        raise ValueError(f"'{raw}' is not a valid amount. Please enter a number like 250 or 1500.50.")

    if amount <= 0:
        raise ValueError("Amount must be greater than zero.")

    # Sanity cap — ₹10 crore per single transaction (adjustable).
    MAX_AMOUNT = Decimal("10_00_00_000")
    if amount > MAX_AMOUNT:
        raise ValueError("Amount exceeds the maximum allowed per transaction.")

    # Ensure at most 2 decimal places.
    if amount != amount.quantize(Decimal("0.01")):
        raise ValueError("Amount cannot have more than 2 decimal places.")

    return amount.quantize(Decimal("0.01"))


def amount_to_paise(amount: Decimal, currency: str = "INR") -> int:
    """Convert a validated Decimal amount to integer minor units (paise for INR)."""
    from config.settings import CURRENCY_MINOR_UNITS
    minor = CURRENCY_MINOR_UNITS.get(currency, 100)
    return int(amount * minor)


def paise_to_amount(paise: int, currency: str = "INR") -> Decimal:
    """Convert integer minor units back to a Decimal amount."""
    from config.settings import CURRENCY_MINOR_UNITS
    minor = CURRENCY_MINOR_UNITS.get(currency, 100)
    return Decimal(paise) / Decimal(minor)


# ---------------------------------------------------------------------------
# Name validation
# ---------------------------------------------------------------------------

def validate_name(name: str, field: str = "Name") -> str:
    """
    Validate a user-supplied name field.

    - Must not be empty.
    - Must not exceed 100 characters.
    - Must not be only whitespace.
    - Allowed characters: letters, spaces, hyphens, apostrophes, dots.
    """
    if not name or not name.strip():
        raise ValueError(f"{field} cannot be empty.")

    stripped = name.strip()

    if len(stripped) > 100:
        raise ValueError(f"{field} must not exceed 100 characters.")

    if not re.match(r"^[A-Za-z\u0900-\u097F\s'\-\.]+$", stripped):
        raise ValueError(
            f"{field} contains invalid characters. "
            "Only letters, spaces, hyphens, apostrophes, and dots are allowed."
        )

    return stripped


def validate_profession_text(text: str, field: str = "Profession") -> str:
    """
    Validate a user-supplied custom profession.
    Allows letters, numbers, spaces, hyphens, slashes, ampersands, dots, and parentheses.
    """
    if not text or not text.strip():
        raise ValueError(f"{field} cannot be empty.")

    stripped = text.strip()

    if len(stripped) > 100:
        raise ValueError(f"{field} must not exceed 100 characters.")

    if not re.match(r"^[A-Za-z0-9\u0900-\u097F\s'\-\./&()]+$", stripped):
        raise ValueError(
            f"{field} contains invalid characters."
        )

    return stripped


# ---------------------------------------------------------------------------
# Date validation
# ---------------------------------------------------------------------------

def validate_date_string(raw: str) -> date:
    """
    Parse a date string in YYYY-MM-DD format.
    Raises ValueError with a user-facing message on failure.
    """
    if not raw or not raw.strip():
        raise ValueError("Date cannot be empty.")

    try:
        return datetime.strptime(raw.strip(), "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"'{raw}' is not a valid date. Use YYYY-MM-DD format (e.g. 2026-09-14).")


def validate_date_range(start: date, end: date) -> None:
    """
    Ensure start_date <= end_date.
    Raises ValueError with a user-facing message if the range is invalid.
    """
    if start > end:
        raise ValueError(
            f"Start date ({start}) must not be after end date ({end})."
        )


# ---------------------------------------------------------------------------
# Category / text validation
# ---------------------------------------------------------------------------

def validate_category_name(name: str) -> str:
    """
    Validate a category or subcategory name.

    - Must not be empty or whitespace.
    - Maximum 50 characters.
    - No control characters.
    """
    if not name or not name.strip():
        raise ValueError("Category name cannot be empty.")

    stripped = name.strip()

    if len(stripped) > 50:
        raise ValueError("Category name must not exceed 50 characters.")

    # Reject control characters.
    if re.search(r"[\x00-\x1f\x7f]", stripped):
        raise ValueError("Category name contains invalid characters.")

    return stripped


def validate_description(description: Optional[str], max_length: int = 255) -> Optional[str]:
    """
    Validate an optional transaction description.
    Returns None for empty/whitespace input, stripped string otherwise.
    """
    if not description:
        return None
    stripped = description.strip()
    if not stripped:
        return None
    if len(stripped) > max_length:
        raise ValueError(f"Description must not exceed {max_length} characters.")
    return stripped

