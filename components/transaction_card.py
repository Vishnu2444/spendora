"""
Spendora — TransactionCard component.

A reusable Material Design 3 card for displaying a single transaction.
Shows the category icon, description, date, and color-coded amount.

Usage:
    card = TransactionCard(
        transaction=txn_object,
        currency="INR",
        on_tap=lambda txn: print(f"Tapped {txn.id}"),
    )
"""

from __future__ import annotations

import logging
from typing import Callable, Optional

from kivy.metrics import dp
from kivy.properties import ObjectProperty
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel

from config.settings import (
    APP_BG_CARD,
    APP_TEXT,
    APP_MUTED_TEXT,
    APP_SUCCESS,
    APP_DANGER,
)
from database.models import Transaction, TransactionType
from utils.formatting import format_currency, format_date

logger = logging.getLogger(__name__)

# Default category icon/color when the transaction has no category.
_DEFAULT_ICON = "cash"
_DEFAULT_COLOR = "#9E9E9E"

# Map common category icons to their MDI names (already stored as MDI names in DB).
# No mapping needed — just use the icon field directly.


class TransactionCard(MDCard):
    """
    A single transaction display card.

    Displays:
    - Category icon circle (left)
    - Description + category name (center)
    - Amount (right, green for income, red for expense)
    - Date (below)
    """

    transaction = ObjectProperty(None)

    def __init__(
        self,
        transaction: Transaction,
        currency: str = "INR",
        on_tap: Optional[Callable[[Transaction], None]] = None,
        **kwargs,
    ) -> None:
        super().__init__(
            style="filled",
            md_bg_color=APP_BG_CARD,
            radius=[dp(14)],
            padding=[dp(14), dp(12), dp(14), dp(12)],
            size_hint_y=None,
            height=dp(72),
            ripple_behavior=True,
            **kwargs,
        )
        self.transaction = transaction
        self._currency = currency
        self._on_tap = on_tap

        if on_tap:
            self.bind(on_release=self._handle_tap)

        self._build(transaction)

    def _handle_tap(self, *args) -> None:
        if self._on_tap and self.transaction:
            self._on_tap(self.transaction)

    def _build(self, txn: Transaction) -> None:
        """Build the card layout."""
        row = MDBoxLayout(
            orientation="horizontal",
            spacing=dp(12),
        )

        # --- Icon circle ---
        icon_name = _DEFAULT_ICON
        icon_color_hex = _DEFAULT_COLOR
        category_name = "Uncategorized"

        if txn.category is not None:
            category_name = txn.category.name
            if txn.category.icon:
                icon_name = txn.category.icon
            if txn.category.color:
                icon_color_hex = txn.category.color

        icon_bg = self._hex_to_rgba(icon_color_hex, alpha=0.2)
        icon_fg = self._hex_to_rgba(icon_color_hex, alpha=1.0)

        icon_circle = MDCard(
            style="filled",
            md_bg_color=icon_bg,
            size_hint=(None, None),
            size=(dp(44), dp(44)),
            radius=[dp(22)],
            pos_hint={"center_y": 0.5},
        )
        icon_circle.add_widget(
            MDLabel(
                text=self._icon_char(icon_name),
                halign="center",
                valign="middle",
                theme_text_color="Custom",
                text_color=icon_fg,
                font_style="Title",
                role="medium",
            )
        )
        row.add_widget(icon_circle)

        # --- Center: Description + category ---
        center = MDBoxLayout(
            orientation="vertical",
            spacing=dp(2),
            pos_hint={"center_y": 0.5},
        )

        desc_text = txn.description or category_name
        center.add_widget(
            MDLabel(
                text=desc_text,
                font_style="Body",
                role="large",
                adaptive_height=True,
                theme_text_color="Custom",
                text_color=APP_TEXT,
                shorten=True,
                shorten_from="right",
            )
        )

        # Subtitle: category + date
        sub_parts = []
        if txn.description and txn.category:
            sub_parts.append(category_name)
        sub_parts.append(format_date(txn.transaction_date, style="short"))
        subtitle = " · ".join(sub_parts)

        center.add_widget(
            MDLabel(
                text=subtitle,
                font_style="Body",
                role="small",
                adaptive_height=True,
                theme_text_color="Custom",
                text_color=APP_MUTED_TEXT,
            )
        )
        row.add_widget(center)

        # --- Right: Amount ---
        is_income = txn.transaction_type == TransactionType.INCOME
        sign_prefix = "+" if is_income else "−"
        amount_color = APP_SUCCESS if is_income else APP_DANGER
        amount_text = format_currency(txn.amount_paise, self._currency)

        # Prepend sign (format_currency doesn't add + for positive).
        display_amount = f"{sign_prefix}{amount_text}" if is_income else f"−{amount_text}"
        # Avoid double minus — format_currency already adds minus for negative.
        # Since amount_paise is always positive, format_currency returns positive string.
        display_amount = f"{sign_prefix}{amount_text}"

        amount_label = MDLabel(
            text=display_amount,
            font_style="Body",
            role="large",
            adaptive_height=True,
            halign="right",
            theme_text_color="Custom",
            text_color=amount_color,
            size_hint_x=None,
            width=dp(100),
            pos_hint={"center_y": 0.5},
        )
        row.add_widget(amount_label)

        self.add_widget(row)

    @staticmethod
    def _hex_to_rgba(hex_str: str, alpha: float = 1.0) -> tuple:
        """Convert a hex color string (#RRGGBB) to an RGBA tuple."""
        hex_str = hex_str.lstrip("#")
        if len(hex_str) != 6:
            return (0.6, 0.6, 0.6, alpha)
        r = int(hex_str[0:2], 16) / 255
        g = int(hex_str[2:4], 16) / 255
        b = int(hex_str[4:6], 16) / 255
        return (r, g, b, alpha)

    @staticmethod
    def _icon_char(icon_name: str) -> str:
        """
        Return a display character for the icon.

        KivyMD's MDIcon uses icon fonts, but inside a plain MDLabel we use
        emoji/unicode fallbacks for simplicity. A full implementation would
        use MDIcon widget.
        """
        # Map common MDI icon names to emoji for quick display.
        _ICON_MAP = {
            "food": "🍽",
            "car": "🚗",
            "train": "🚆",
            "bus": "🚌",
            "home": "🏠",
            "laptop": "💻",
            "book-open-variant": "📚",
            "television-play": "🎬",
            "shopping": "🛍",
            "heart-pulse": "❤",
            "lightning-bolt": "⚡",
            "piggy-bank": "🐷",
            "wifi": "📶",
            "briefcase": "💼",
            "desk": "🪑",
            "stethoscope": "🩺",
            "cash": "💰",
            "tag-multiple": "🏷",
        }
        return _ICON_MAP.get(icon_name, "💰")
