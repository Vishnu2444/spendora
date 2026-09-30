"""
Spendora (Trackz) — Category Setup Screen (Flet Onboarding).
"""

from __future__ import annotations

from typing import Callable
import flet as ft

from config.settings import (
    COLOR_BACKGROUND,
    COLOR_ON_PRIMARY,
    COLOR_ON_SURFACE,
    COLOR_OUTLINE_VARIANT,
    COLOR_PRIMARY,
    COLOR_SECONDARY,
    COLOR_SURFACE_CARD,
)
from services.category_service import CategoryService
from services.profile_service import ProfileService


class CategorySetupView:
    """Optional onboarding category confirmation screen."""

    def __init__(self, on_finish: Callable[[], None]) -> None:
        self._on_finish = on_finish

    def build(self) -> ft.Control:
        return ft.Container(
            expand=True,
            bgcolor=COLOR_BACKGROUND,
            alignment=ft.Alignment.CENTER,
            padding=ft.Padding.all(20),
            content=ft.Container(
                bgcolor=COLOR_SURFACE_CARD,
                border=ft.Border.all(1, COLOR_OUTLINE_VARIANT),
                border_radius=20,
                padding=ft.Padding.all(28),
                content=ft.Column(
                    spacing=16,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, color=COLOR_PRIMARY, size=48),
                        ft.Text("Categories Ready", size=22, weight=ft.FontWeight.W_800, color=COLOR_PRIMARY),
                        ft.Text(
                            "Default categories tailored to your profession have been prepared.",
                            size=14,
                            color=COLOR_SECONDARY,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.ElevatedButton(
                            "Go to Dashboard",
                            bgcolor=COLOR_PRIMARY,
                            color=COLOR_ON_PRIMARY,
                            height=48,
                            border_radius=12,
                            on_click=lambda e: self._on_finish(),
                        ),
                    ],
                ),
            ),
        )
