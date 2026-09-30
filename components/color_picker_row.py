"""
Spendora — ColorPickerRow component (Flet).

A horizontal row of clickable color swatches for category customization.
"""

from __future__ import annotations

from typing import Callable, Optional

import flet as ft

# Predefined colour palette for categories.
_PALETTE = [
    "#FF6B6B", "#4ECDC4", "#45B7D1", "#F7DC6F",
    "#BB8FCE", "#82E0AA", "#F0B27A", "#5DADE2",
    "#1ABC9C", "#A9DFBF", "#2ECC71", "#E74C3C",
]


def build_color_picker_row(
    selected_color: str = "#4ECDC4",
    on_color_selected: Optional[Callable[[str], None]] = None,
) -> ft.Row:
    """Build a horizontal row of clickable color swatch circles."""
    swatches = []
    for color in _PALETTE:
        is_selected = color.upper() == selected_color.upper()
        swatches.append(
            ft.Container(
                width=32,
                height=32,
                border_radius=16,
                bgcolor=color,
                border=ft.Border.all(3, "#FFFFFF") if is_selected else None,
                on_click=lambda e, c=color: on_color_selected(c) if on_color_selected else None,
                tooltip=color,
            )
        )

    return ft.Row(wrap=True, spacing=8, run_spacing=8, controls=swatches)
