"""
Spendora — CategoryBreakdownItem component.

Displays a single category's share in total expenses with:
- Category icon badge & name
- Transaction count
- Formatted total amount & percentage
- Horizontal distribution bar
"""

from __future__ import annotations

from kivy.metrics import dp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel

from components.distribution_bar import DistributionBar
from config.settings import APP_BG_CARD, APP_MUTED_TEXT, APP_TEXT
from utils.formatting import format_currency


class CategoryBreakdownItem(MDCard):
    """Row displaying a category's expenditure share, amount, and progress bar."""

    def __init__(
        self,
        category_name: str,
        amount_paise: int,
        percentage: float,
        transaction_count: int,
        color_hex: str = "#80CBC4",
        icon_name: str = "tag",
        currency: str = "INR",
        **kwargs,
    ) -> None:
        super().__init__(
            style="filled",
            md_bg_color=APP_BG_CARD,
            radius=[dp(12)],
            padding=[dp(14), dp(12), dp(14), dp(12)],
            size_hint_y=None,
            height=dp(70),
            **kwargs,
        )
        self._build(
            category_name=category_name,
            amount_paise=amount_paise,
            percentage=percentage,
            transaction_count=transaction_count,
            color_hex=color_hex,
            icon_name=icon_name,
            currency=currency,
        )

    def _build(
        self,
        category_name: str,
        amount_paise: int,
        percentage: float,
        transaction_count: int,
        color_hex: str,
        icon_name: str,
        currency: str,
    ) -> None:
        layout = MDBoxLayout(orientation="vertical", spacing=dp(8))

        # Top row: icon + name + count (left), percentage + amount (right)
        top_row = MDBoxLayout(orientation="horizontal", adaptive_height=True, spacing=dp(8))

        # Category icon symbol
        icon_box = MDCard(
            style="filled",
            md_bg_color=self._hex_to_rgba(color_hex, alpha=0.2),
            size_hint=(None, None),
            size=(dp(28), dp(28)),
            radius=[dp(14)],
            pos_hint={"center_y": 0.5},
        )
        icon_box.add_widget(
            MDLabel(
                text=self._icon_char(icon_name),
                halign="center",
                valign="middle",
                theme_text_color="Custom",
                text_color=self._hex_to_rgba(color_hex, alpha=1.0),
                font_style="Title",
                role="small",
            )
        )
        top_row.add_widget(icon_box)

        name_box = MDBoxLayout(orientation="horizontal", adaptive_height=True, spacing=dp(4), pos_hint={"center_y": 0.5})
        name_box.add_widget(
            MDLabel(
                text=category_name,
                font_style="Body",
                role="medium",
                adaptive_height=True,
                theme_text_color="Custom",
                text_color=APP_TEXT,
            )
        )
        name_box.add_widget(
            MDLabel(
                text=f"({transaction_count})",
                font_style="Body",
                role="small",
                adaptive_height=True,
                theme_text_color="Custom",
                text_color=APP_MUTED_TEXT,
            )
        )
        top_row.add_widget(name_box)

        top_row.add_widget(MDBoxLayout())  # Spacer

        amount_str = format_currency(amount_paise, currency)
        right_label = MDLabel(
            text=f"{percentage:.1f}% · {amount_str}",
            font_style="Body",
            role="medium",
            adaptive_height=True,
            halign="right",
            theme_text_color="Custom",
            text_color=APP_TEXT,
            pos_hint={"center_y": 0.5},
        )
        top_row.add_widget(right_label)

        layout.add_widget(top_row)

        # Bottom row: DistributionBar
        bar_color = self._hex_to_rgba(color_hex, alpha=0.9)
        dist_bar = DistributionBar(percentage=percentage, color_rgba=bar_color, bar_height=6.0)
        layout.add_widget(dist_bar)

        self.add_widget(layout)

    @staticmethod
    def _hex_to_rgba(hex_str: str, alpha: float = 1.0) -> tuple:
        hex_str = hex_str.lstrip("#")
        if len(hex_str) != 6:
            return (0.5, 0.5, 0.5, alpha)
        r = int(hex_str[0:2], 16) / 255.0
        g = int(hex_str[2:4], 16) / 255.0
        b = int(hex_str[4:6], 16) / 255.0
        return (r, g, b, alpha)

    @staticmethod
    def _icon_char(icon_name: str) -> str:
        _MAP = {
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
            "cash": "💰",
            "tag": "🏷",
        }
        return _MAP.get(icon_name, "🏷")

