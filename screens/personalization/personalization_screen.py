"""
Spendora — Settings Screen (Flet).

Matches Google Stitch "Settings - ExpenseAI" screen:
- Header: Back button, "Settings" + PRO badge, "SPENDORA v2.4 • Pro Plan", Theme toggle
- 1. User Profile Card:
    - Gradient avatar with verified badge
    - "Vishnu" + PRO MEMBER badge
    - "Software Engineer • Bengaluru, India"
    - Quick metrics ribbon: Monthly Budget (₹50,000) & Tracked Since (Jan 2026)
- 2. AI & Automation:
    - AI Peer Insights switch
    - Smart Categorization switch
    - AI Voice & Floating Bar switch
- 3. Preferences & Region:
    - Primary Currency (INR ₹)
    - Financial Month Cycle (1st of month)
    - Daily Expense Check (8:00 PM)
- 4. Security & Cloud Ledger:
    - Biometric / Face ID switch
    - Cloud Backup & Sync button
    - Export Financial Ledger
- 5. Theme & Display:
    - Segmented buttons: Light, Dark, System
- 6. Account Actions:
    - Help & AI Financial Concierge
    - Log Out from SPENDORA
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
    COLOR_ERROR_CONTAINER,
    COLOR_ON_PRIMARY,
    COLOR_ON_SURFACE,
    COLOR_ON_SURFACE_VARIANT,
    COLOR_OUTLINE,
    COLOR_OUTLINE_VARIANT,
    COLOR_PRIMARY,
    COLOR_PRIMARY_CONTAINER,
    COLOR_PRIMARY_FIXED,
    COLOR_SECONDARY,
    COLOR_SECONDARY_CONTAINER,
    COLOR_SECONDARY_FIXED,
    COLOR_SURFACE_CARD,
    COLOR_SURFACE_CONTAINER,
    COLOR_SURFACE_LOW,
    CURRENCY_SYMBOLS,
    DEFAULT_CURRENCY,
)
from config.theme_manager import ThemeMode, theme_manager
from database.models import Category, User
from services.category_service import CategoryService
from services.profile_service import ProfileService

logger = logging.getLogger(__name__)


class PersonalizationView:
    """Settings view matching Google Stitch SPENDORA Settings design."""

    def __init__(
        self,
        switch_to_tab: Optional[Callable[[int], None]] = None,
        on_logout: Optional[Callable[[], None]] = None,
    ) -> None:
        self._profile_service = ProfileService()
        self._category_service = CategoryService()
        self._user: Optional[User] = None
        self._page: Optional[ft.Page] = None
        self._switch_to_tab = switch_to_tab
        self._on_logout = on_logout

        # Profile details
        self._name_text = ft.Text("Vishnu", size=18, weight=ft.FontWeight.W_800, color=COLOR_ON_SURFACE)
        self._prof_text = ft.Text("Software Engineer • Bengaluru, India", size=12, color=COLOR_ON_SURFACE_VARIANT)
        self._budget_text = ft.Text("₹50,000", size=14, weight=ft.FontWeight.W_700, color=COLOR_ON_SURFACE)
        self._currency_text = ft.Text("INR (₹)", size=12, weight=ft.FontWeight.W_700, color=COLOR_PRIMARY)

        # Dialog inputs
        self._cat_name_input = ft.TextField(label="Category Name", dense=True)

        # Theme icon & buttons
        self._theme_icon = ft.IconButton(
            icon=ft.Icons.LIGHT_MODE if theme_manager.is_dark() else ft.Icons.DARK_MODE,
            icon_color=COLOR_ON_SURFACE,
            icon_size=20,
            tooltip="Toggle Dark/Light Mode",
            on_click=self._on_toggle_theme,
        )

        self._theme_buttons_row = ft.Row(spacing=6)
        self._update_theme_buttons()
        theme_manager.add_listener(self._on_theme_changed)

    def set_page(self, page: ft.Page) -> None:
        self._page = page

    def _on_toggle_theme(self, e) -> None:
        theme_manager.toggle(self._page)

    def _set_theme(self, mode: ThemeMode) -> None:
        theme_manager.set_theme(mode, self._page)
        self._update_theme_buttons()
        try:
            self._theme_buttons_row.update()
        except Exception:
            pass

    def _update_theme_buttons(self) -> None:
        current_mode = theme_manager.mode

        def _theme_btn(label: str, icon: str, mode: ThemeMode) -> ft.Container:
            is_active = (current_mode == mode)
            return ft.Container(
                expand=True,
                bgcolor=COLOR_SURFACE_CARD if is_active else COLOR_SURFACE_LOW,
                border_radius=12,
                padding=ft.Padding.symmetric(vertical=10),
                alignment=ft.Alignment.CENTER,
                shadow=ft.BoxShadow(spread_radius=1, blur_radius=8, color=f"{COLOR_ON_SURFACE}08") if is_active else None,
                ink=True,
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=6,
                    controls=[
                        ft.Icon(icon, size=16, color=COLOR_PRIMARY if is_active else COLOR_OUTLINE),
                        ft.Text(label, size=12, weight=ft.FontWeight.W_700 if is_active else ft.FontWeight.W_500, color=COLOR_PRIMARY if is_active else COLOR_OUTLINE),
                    ],
                ),
                on_click=lambda e, m=mode: self._set_theme(m),
            )

        self._theme_buttons_row.controls = [
            _theme_btn("Light", ft.Icons.LIGHT_MODE, ThemeMode.LIGHT),
            _theme_btn("Dark", ft.Icons.DARK_MODE, ThemeMode.DARK),
            _theme_btn("System", ft.Icons.SETTINGS_BRIGHTNESS, ThemeMode.SYSTEM),
        ]

    def _on_theme_changed(self) -> None:
        self._theme_icon.icon = ft.Icons.LIGHT_MODE if theme_manager.is_dark() else ft.Icons.DARK_MODE
        self._update_theme_buttons()
        if self._page:
            try:
                self._theme_icon.update()
                self._theme_buttons_row.update()
                self._page.update()
            except Exception:
                pass

    def _show_snackbar(self, message: str, color: str = COLOR_PRIMARY) -> None:
        if self._page:
            sb = ft.SnackBar(
                content=ft.Text(message, color=COLOR_ON_PRIMARY, weight=ft.FontWeight.W_600),
                bgcolor=color,
                duration=2000,
            )
            self._page.overlay.append(sb)
            sb.open = True
            try:
                self._page.update()
            except Exception:
                pass

    def _open_notifications_sheet(self, e=None) -> None:
        from components.notifications_sheet import show_notifications_dialog
        if self._page:
            show_notifications_dialog(self._page)

    def _open_category_management(self, e=None) -> None:
        from components.category_management_dialog import show_category_management_dialog
        if self._page:
            show_category_management_dialog(self._page, on_change=self.refresh)

    def _open_edit_profile_dialog(self, e) -> None:
        if not self._page:
            return

        name_input = ft.TextField(
            label="Your Name",
            value=self._user.name if self._user else "Vishnu",
            dense=True,
        )
        profession_input = ft.TextField(
            label="Profession",
            value=self._user.profession if (self._user and self._user.profession) else "Software Engineer",
            dense=True,
        )
        current_budget = str(self._user.monthly_income_paise // 100) if (self._user and self._user.monthly_income_paise) else "50000"
        budget_input = ft.TextField(
            label="Monthly Budget (₹)",
            value=current_budget,
            keyboard_type=ft.KeyboardType.NUMBER,
            dense=True,
        )

        def _save_profile(ev):
            try:
                new_name = name_input.value.strip() if name_input.value else "Vishnu"
                new_prof = profession_input.value.strip() if profession_input.value else "Software Engineer"
                new_budget = budget_input.value.strip() if budget_input.value else "50000"
                if self._user:
                    self._profile_service.update_profile(
                        self._user.id,
                        name=new_name,
                        profession=new_prof,
                        monthly_income_str=new_budget,
                    )
                self.refresh()
                dialog.open = False
                self._page.update()
                self._show_snackbar("Profile updated successfully!", COLOR_EMERALD_ACCENT)
            except Exception as ex:
                self._show_snackbar(f"Failed to update profile: {ex}", COLOR_ERROR)

        def _cancel(ev):
            dialog.open = False
            self._page.update()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Edit Profile", weight=ft.FontWeight.W_700),
            content=ft.Column(
                spacing=12,
                tight=True,
                controls=[
                    name_input,
                    profession_input,
                    budget_input,
                ],
            ),
            actions=[
                ft.TextButton("Cancel", on_click=_cancel),
                ft.ElevatedButton("Save", bgcolor=COLOR_PRIMARY, color=COLOR_ON_PRIMARY, on_click=_save_profile),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self._page.overlay.append(dialog)
        dialog.open = True
        self._page.update()

    def _open_privacy_disclosure_dialog(self, e=None) -> None:
        if not self._page:
            return

        def _close(ev):
            dialog.open = False
            self._page.update()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                spacing=8,
                controls=[
                    ft.Icon(ft.Icons.SHIELD_OUTLINED, color=COLOR_PRIMARY, size=22),
                    ft.Text("Privacy & Storage Disclosure", weight=ft.FontWeight.W_700, size=16),
                ],
            ),
            content=ft.Container(
                width=360,
                content=ft.Column(
                    spacing=12,
                    tight=True,
                    scroll=ft.ScrollMode.ADAPTIVE,
                    controls=[
                        ft.Text(
                            "Spendora is engineered with privacy-first and deterministic local computing principles:",
                            size=12,
                            color=COLOR_ON_SURFACE,
                        ),
                        ft.Container(
                            bgcolor=f"{COLOR_PRIMARY}12",
                            border=ft.Border.all(1, f"{COLOR_PRIMARY}33"),
                            border_radius=10,
                            padding=ft.Padding.all(10),
                            content=ft.Column(
                                spacing=6,
                                controls=[
                                    ft.Text("💾 On-Device SQLite Storage", size=12, weight=ft.FontWeight.W_700, color=COLOR_PRIMARY),
                                    ft.Text(
                                        "All your transactions, categories, budgets, and profile records are stored exclusively in a secure, sandboxed on-device database.",
                                        size=11,
                                        color=COLOR_ON_SURFACE,
                                    ),
                                ],
                            ),
                        ),
                        ft.Container(
                            bgcolor=f"{COLOR_EMERALD_ACCENT}12",
                            border=ft.Border.all(1, f"{COLOR_EMERALD_ACCENT}33"),
                            border_radius=10,
                            padding=ft.Padding.all(10),
                            content=ft.Column(
                                spacing=6,
                                controls=[
                                    ft.Text("🧮 100% Deterministic Integer Math", size=12, weight=ft.FontWeight.W_700, color=COLOR_EMERALD_ACCENT),
                                    ft.Text(
                                        "All balances, surplus, 50-30-20 splits, and burn calculations run locally using integer paise units. No cloud service is ever needed for your financial figures.",
                                        size=11,
                                        color=COLOR_ON_SURFACE,
                                    ),
                                ],
                            ),
                        ),
                        ft.Container(
                            bgcolor=f"{COLOR_SECONDARY}12",
                            border=ft.Border.all(1, f"{COLOR_SECONDARY}33"),
                            border_radius=10,
                            padding=ft.Padding.all(10),
                            content=ft.Column(
                                spacing=6,
                                controls=[
                                    ft.Text("🔒 Opt-In Cloud AI", size=12, weight=ft.FontWeight.W_700, color=COLOR_SECONDARY),
                                    ft.Text(
                                        "Cloud AI (Google Gemini) can be toggled on or off at any time. When disabled, Spendora automatically falls back to the on-device financial intelligence engine with zero network transmission.",
                                        size=11,
                                        color=COLOR_ON_SURFACE,
                                    ),
                                ],
                            ),
                        ),
                    ],
                ),
            ),
            actions=[
                ft.ElevatedButton("Got It", bgcolor=COLOR_PRIMARY, color=COLOR_ON_PRIMARY, on_click=_close),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self._page.overlay.append(dialog)
        dialog.open = True
        self._page.update()

    def _open_currency_dialog(self, e) -> None:
        if not self._page or not self._user:
            return

        currencies = [
            ("INR", "Indian Rupee (₹)", "₹"),
            ("USD", "US Dollar ($)", "$"),
            ("EUR", "Euro (€)", "€"),
            ("GBP", "British Pound (£)", "£"),
        ]

        def _select_currency(code: str, sym: str):
            try:
                self._profile_service.update_profile(self._user.id, currency=code)
                self._currency_text.value = f"{code} ({sym})"
                self.refresh()
                dialog.open = False
                self._page.update()
                self._show_snackbar(f"Primary currency set to {code} ({sym})", COLOR_EMERALD_ACCENT)
            except Exception as ex:
                self._show_snackbar(f"Failed to change currency: {ex}", COLOR_ERROR)

        def _cancel(ev):
            dialog.open = False
            self._page.update()

        currency_rows = [
            ft.ListTile(
                leading=ft.Text(sym, size=18, weight=ft.FontWeight.W_700, color=COLOR_PRIMARY),
                title=ft.Text(label, size=14, weight=ft.FontWeight.W_600),
                on_click=lambda ev, c=code, s=sym: _select_currency(c, s),
            )
            for code, label, sym in currencies
        ]

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Select Primary Currency", weight=ft.FontWeight.W_700),
            content=ft.Column(tight=True, spacing=4, controls=currency_rows),
            actions=[ft.TextButton("Cancel", on_click=_cancel)],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self._page.overlay.append(dialog)
        dialog.open = True
        self._page.update()

    def _open_logout_dialog(self, e) -> None:
        if not self._page:
            return

        def _confirm_logout(ev):
            dialog.open = False
            self._page.update()
            if self._on_logout:
                self._on_logout()
            else:
                self._show_snackbar("Logged out from SPENDORA session.", COLOR_ERROR)

        def _cancel(ev):
            dialog.open = False
            self._page.update()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Log Out", weight=ft.FontWeight.W_700),
            content=ft.Text("Are you sure you want to log out from SPENDORA? Your data remains securely encrypted on this device."),
            actions=[
                ft.TextButton("Cancel", on_click=_cancel),
                ft.ElevatedButton("Log Out", bgcolor=COLOR_ERROR, color=COLOR_ON_PRIMARY, on_click=_confirm_logout),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self._page.overlay.append(dialog)
        dialog.open = True
        self._page.update()

    def build(self) -> ft.Control:
        is_dark = theme_manager.is_dark()
        card_bg = "#151D30" if is_dark else COLOR_SURFACE_CARD
        border_col = "#222E48" if is_dark else COLOR_OUTLINE_VARIANT
        text_col = "#FFFFFF" if is_dark else COLOR_ON_SURFACE
        sub_col = "#94A3B8" if is_dark else COLOR_OUTLINE
        input_bg = "#0F1726" if is_dark else COLOR_SURFACE_LOW

        # Top App Bar
        top_bar = ft.Container(
            bgcolor=card_bg,
            border=ft.Border.only(bottom=ft.BorderSide(1, border_col)),
            padding=ft.Padding.symmetric(horizontal=16, vertical=10),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Row(
                        spacing=10,
                        controls=[
                            ft.IconButton(
                                icon=ft.Icons.ARROW_BACK,
                                icon_color=text_col,
                                icon_size=20,
                                tooltip="Back to Dashboard",
                                on_click=lambda e: self._switch_to_tab(0) if self._switch_to_tab else None,
                            ),
                            ft.Column(
                                spacing=2,
                                controls=[
                                    ft.Row(
                                        spacing=6,
                                        controls=[
                                            ft.Text("Settings", size=18, weight=ft.FontWeight.W_800, color=text_col),
                                            ft.Container(
                                                bgcolor=f"{COLOR_PRIMARY}25",
                                                border=ft.Border.all(1, f"{COLOR_PRIMARY}50"),
                                                border_radius=10,
                                                padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                                                content=ft.Text("PRO", size=10, weight=ft.FontWeight.W_800, color=COLOR_PRIMARY),
                                            ),
                                        ],
                                    ),
                                    ft.Text("SPENDORA v2.4 • Pro Plan", size=11, color=sub_col),
                                ],
                            ),
                        ],
                    ),
                    ft.Row(
                        spacing=4,
                        controls=[
                            self._theme_icon,
                            ft.IconButton(
                                icon=ft.Icons.NOTIFICATIONS_OUTLINED,
                                icon_color=sub_col,
                                icon_size=20,
                                tooltip="Notifications & Activity",
                                on_click=self._open_notifications_sheet,
                            ),
                        ],
                    ),
                ],
            ),
        )

        # 1. User Profile Card
        profile_card = ft.Container(
            bgcolor=card_bg,
            border=ft.Border.all(1, border_col),
            border_radius=24,
            padding=ft.Padding.all(18),
            shadow=ft.BoxShadow(spread_radius=1, blur_radius=16, color="#00000033" if is_dark else "#0D132208", offset=ft.Offset(0, 4)),
            content=ft.Column(
                spacing=14,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Row(
                                spacing=12,
                                controls=[
                                    ft.Stack(
                                        controls=[
                                            ft.Container(
                                                width=52,
                                                height=52,
                                                border_radius=16,
                                                gradient=ft.LinearGradient(
                                                    begin=ft.Alignment.TOP_LEFT,
                                                    end=ft.Alignment.BOTTOM_RIGHT,
                                                    colors=[COLOR_PRIMARY, COLOR_SECONDARY, COLOR_SECONDARY_CONTAINER],
                                                ),
                                                alignment=ft.Alignment.CENTER,
                                                content=ft.Text("VV", size=18, weight=ft.FontWeight.W_800, color=COLOR_ON_PRIMARY),
                                            ),
                                            ft.Container(
                                                width=16,
                                                height=16,
                                                border_radius=8,
                                                bgcolor=COLOR_PRIMARY,
                                                border=ft.Border.all(2, card_bg),
                                                alignment=ft.Alignment.CENTER,
                                                right=-2,
                                                bottom=-2,
                                                content=ft.Icon(ft.Icons.VERIFIED, color=COLOR_ON_PRIMARY, size=11),
                                            ),
                                        ],
                                    ),
                                    ft.Column(
                                        spacing=2,
                                        controls=[
                                            ft.Row(
                                                spacing=6,
                                                controls=[
                                                    self._name_text,
                                                    ft.Container(
                                                        bgcolor=f"{COLOR_SECONDARY}33",
                                                        border_radius=8,
                                                        padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                                                        content=ft.Text("PRO MEMBER", size=9, weight=ft.FontWeight.W_800, color=COLOR_SECONDARY),
                                                    ),
                                                ],
                                            ),
                                            self._prof_text,
                                            ft.Text("vishnu@engineer.dev", size=11, color=sub_col),
                                        ],
                                    ),
                                ],
                            ),
                            ft.IconButton(
                                icon=ft.Icons.EDIT,
                                icon_color=COLOR_PRIMARY,
                                bgcolor=input_bg,
                                icon_size=18,
                                tooltip="Edit Profile",
                                on_click=self._open_edit_profile_dialog,
                            ),
                        ],
                    ),
                    # Quick Metrics Ribbon
                    ft.Row(
                        spacing=10,
                        controls=[
                            ft.Container(
                                expand=True,
                                bgcolor=input_bg,
                                border=ft.Border.all(1, border_col),
                                border_radius=14,
                                padding=ft.Padding.all(10),
                                content=ft.Row(
                                    spacing=8,
                                    controls=[
                                        ft.Container(
                                            width=32,
                                            height=32,
                                            border_radius=8,
                                            bgcolor=f"{COLOR_PRIMARY}18",
                                            alignment=ft.Alignment.CENTER,
                                            content=ft.Icon(ft.Icons.ACCOUNT_BALANCE_WALLET, color=COLOR_PRIMARY, size=16),
                                        ),
                                        ft.Column(
                                            spacing=1,
                                            controls=[
                                                ft.Text("Monthly Budget", size=9, weight=ft.FontWeight.W_700, color=sub_col),
                                                self._budget_text,
                                            ],
                                        ),
                                    ],
                                ),
                            ),
                            ft.Container(
                                expand=True,
                                bgcolor=input_bg,
                                border=ft.Border.all(1, border_col),
                                border_radius=14,
                                padding=ft.Padding.all(10),
                                content=ft.Row(
                                    spacing=8,
                                    controls=[
                                        ft.Container(
                                            width=32,
                                            height=32,
                                            border_radius=8,
                                            bgcolor=f"{COLOR_SECONDARY}18",
                                            alignment=ft.Alignment.CENTER,
                                            content=ft.Icon(ft.Icons.CALENDAR_MONTH, color=COLOR_SECONDARY, size=16),
                                        ),
                                        ft.Column(
                                            spacing=1,
                                            controls=[
                                                ft.Text("Tracked Since", size=9, weight=ft.FontWeight.W_700, color=sub_col),
                                                ft.Text("Jan 2026", size=14, weight=ft.FontWeight.W_700, color=text_col),
                                            ],
                                        ),
                                    ],
                                ),
                            ),
                        ],
                    ),
                ],
            ),
        )

        # 2. AI & Automation Features Card
        def _switch_row(title: str, subtitle: str, icon: str, icon_col: str, checked: bool = True) -> ft.Container:
            def _on_switch_change(e):
                val_str = "enabled" if e.control.value else "disabled"
                self._show_snackbar(f"{title} {val_str}")

            return ft.Container(
                padding=ft.Padding.symmetric(vertical=8),
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Row(
                            spacing=12,
                            controls=[
                                ft.Container(
                                    width=38,
                                    height=38,
                                    border_radius=12,
                                    bgcolor=f"{icon_col}18",
                                    alignment=ft.Alignment.CENTER,
                                    content=ft.Icon(icon, color=icon_col, size=18),
                                ),
                                ft.Column(
                                    spacing=2,
                                    controls=[
                                        ft.Text(title, size=13, weight=ft.FontWeight.W_600, color=text_col),
                                        ft.Text(subtitle, size=11, color=sub_col),
                                    ],
                                ),
                            ],
                        ),
                        ft.Switch(value=checked, active_color=COLOR_PRIMARY, on_change=_on_switch_change),
                    ],
                ),
            )

        user_id = self._user.id if self._user else 1
        cloud_ai_pref = self._profile_service.get_preference(user_id, "cloud_ai_enabled", "false")
        cloud_ai_active = (cloud_ai_pref or "").strip().lower() == "true"

        def _on_cloud_ai_toggle(e):
            val = e.control.value
            self._profile_service.set_preference(user_id, "cloud_ai_enabled", "true" if val else "false")
            status = "enabled" if val else "disabled (offline local mode)"
            self._show_snackbar(f"Cloud AI {status}")

        def _cloud_ai_row() -> ft.Container:
            return ft.Container(
                padding=ft.Padding.symmetric(vertical=8),
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Row(
                            spacing=12,
                            controls=[
                                ft.Container(
                                    width=38,
                                    height=38,
                                    border_radius=12,
                                    bgcolor=f"{COLOR_PRIMARY}18",
                                    alignment=ft.Alignment.CENTER,
                                    content=ft.Icon(ft.Icons.CLOUD_DONE, color=COLOR_PRIMARY, size=18),
                                ),
                                ft.Column(
                                    spacing=2,
                                    controls=[
                                        ft.Text("Cloud AI (Google Gemini)", size=13, weight=ft.FontWeight.W_600, color=text_col),
                                        ft.Text("Conversational assistant (fallback to local if off)", size=11, color=sub_col),
                                    ],
                                ),
                            ],
                        ),
                        ft.Switch(value=cloud_ai_active, active_color=COLOR_PRIMARY, on_change=_on_cloud_ai_toggle),
                    ],
                ),
            )

        def _privacy_row() -> ft.Container:
            return ft.Container(
                padding=ft.Padding.symmetric(vertical=8),
                ink=True,
                on_click=self._open_privacy_disclosure_dialog,
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Row(
                            spacing=12,
                            controls=[
                                ft.Container(
                                    width=38,
                                    height=38,
                                    border_radius=12,
                                    bgcolor=f"{COLOR_EMERALD_ACCENT}18",
                                    alignment=ft.Alignment.CENTER,
                                    content=ft.Icon(ft.Icons.SECURITY, color=COLOR_EMERALD_ACCENT, size=18),
                                ),
                                ft.Column(
                                    spacing=2,
                                    controls=[
                                        ft.Text("Data Privacy & Storage", size=13, weight=ft.FontWeight.W_600, color=text_col),
                                        ft.Text("On-device database & offline math guarantee", size=11, color=sub_col),
                                    ],
                                ),
                            ],
                        ),
                        ft.Icon(ft.Icons.CHEVRON_RIGHT, color=sub_col, size=16),
                    ],
                ),
            )

        ai_automation_card = ft.Container(
            bgcolor=card_bg,
            border=ft.Border.all(1, border_col),
            border_radius=24,
            padding=ft.Padding.all(18),
            shadow=ft.BoxShadow(spread_radius=1, blur_radius=16, color="#00000033" if is_dark else "#0D132208", offset=ft.Offset(0, 4)),
            content=ft.Column(
                spacing=4,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Row(
                                spacing=6,
                                controls=[
                                    ft.Container(width=8, height=8, border_radius=4, bgcolor=COLOR_PRIMARY),
                                    ft.Text("AI & Automation", size=15, weight=ft.FontWeight.W_700, color=text_col),
                                ],
                            ),
                            ft.Text("ACTIVE", size=10, weight=ft.FontWeight.W_800, color=COLOR_PRIMARY),
                        ],
                    ),
                    ft.Divider(color=border_col, height=12),
                    _cloud_ai_row(),
                    _switch_row("AI Peer Insights", "Compare spending with tech peer benchmarks", ft.Icons.AUTO_AWESOME, COLOR_PRIMARY),
                    _switch_row("Smart Categorization", "Auto-detect merchant & tax deductions", ft.Icons.CATEGORY, COLOR_SECONDARY),
                    _switch_row("AI Voice & Floating Bar", "Quick access conversational financial agent", ft.Icons.MIC, COLOR_PRIMARY),
                    _privacy_row(),
                ],
            ),
        )

        # 3. Preferences & Region Card
        def _pref_nav_row(title: str, subtitle: str, value_pill: str, icon: str, on_tap=None) -> ft.Container:
            return ft.Container(
                padding=ft.Padding.symmetric(vertical=8),
                ink=True if on_tap else False,
                on_click=on_tap,
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Row(
                            spacing=12,
                            controls=[
                                ft.Container(
                                    width=38,
                                    height=38,
                                    border_radius=12,
                                    bgcolor=input_bg,
                                    alignment=ft.Alignment.CENTER,
                                    content=ft.Icon(icon, color=text_col, size=18),
                                ),
                                ft.Column(
                                    spacing=2,
                                    controls=[
                                        ft.Text(title, size=13, weight=ft.FontWeight.W_600, color=text_col),
                                        ft.Text(subtitle, size=11, color=sub_col),
                                    ],
                                ),
                            ],
                        ),
                        ft.Row(
                            spacing=4,
                            controls=[
                                ft.Container(
                                    bgcolor=input_bg,
                                    border=ft.Border.all(1, border_col),
                                    border_radius=8,
                                    padding=ft.Padding.symmetric(horizontal=8, vertical=4),
                                    content=ft.Text(value_pill, size=11, weight=ft.FontWeight.W_700, color=COLOR_PRIMARY),
                                ),
                                ft.Icon(ft.Icons.CHEVRON_RIGHT, color=sub_col, size=16),
                            ],
                        ),
                    ],
                ),
            )

        pref_card = ft.Container(
            bgcolor=card_bg,
            border=ft.Border.all(1, border_col),
            border_radius=24,
            padding=ft.Padding.all(18),
            shadow=ft.BoxShadow(spread_radius=1, blur_radius=16, color="#00000033" if is_dark else "#0D132208", offset=ft.Offset(0, 4)),
            content=ft.Column(
                spacing=4,
                controls=[
                    ft.Text("Preferences & Region", size=15, weight=ft.FontWeight.W_700, color=text_col),
                    ft.Divider(color=border_col, height=12),
                    _pref_nav_row("Primary Currency", "Tap to change active currency", "INR (₹)", ft.Icons.CURRENCY_RUPEE, on_tap=self._open_currency_dialog),
                    _pref_nav_row("Categories & Subcategories", "Create new categories & manage labels", "Manage", ft.Icons.CATEGORY, on_tap=self._open_category_management),
                    _pref_nav_row("Financial Month Cycle", "Starts 1st of each month", "1st of month", ft.Icons.EVENT_REPEAT, on_tap=lambda e: self._show_snackbar("Billing cycle set to 1st of each month")),
                    _pref_nav_row("Daily Expense Check", "Smart evening notification", "8:00 PM", ft.Icons.SCHEDULE, on_tap=lambda e: self._show_snackbar("Daily check reminder set for 8:00 PM")),
                ],
            ),
        )

        # 4. Security & Cloud Ledger Card
        security_card = ft.Container(
            bgcolor=card_bg,
            border=ft.Border.all(1, border_col),
            border_radius=24,
            padding=ft.Padding.all(18),
            shadow=ft.BoxShadow(spread_radius=1, blur_radius=16, color="#00000033" if is_dark else "#0D132208", offset=ft.Offset(0, 4)),
            content=ft.Column(
                spacing=4,
                controls=[
                    ft.Text("Security & Cloud Ledger", size=15, weight=ft.FontWeight.W_700, color=text_col),
                    ft.Divider(color=border_col, height=12),
                    _switch_row("Biometric / Face ID Login", "Secure access via hardware key", ft.Icons.FINGERPRINT, COLOR_PRIMARY),
                    # Cloud backup
                    ft.Container(
                        padding=ft.Padding.symmetric(vertical=8),
                        content=ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Row(
                                    spacing=12,
                                    controls=[
                                        ft.Container(
                                            width=38,
                                            height=38,
                                            border_radius=12,
                                            bgcolor=f"{COLOR_SECONDARY}18",
                                            alignment=ft.Alignment.CENTER,
                                            content=ft.Icon(ft.Icons.CLOUD_SYNC, color=COLOR_SECONDARY, size=18),
                                        ),
                                        ft.Column(
                                            spacing=2,
                                            controls=[
                                                ft.Text("Cloud Backup & Sync", size=13, weight=ft.FontWeight.W_600, color=text_col),
                                                ft.Text("Last synced today, 10:45 AM", size=11, color=sub_col),
                                            ],
                                        ),
                                    ],
                                ),
                                ft.ElevatedButton(
                                    "Sync",
                                    bgcolor=input_bg,
                                    color=COLOR_PRIMARY,
                                    height=32,
                                    border_radius=14,
                                    on_click=lambda e: self._show_snackbar("Cloud backup complete! 100% ledger entries backed up.", COLOR_EMERALD_ACCENT),
                                ),
                            ],
                        ),
                    ),
                    # Export ledger
                    ft.Container(
                        padding=ft.Padding.symmetric(vertical=8),
                        ink=True,
                        on_click=lambda e: self._show_snackbar("Financial Ledger (CSV & PDF) exported to Downloads!"),
                        content=ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Row(
                                    spacing=12,
                                    controls=[
                                        ft.Container(
                                            width=38,
                                            height=38,
                                            border_radius=12,
                                            bgcolor=input_bg,
                                            alignment=ft.Alignment.CENTER,
                                            content=ft.Icon(ft.Icons.FILE_DOWNLOAD, color=text_col, size=18),
                                        ),
                                        ft.Column(
                                            spacing=2,
                                            controls=[
                                                ft.Text("Export Financial Ledger", size=13, weight=ft.FontWeight.W_600, color=text_col),
                                                ft.Text("Download audit files (CSV, PDF, Excel)", size=11, color=sub_col),
                                            ],
                                        ),
                                    ],
                                ),
                                ft.Icon(ft.Icons.ARROW_FORWARD, color=sub_col, size=16),
                            ],
                        ),
                    ),
                ],
            ),
        )

        # 5. Appearance Theme Segmented Buttons Card
        theme_card = ft.Container(
            bgcolor=card_bg,
            border=ft.Border.all(1, border_col),
            border_radius=24,
            padding=ft.Padding.all(18),
            shadow=ft.BoxShadow(spread_radius=1, blur_radius=16, color="#00000033" if is_dark else "#0D132208", offset=ft.Offset(0, 4)),
            content=ft.Column(
                spacing=10,
                controls=[
                    ft.Text("Theme & Display", size=15, weight=ft.FontWeight.W_700, color=text_col),
                    ft.Container(
                        bgcolor=input_bg,
                        border=ft.Border.all(1, border_col),
                        border_radius=14,
                        padding=ft.Padding.all(4),
                        content=self._theme_buttons_row,
                    ),
                ],
            ),
        )

        # 6. Account Actions
        help_btn = ft.Container(
            bgcolor=card_bg,
            border=ft.Border.all(1, border_col),
            border_radius=16,
            padding=ft.Padding.symmetric(horizontal=16, vertical=14),
            ink=True,
            on_click=lambda e: self._switch_to_tab(2) if self._switch_to_tab else None,
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Row(
                        spacing=12,
                        controls=[
                            ft.Icon(ft.Icons.HELP_CENTER, color=COLOR_PRIMARY, size=20),
                            ft.Text("Help & AI Financial Concierge", size=14, weight=ft.FontWeight.W_600, color=text_col),
                        ],
                    ),
                    ft.Icon(ft.Icons.CHEVRON_RIGHT, color=sub_col, size=18),
                ],
            ),
        )

        logout_btn = ft.Container(
            bgcolor=f"{COLOR_ERROR}18",
            border=ft.Border.all(1, f"{COLOR_ERROR}44"),
            border_radius=16,
            padding=ft.Padding.symmetric(horizontal=16, vertical=14),
            alignment=ft.Alignment.CENTER,
            ink=True,
            on_click=self._open_logout_dialog,
            content=ft.Row(
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=8,
                controls=[
                    ft.Icon(ft.Icons.LOGOUT, color=COLOR_ERROR, size=18),
                    ft.Text("Log Out from SPENDORA", size=14, weight=ft.FontWeight.W_700, color=COLOR_ERROR),
                ],
            ),
        )

        scroll_content = ft.ListView(
            expand=True,
            spacing=16,
            padding=ft.Padding.symmetric(horizontal=16, vertical=12),
            controls=[
                profile_card,
                ai_automation_card,
                pref_card,
                security_card,
                theme_card,
                help_btn,
                logout_btn,
                ft.Container(height=80),
            ],
        )

        return ft.Column(
            expand=True,
            spacing=0,
            controls=[
                top_bar,
                scroll_content,
            ],
        )

    def refresh(self) -> None:
        """Fetch user data from DB."""
        try:
            self._user = self._profile_service.get_user()
            if self._user:
                self._name_text.value = self._user.name
                prof = self._user.profession or "Software Engineer"
                self._prof_text.value = f"{prof} • Bengaluru, India"
                self._currency_text.value = f"{self._user.currency or DEFAULT_CURRENCY} ({CURRENCY_SYMBOLS.get(self._user.currency or DEFAULT_CURRENCY, '₹')})"
                if self._user.monthly_income_paise:
                    self._budget_text.value = f"₹{self._user.monthly_income_paise // 100:,}"
            if self._page:
                try:
                    self._page.update()
                except Exception:
                    pass
        except Exception as ex:
            logger.error("Error refreshing settings: %s", ex, exc_info=True)
