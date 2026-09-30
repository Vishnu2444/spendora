"""
Spendora (Trackz) — TransactionCard component (Flet).

Material 3 / Stitch aesthetic for displaying a single transaction:
- Category icon in soft `#EAEDFF` container
- Description & Category / Date metadata
- Color-coded tabular currency amount
"""

from __future__ import annotations

import logging
from typing import Callable, Optional

import flet as ft

from config.settings import (
    COLOR_ERROR,
    COLOR_ON_SURFACE,
    COLOR_OUTLINE_VARIANT,
    COLOR_PRIMARY,
    COLOR_SECONDARY,
    COLOR_SURFACE_CARD,
    COLOR_SURFACE_CONTAINER,
)
from database.models import Transaction, TransactionType
from utils.formatting import format_currency, format_date

logger = logging.getLogger(__name__)

# Map category icon names to Flet Material Icons
_ICON_MAP: dict[str, str] = {
    "food": ft.Icons.RESTAURANT,
    "restaurant": ft.Icons.RESTAURANT,
    "car": ft.Icons.DIRECTIONS_CAR,
    "transport": ft.Icons.DIRECTIONS_CAR,
    "train": ft.Icons.TRAIN,
    "bus": ft.Icons.DIRECTIONS_BUS,
    "home": ft.Icons.HOME,
    "housing": ft.Icons.HOME,
    "laptop": ft.Icons.LAPTOP,
    "cloud": ft.Icons.CLOUD,
    "book-open-variant": ft.Icons.MENU_BOOK,
    "television-play": ft.Icons.LIVE_TV,
    "shopping": ft.Icons.SHOPPING_BAG,
    "shopping_cart": ft.Icons.SHOPPING_BAG,
    "heart-pulse": ft.Icons.FAVORITE,
    "health": ft.Icons.FAVORITE,
    "lightning-bolt": ft.Icons.BOLT,
    "utilities": ft.Icons.BOLT,
    "piggy-bank": ft.Icons.SAVINGS,
    "savings": ft.Icons.SAVINGS,
    "wifi": ft.Icons.WIFI,
    "briefcase": ft.Icons.WORK,
    "work": ft.Icons.WORK,
    "cash": ft.Icons.PAYMENTS,
    "payments": ft.Icons.PAYMENTS,
    "salary": ft.Icons.PAYMENTS,
    "robot": ft.Icons.SMART_TOY,
    "smart_toy": ft.Icons.SMART_TOY,
}


def _resolve_icon(icon_name: str) -> str:
    return _ICON_MAP.get((icon_name or "").lower(), ft.Icons.PAYMENTS)


def build_transaction_card(
    transaction: Transaction,
    currency: str = "INR",
    on_tap: Optional[Callable[[Transaction], None]] = None,
) -> ft.Container:
    """Build a Stitch-styled transaction row card."""
    icon_name = "payments"
    category_name = "General"

    if transaction.category is not None:
        category_name = transaction.category.name
        if transaction.category.icon:
            icon_name = transaction.category.icon

    flet_icon = _resolve_icon(icon_name)

    is_income = transaction.transaction_type == TransactionType.INCOME
    sign = "+" if is_income else "-"
    amount_color = COLOR_PRIMARY if is_income else COLOR_ERROR
    amount_str = format_currency(transaction.amount_paise, currency)
    display_amount = f"{sign}{amount_str}"

    title = transaction.description or category_name
    date_str = format_date(transaction.transaction_date, style="short")
    subtitle = f"{category_name} • {date_str}" if transaction.description else date_str

    def _handle_click(e):
        if on_tap:
            on_tap(transaction)

    from config.theme_manager import theme_manager
    is_dark = theme_manager.is_dark()
    card_bg = "#151D30" if is_dark else COLOR_SURFACE_CARD
    border_col = "#222E48" if is_dark else COLOR_OUTLINE_VARIANT
    text_col = "#FFFFFF" if is_dark else COLOR_ON_SURFACE
    sub_col = "#94A3B8" if is_dark else "#64748B"
    # Stitch color matching for categories
    cat_color = getattr(transaction.category, "color", None) or (COLOR_PRIMARY if is_income else "#CA3513")
    icon_tint = f"{cat_color}22" if is_dark else f"{cat_color}18"

    return ft.Container(
        bgcolor=card_bg,
        border_radius=16,
        border=ft.Border.all(1, border_col),
        padding=ft.Padding.symmetric(horizontal=16, vertical=12),
        ink=True,
        on_click=_handle_click if on_tap else None,
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Row(
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        # Rounded category icon container with soft tint
                        ft.Container(
                            width=44,
                            height=44,
                            border_radius=14,
                            bgcolor=icon_tint,
                            alignment=ft.Alignment.CENTER,
                            content=ft.Icon(
                                flet_icon,
                                color=cat_color,
                                size=22,
                            ),
                        ),
                        # Title and Date
                        ft.Column(
                            spacing=2,
                            alignment=ft.MainAxisAlignment.CENTER,
                            controls=[
                                ft.Text(
                                    title,
                                    color=text_col,
                                    size=15,
                                    weight=ft.FontWeight.W_600,
                                    max_lines=1,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                ),
                                ft.Text(
                                    date_str,
                                    color=sub_col,
                                    size=12,
                                ),
                            ],
                        ),
                    ],
                ),
                # Amount and Category tag matching Stitch
                ft.Column(
                    spacing=2,
                    horizontal_alignment=ft.CrossAxisAlignment.END,
                    alignment=ft.MainAxisAlignment.CENTER,
                    controls=[
                        ft.Text(
                            display_amount,
                            color=text_col,
                            size=15,
                            weight=ft.FontWeight.W_700,
                        ),
                        ft.Text(
                            category_name.upper(),
                            color=cat_color,
                            size=10,
                            weight=ft.FontWeight.W_700,
                        ),
                    ],
                ),
            ],
        ),
    )
