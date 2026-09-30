"""
Spendora — Welcome Onboarding Screen (Flet).

Matches Google Stitch "SPENDORA · STEP 1 OF 2":
- Step tracker pill & 50% progress bar
- Title: "Welcome to SPENDORA 👋"
- Full Name with verified badge
- Profession selector chips (Software Engineer, Freelancer, Business Owner, etc.)
- 2-Column Age & Monthly Income
- City / Location
- Currency selector chips (₹ INR, $ USD, € EUR, £ GBP)
- 256-bit AES protection security badge
- "Continue to Dashboard" primary action
"""

from __future__ import annotations

import logging
from typing import Callable, Optional

import flet as ft

from config.settings import (
    COLOR_BACKGROUND,
    COLOR_CORAL_ACCENT,
    COLOR_EMERALD_ACCENT,
    COLOR_ERROR,
    COLOR_ON_PRIMARY,
    COLOR_ON_SURFACE,
    COLOR_ON_SURFACE_VARIANT,
    COLOR_OUTLINE,
    COLOR_OUTLINE_VARIANT,
    COLOR_PRIMARY,
    COLOR_PRIMARY_CONTAINER,
    COLOR_PRIMARY_FIXED,
    COLOR_SECONDARY,
    COLOR_SURFACE_CARD,
    COLOR_SURFACE_CONTAINER,
    COLOR_SURFACE_LOW,
    CURRENCY_SYMBOLS,
    DEFAULT_CURRENCY,
    PROFESSIONS,
)
from config.theme_manager import theme_manager
from services.profile_service import ProfileService

logger = logging.getLogger(__name__)


class WelcomeView:
    """Onboarding profile creation matching Google Stitch design."""

    def __init__(self, on_complete: Callable[[], None]) -> None:
        self._profile_service = ProfileService()
        self._on_complete = on_complete
        self._page: Optional[ft.Page] = None

        # Form values
        self._selected_profession = "Software Engineer"
        self._selected_currency = "INR"

        # Theme toggle icon
        self._theme_icon = ft.IconButton(
            icon=ft.Icons.LIGHT_MODE if theme_manager.is_dark() else ft.Icons.DARK_MODE,
            icon_color=COLOR_ON_SURFACE,
            icon_size=20,
            tooltip="Toggle Dark Mode",
            on_click=lambda e: theme_manager.toggle(self._page),
        )
        theme_manager.register_listener(self._on_theme_changed)

        # Controls
        self._name_field = ft.TextField(
            value="Vishnu",
            hint_text="Enter your full name",
            border_color=COLOR_OUTLINE_VARIANT,
            focused_border_color=COLOR_PRIMARY,
            border_radius=16,
            bgcolor=COLOR_SURFACE_CARD,
            text_style=ft.TextStyle(color=COLOR_ON_SURFACE, size=15, weight=ft.FontWeight.W_500),
            suffix=ft.Container(
                bgcolor=f"{COLOR_EMERALD_ACCENT}15",
                border_radius=12,
                padding=ft.Padding.all(4),
                content=ft.Icon(ft.Icons.CHECK, color=COLOR_EMERALD_ACCENT, size=16),
            ),
        )

        self._age_field = ft.TextField(
            value="26 yrs",
            hint_text="e.g. 26",
            border_color=COLOR_OUTLINE_VARIANT,
            focused_border_color=COLOR_PRIMARY,
            border_radius=16,
            bgcolor=COLOR_SURFACE_CARD,
            text_style=ft.TextStyle(color=COLOR_ON_SURFACE, size=14),
            suffix_icon=ft.Icons.CALENDAR_MONTH,
        )

        self._income_field = ft.TextField(
            value="₹ 60,000 / mo",
            hint_text="₹ Amount",
            border_color=COLOR_OUTLINE_VARIANT,
            focused_border_color=COLOR_PRIMARY,
            border_radius=16,
            bgcolor=COLOR_SURFACE_CARD,
            text_style=ft.TextStyle(color=COLOR_ON_SURFACE, size=14),
            suffix_icon=ft.Icons.TRENDING_UP,
        )

        self._city_field = ft.TextField(
            value="Bengaluru, India",
            hint_text="City, Country",
            border_color=COLOR_OUTLINE_VARIANT,
            focused_border_color=COLOR_PRIMARY,
            border_radius=16,
            bgcolor=COLOR_SURFACE_CARD,
            text_style=ft.TextStyle(color=COLOR_ON_SURFACE, size=14),
            prefix_icon=ft.Icons.LOCATION_ON,
            suffix_icon=ft.Icons.MY_LOCATION,
        )

        self._error_text = ft.Text("", color=COLOR_ERROR, size=12, visible=False)
        self._prof_chips_row = ft.Row(wrap=True, spacing=8, run_spacing=8)
        self._curr_chips_row = ft.Row(spacing=8)

    def set_page(self, page: ft.Page) -> None:
        self._page = page

    def _on_theme_changed(self, is_dark: bool) -> None:
        self._theme_icon.icon = ft.Icons.LIGHT_MODE if is_dark else ft.Icons.DARK_MODE
        self._theme_icon.icon_color = "#F8FAFC" if is_dark else COLOR_ON_SURFACE
        if hasattr(self, "_main_container") and self._main_container:
            self._main_container.bgcolor = "#090D16" if is_dark else COLOR_BACKGROUND
            try:
                self._main_container.update()
            except Exception:
                pass
        try:
            self._theme_icon.update()
        except Exception:
            pass

    def _select_profession(self, prof: str) -> None:
        self._selected_profession = prof
        self._build_prof_chips()
        try:
            self._prof_chips_row.update()
        except Exception:
            pass

    def _build_prof_chips(self) -> None:
        self._prof_chips_row.controls.clear()
        is_dark = theme_manager.is_dark()
        card_bg = "#151D30" if is_dark else COLOR_SURFACE_CARD
        border_col = "#222E48" if is_dark else COLOR_OUTLINE_VARIANT
        text_col = "#FFFFFF" if is_dark else COLOR_ON_SURFACE
        primary_accent = "#8B5CF6" if is_dark else COLOR_PRIMARY

        options = [
            ("Software Engineer", ft.Icons.CODE),
            ("Freelancer", ft.Icons.LAPTOP_CHROMEBOOK),
            ("Business Owner", ft.Icons.STOREFRONT),
            ("Doctor", ft.Icons.MEDICAL_SERVICES),
            ("Student", ft.Icons.SCHOOL),
            ("Others", ft.Icons.MORE_HORIZ),
        ]
        for name, icon in options:
            is_sel = name == self._selected_profession
            self._prof_chips_row.controls.append(
                ft.Container(
                    bgcolor=primary_accent if is_sel else card_bg,
                    border=None if is_sel else ft.Border.all(1, border_col),
                    border_radius=20,
                    padding=ft.Padding.symmetric(horizontal=14, vertical=8),
                    ink=True,
                    content=ft.Row(
                        spacing=6,
                        tight=True,
                        controls=[
                            ft.Icon(icon, size=16, color="#FFFFFF" if is_sel else text_col),
                            ft.Text(
                                name,
                                size=13,
                                weight=ft.FontWeight.W_600 if is_sel else ft.FontWeight.W_500,
                                color="#FFFFFF" if is_sel else text_col,
                            ),
                            *(
                                [ft.Icon(ft.Icons.CHECK, size=14, color="#FFFFFF")]
                                if is_sel
                                else []
                            ),
                        ],
                    ),
                    on_click=lambda e, n=name: self._select_profession(n),
                )
            )

    def _select_currency(self, curr: str) -> None:
        self._selected_currency = curr
        self._build_curr_chips()
        try:
            self._curr_chips_row.update()
        except Exception:
            pass

    def _build_curr_chips(self) -> None:
        self._curr_chips_row.controls.clear()
        is_dark = theme_manager.is_dark()
        card_bg = "#151D30" if is_dark else COLOR_SURFACE_CARD
        border_col = "#222E48" if is_dark else COLOR_OUTLINE_VARIANT
        text_col = "#FFFFFF" if is_dark else COLOR_ON_SURFACE
        primary_accent = "#8B5CF6" if is_dark else COLOR_PRIMARY

        currencies = [("INR", "₹"), ("USD", "$"), ("EUR", "€"), ("GBP", "£")]
        for code, sym in currencies:
            is_sel = code == self._selected_currency
            self._curr_chips_row.controls.append(
                ft.Container(
                    expand=True,
                    bgcolor=primary_accent if is_sel else card_bg,
                    border=None if is_sel else ft.Border.all(1, border_col),
                    border_radius=14,
                    padding=ft.Padding.symmetric(vertical=10),
                    alignment=ft.Alignment.CENTER,
                    ink=True,
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=4,
                        controls=[
                            ft.Text(
                                sym,
                                size=14,
                                weight=ft.FontWeight.W_800,
                                color="#FFFFFF" if is_sel else text_col,
                            ),
                            ft.Text(
                                code,
                                size=13,
                                weight=ft.FontWeight.W_600,
                                color="#FFFFFF" if is_sel else text_col,
                            ),
                            *(
                                [ft.Icon(ft.Icons.CHECK, size=14, color="#FFFFFF")]
                                if is_sel
                                else []
                            ),
                        ],
                    ),
                    on_click=lambda e, c=code: self._select_currency(c),
                )
            )

    def build(self) -> ft.Control:
        self._build_prof_chips()
        self._build_curr_chips()

        # Step Indicator Header
        step_pill = ft.Container(
            bgcolor=COLOR_SURFACE_CARD,
            border=ft.Border.all(1, COLOR_OUTLINE_VARIANT),
            border_radius=20,
            padding=ft.Padding.symmetric(horizontal=12, vertical=6),
            content=ft.Row(
                spacing=8,
                tight=True,
                controls=[
                    ft.Container(
                        width=8,
                        height=8,
                        border_radius=4,
                        bgcolor=COLOR_PRIMARY_CONTAINER,
                    ),
                    ft.Text(
                        "SPENDORA · STEP 1 OF 2",
                        size=11,
                        weight=ft.FontWeight.W_700,
                        color=COLOR_PRIMARY,
                    ),
                ],
            ),
        )

        header_row = ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                step_pill,
                self._theme_icon,
            ],
        )

        progress_track = ft.ProgressBar(
            value=0.5,
            color=COLOR_PRIMARY_CONTAINER,
            bgcolor=COLOR_SURFACE_CONTAINER,
            bar_height=5,
            border_radius=3,
        )

        # Title section
        title_section = ft.Column(
            spacing=6,
            controls=[
                ft.Row(
                    spacing=8,
                    controls=[
                        ft.Text(
                            "Welcome to SPENDORA",
                            size=24,
                            weight=ft.FontWeight.W_800,
                            color=COLOR_ON_SURFACE,
                        ),
                        ft.Text("👋", size=24),
                    ],
                ),
                ft.Text(
                    "Let's set up your personalized ledger and Spendora AI smart predictions.",
                    size=14,
                    color=COLOR_ON_SURFACE_VARIANT,
                ),
            ],
        )

        # 2-column Age & Income
        two_col_row = ft.Row(
            spacing=12,
            controls=[
                ft.Column(
                    expand=True,
                    spacing=6,
                    controls=[
                        ft.Text("Age (optional)", size=13, weight=ft.FontWeight.W_600, color=COLOR_ON_SURFACE),
                        self._age_field,
                    ],
                ),
                ft.Column(
                    expand=True,
                    spacing=6,
                    controls=[
                        ft.Text("Monthly Income (opt)", size=13, weight=ft.FontWeight.W_600, color=COLOR_ON_SURFACE),
                        self._income_field,
                    ],
                ),
            ],
        )

        # Security Note
        security_note = ft.Container(
            bgcolor=COLOR_SURFACE_CONTAINER,
            border=ft.Border.all(1, COLOR_OUTLINE_VARIANT),
            border_radius=16,
            padding=ft.Padding.all(12),
            content=ft.Row(
                spacing=10,
                controls=[
                    ft.Icon(ft.Icons.LOCK, color=COLOR_PRIMARY_CONTAINER, size=18),
                    ft.Text(
                        "Your financial data is encrypted with 256-bit AES protection and stored locally on your device.",
                        size=11,
                        color=COLOR_ON_SURFACE_VARIANT,
                        expand=True,
                    ),
                ],
            ),
        )

        # Main Action Button
        continue_btn = ft.ElevatedButton(
            content=ft.Row(
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=8,
                controls=[
                    ft.Text("Continue to Dashboard", size=15, weight=ft.FontWeight.W_700),
                    ft.Icon(ft.Icons.ARROW_FORWARD, size=18),
                ],
            ),
            bgcolor=COLOR_PRIMARY_CONTAINER,
            color=COLOR_ON_PRIMARY,
            height=50,
            border_radius=14,
            on_click=self._on_submit,
        )

        skip_btn = ft.TextButton(
            content=ft.Text("I'll configure this later", color=COLOR_OUTLINE, size=13),
            on_click=self._on_skip,
        )

        form_column = ft.Column(
            spacing=16,
            controls=[
                # Full Name
                ft.Column(
                    spacing=6,
                    controls=[
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Text("Full Name *", size=13, weight=ft.FontWeight.W_600, color=COLOR_ON_SURFACE),
                                ft.Text("Verified", size=11, weight=ft.FontWeight.W_700, color=COLOR_PRIMARY),
                            ],
                        ),
                        self._name_field,
                    ],
                ),
                # Profession
                ft.Column(
                    spacing=6,
                    controls=[
                        ft.Text("Profession *", size=13, weight=ft.FontWeight.W_600, color=COLOR_ON_SURFACE),
                        self._prof_chips_row,
                    ],
                ),
                # 2-col Age & Income
                two_col_row,
                # City
                ft.Column(
                    spacing=6,
                    controls=[
                        ft.Text("City / Location (optional)", size=13, weight=ft.FontWeight.W_600, color=COLOR_ON_SURFACE),
                        self._city_field,
                    ],
                ),
                # Currency
                ft.Column(
                    spacing=6,
                    controls=[
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Text("Primary Currency *", size=13, weight=ft.FontWeight.W_600, color=COLOR_ON_SURFACE),
                                ft.Text("₹ INR AUTO-DETECTED", size=10, weight=ft.FontWeight.W_700, color=COLOR_PRIMARY),
                            ],
                        ),
                        self._curr_chips_row,
                        ft.Text(
                            "Default: Indian Rupee (₹). You can change this anytime later in Settings.",
                            size=11,
                            color=COLOR_ON_SURFACE_VARIANT,
                        ),
                    ],
                ),
                security_note,
                self._error_text,
                continue_btn,
                ft.Row(alignment=ft.MainAxisAlignment.CENTER, controls=[skip_btn]),
                ft.Container(height=20),
            ],
        )

        scroll_view = ft.ListView(
            expand=True,
            spacing=14,
            padding=ft.Padding.symmetric(horizontal=16, vertical=12),
            controls=[
                header_row,
                progress_track,
                ft.Container(height=6),
                title_section,
                form_column,
            ],
        )

        self._main_container = ft.Container(
            expand=True,
            bgcolor="#090D16" if theme_manager.is_dark() else COLOR_BACKGROUND,
            content=scroll_view,
        )
        return self._main_container

    def _on_skip(self, e) -> None:
        try:
            if not self._profile_service.has_profile():
                self._profile_service.create_profile(
                    name="Vishnu",
                    profession="Software Engineer",
                    currency=self._selected_currency or DEFAULT_CURRENCY,
                    monthly_income_str="60000",
                )
        except Exception as ex:
            logger.debug("Skip fallback profile creation: %s", ex)
        self._on_complete()

    def _on_submit(self, e) -> None:
        name = (self._name_field.value or "").strip()
        if not name:
            self._error_text.value = "Please enter your name to continue."
            self._error_text.visible = True
            try:
                self._error_text.update()
            except Exception:
                pass
            return

        try:
            self._profile_service.create_profile(
                name=name,
                profession=self._selected_profession,
                currency=self._selected_currency or DEFAULT_CURRENCY,
            )
            self._on_complete()
        except Exception as ex:
            logger.error("Failed to create profile: %s", ex, exc_info=True)
            self._error_text.value = f"Error: {ex}"
            self._error_text.visible = True
            try:
                self._error_text.update()
            except Exception:
                pass