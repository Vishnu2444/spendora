"""
Spendora — Tests for input validators.

These tests run without any database or UI — pure Python.
"""

from __future__ import annotations

import pytest
from decimal import Decimal

from utils.validators import (
    validate_amount_string,
    validate_name,
    validate_date_string,
    validate_date_range,
    validate_category_name,
    validate_description,
    amount_to_paise,
    paise_to_amount,
)
from datetime import date


# ---------------------------------------------------------------------------
# Amount validation
# ---------------------------------------------------------------------------

class TestValidateAmountString:

    def test_valid_integer(self):
        assert validate_amount_string("1000") == Decimal("1000.00")

    def test_valid_decimal(self):
        assert validate_amount_string("250.50") == Decimal("250.50")

    def test_valid_with_commas(self):
        assert validate_amount_string("1,500.00") == Decimal("1500.00")

    def test_zero_rejected(self):
        with pytest.raises(ValueError, match="greater than zero"):
            validate_amount_string("0")

    def test_negative_rejected(self):
        with pytest.raises(ValueError, match="greater than zero"):
            validate_amount_string("-100")

    def test_empty_rejected(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_amount_string("")

    def test_whitespace_rejected(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_amount_string("   ")

    def test_text_rejected(self):
        with pytest.raises(ValueError, match="not a valid amount"):
            validate_amount_string("abc")

    def test_too_many_decimals_rejected(self):
        with pytest.raises(ValueError, match="2 decimal places"):
            validate_amount_string("100.999")

    def test_excessively_large_rejected(self):
        with pytest.raises(ValueError, match="maximum allowed"):
            validate_amount_string("999999999")

    def test_two_decimal_places_accepted(self):
        assert validate_amount_string("0.01") == Decimal("0.01")


# ---------------------------------------------------------------------------
# Paise conversion
# ---------------------------------------------------------------------------

class TestPaiseConversion:

    def test_amount_to_paise_whole(self):
        assert amount_to_paise(Decimal("100.00")) == 10000

    def test_amount_to_paise_fractional(self):
        assert amount_to_paise(Decimal("250.50")) == 25050

    def test_amount_to_paise_one_paise(self):
        assert amount_to_paise(Decimal("0.01")) == 1

    def test_paise_to_amount_round_trip(self):
        original = Decimal("1234.56")
        paise = amount_to_paise(original)
        assert paise_to_amount(paise) == original

    def test_paise_to_amount_zero(self):
        assert paise_to_amount(0) == Decimal("0.00")


# ---------------------------------------------------------------------------
# Name validation
# ---------------------------------------------------------------------------

class TestValidateName:

    def test_valid_simple_name(self):
        assert validate_name("Vichu") == "Vichu"

    def test_valid_name_with_spaces(self):
        assert validate_name("Vishnu Kumar") == "Vishnu Kumar"

    def test_valid_hyphenated(self):
        assert validate_name("Mary-Jane") == "Mary-Jane"

    def test_strips_whitespace(self):
        assert validate_name("  Vichu  ") == "Vichu"

    def test_empty_rejected(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_name("")

    def test_whitespace_only_rejected(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_name("   ")

    def test_too_long_rejected(self):
        with pytest.raises(ValueError, match="100 characters"):
            validate_name("A" * 101)

    def test_numbers_rejected(self):
        with pytest.raises(ValueError, match="invalid characters"):
            validate_name("Vichu123")


# ---------------------------------------------------------------------------
# Date validation
# ---------------------------------------------------------------------------

class TestValidateDateString:

    def test_valid_date(self):
        assert validate_date_string("2026-09-14") == date(2026, 9, 14)

    def test_invalid_format_rejected(self):
        with pytest.raises(ValueError, match="YYYY-MM-DD"):
            validate_date_string("14/09/2026")

    def test_empty_rejected(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_date_string("")

    def test_invalid_date_rejected(self):
        with pytest.raises(ValueError):
            validate_date_string("2026-13-01")  # Month 13.


class TestValidateDateRange:

    def test_valid_range(self):
        # Should not raise.
        validate_date_range(date(2026, 8, 1), date(2026, 8, 31))

    def test_same_date_valid(self):
        d = date(2026, 9, 14)
        validate_date_range(d, d)

    def test_invalid_range_raises(self):
        with pytest.raises(ValueError, match="Start date"):
            validate_date_range(date(2026, 9, 30), date(2026, 9, 1))


# ---------------------------------------------------------------------------
# Category name validation
# ---------------------------------------------------------------------------

class TestValidateCategoryName:

    def test_valid_name(self):
        assert validate_category_name("Food") == "Food"

    def test_strips_whitespace(self):
        assert validate_category_name("  Transport  ") == "Transport"

    def test_empty_rejected(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_category_name("")

    def test_too_long_rejected(self):
        with pytest.raises(ValueError, match="50 characters"):
            validate_category_name("A" * 51)

    def test_control_char_rejected(self):
        with pytest.raises(ValueError, match="invalid characters"):
            validate_category_name("Food\x00")


# ---------------------------------------------------------------------------
# Description validation
# ---------------------------------------------------------------------------

class TestValidateDescription:

    def test_valid_description(self):
        assert validate_description("Netflix subscription") == "Netflix subscription"

    def test_empty_returns_none(self):
        assert validate_description("") is None

    def test_none_returns_none(self):
        assert validate_description(None) is None

    def test_whitespace_returns_none(self):
        assert validate_description("   ") is None

    def test_too_long_rejected(self):
        with pytest.raises(ValueError, match="255 characters"):
            validate_description("A" * 256)

