"""
Spendora (Trackz) — CategoryBreakdownItem component (Flet).

Renders a single category row in the spending distribution:
icon circle | name + count | amount + percentage | thin progress bar.
"""

from __future__ import annotations

import flet as ft

from config.settings import (
    COLOR_ON_SURFACE,
    COLOR_OUTLINE_VARIANT,
    COLOR_SECONDARY,
    COLOR_SURFACE_CARD,
    COLOR_SURFACE_CONTAINER,
)
from utils.formatting import format_currency


def build_category_breakdown_item(
    category_name: str,
    amount_paise: int,
    percentage: float,
    transaction_count: int,
    color_hex: str,
    icon_name: str,
    currency: str = "INR",
) -> ft.Container:
    """Build a Stitch-styled card showing a category's spending share."""
    from components.transaction_card import _resolve_icon

    flet_icon = _resolve_icon(icon_name)
    amount_str = format_currency(amount_paise, currency)
    pct_str = f"{percentage:.1f}%"
    count_str = f"{transaction_count} txn{'s' if transaction_count != 1 else ''}"

    return ft.Container(
        bgcolor=COLOR_SURFACE_CARD,
        border=ft.Border.all(1, COLOR_OUTLINE_VARIANT),
        border_radius=12,
        padding=ft.Padding.symmetric(horizontal=16, vertical=12),
        content=ft.Column(
            spacing=8,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Row(
                            spacing=12,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.Container(
                                    width=38,
                                    height=38,
                                    border_radius=10,
                                    bgcolor=COLOR_SURFACE_CONTAINER,
                                    alignment=ft.Alignment.CENTER,
                                    content=ft.Icon(
                                        flet_icon,
                                        color=COLOR_ON_SURFACE,
                                        size=18,
                                    ),
                                ),
                                ft.Column(
                                    spacing=2,
                                    controls=[
                                        ft.Text(
                                            category_name,
                                            color=COLOR_ON_SURFACE,
                                            size=14,
                                            weight=ft.FontWeight.W_600,
                                        ),
                                        ft.Text(
                                            count_str,
                                            color=COLOR_SECONDARY,
                                            size=11,
                                        ),
                                    ],
                                ),
                            ],
                        ),
                        ft.Column(
                            horizontal_alignment=ft.CrossAxisAlignment.END,
                            spacing=2,
                            controls=[
                                ft.Text(
                                    amount_str,
                                    color=COLOR_ON_SURFACE,
                                    size=14,
                                    weight=ft.FontWeight.W_700,
                                ),
                                ft.Text(
                                    pct_str,
                                    color=COLOR_SECONDARY,
                                    size=12,
                                    weight=ft.FontWeight.W_500,
                                ),
                            ],
                        ),
                    ],
                ),
                ft.ProgressBar(
                    value=percentage / 100.0 if percentage > 0 else 0.01,
                    color=color_hex or COLOR_ON_SURFACE,
                    bgcolor=COLOR_SURFACE_CONTAINER,
                    bar_height=4,
                    border_radius=2,
                ),
            ],
        ),
    )
