"""
Spendora (Trackz) — CategoryManagementCard component (Flet).

Matches Google Stitch Personalization category cards:
- Clean card with 1px border (#E2E8F0)
- Icon circle + Name + Edit/Delete actions
- Subcategory / label chips
- Add subcategory action
"""

from __future__ import annotations

from typing import Callable, Optional

import flet as ft

from config.settings import (
    COLOR_ERROR,
    COLOR_ON_SURFACE,
    COLOR_OUTLINE_VARIANT,
    COLOR_PRIMARY_CONTAINER,
    COLOR_SECONDARY,
    COLOR_SURFACE_CARD,
    COLOR_SURFACE_CONTAINER,
)
from database.models import Category


def build_category_management_card(
    category: Category,
    on_edit: Optional[Callable[[Category], None]] = None,
    on_delete: Optional[Callable[[Category], None]] = None,
    on_add_subcategory: Optional[Callable[[Category], None]] = None,
    on_delete_subcategory: Optional[Callable[[int], None]] = None,
) -> ft.Container:
    """Build a Stitch-styled card for category and subcategory management."""
    from components.transaction_card import _resolve_icon

    flet_icon = _resolve_icon(category.icon or "payments")

    # Subcategory chips
    sub_chips = []
    active_subs = [s for s in (category.subcategories or []) if s.is_active]
    for sub in active_subs:
        sub_chips.append(
            ft.Chip(
                label=ft.Text(sub.name, size=12, color=COLOR_ON_SURFACE),
                bgcolor=COLOR_SURFACE_CONTAINER,
                border_side=ft.BorderSide(1, COLOR_OUTLINE_VARIANT),
                delete_icon_color=COLOR_ERROR,
                on_delete=lambda e, sid=sub.id: on_delete_subcategory(sid)
                if on_delete_subcategory
                else None,
            )
        )

    sub_row = (
        ft.Row(wrap=True, spacing=6, run_spacing=6, controls=sub_chips)
        if sub_chips
        else ft.Text(
            "No subcategories",
            color=COLOR_SECONDARY,
            size=12,
            italic=True,
        )
    )

    return ft.Container(
        bgcolor=COLOR_SURFACE_CARD,
        border=ft.Border.all(1, COLOR_OUTLINE_VARIANT),
        border_radius=12,
        padding=ft.Padding.all(16),
        content=ft.Column(
            spacing=12,
            controls=[
                # Header row: icon + name + actions
                ft.Row(
                    spacing=12,
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
                                        color=COLOR_PRIMARY_CONTAINER,
                                        size=20,
                                    ),
                                ),
                                ft.Text(
                                    category.name,
                                    color=COLOR_ON_SURFACE,
                                    size=16,
                                    weight=ft.FontWeight.W_600,
                                ),
                            ],
                        ),
                        ft.Row(
                            spacing=4,
                            controls=[
                                ft.IconButton(
                                    icon=ft.Icons.EDIT_OUTLINED,
                                    icon_color=COLOR_SECONDARY,
                                    icon_size=18,
                                    tooltip="Edit Category",
                                    on_click=lambda e: on_edit(category)
                                    if on_edit
                                    else None,
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.DELETE_OUTLINE,
                                    icon_color=COLOR_ERROR,
                                    icon_size=18,
                                    tooltip="Delete Category",
                                    on_click=lambda e: on_delete(category)
                                    if on_delete
                                    else None,
                                ),
                            ],
                        ),
                    ],
                ),
                # Subcategories list
                sub_row,
                # Add subcategory link
                ft.Row(
                    controls=[
                        ft.TextButton(
                            text="+ Add Label",
                            style=ft.ButtonStyle(
                                color=COLOR_PRIMARY_CONTAINER,
                            ),
                            on_click=lambda e: on_add_subcategory(category)
                            if on_add_subcategory
                            else None,
                        ),
                    ]
                ),
            ],
        ),
    )
