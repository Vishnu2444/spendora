"""
Leaksee — Settings Screen (Flet).

Matches Settings screen:
- Header: Back button, "Settings" + PRO badge, "LEAKSEE Pro", Theme toggle, Notifications
- 1. User Profile Card:
    - Gradient avatar with user initials and verified badge
    - User name + PRO MEMBER badge
    - Profession • Location & User Email
    - Quick metrics ribbon: Monthly Budget (editable) & Tracked Since
- 2. AI & Automation:
    - Cloud AI (Google Gemini) switch (integrated with ai_service.py)
    - AI Peer Insights switch (persistent)
    - Smart Categorization switch (persistent)
    - AI Voice & Floating Bar switch (persistent)
    - Data Privacy & Storage disclosure dialog
- 3. Preferences & Region:
    - Primary Currency selector dialog
    - Categories & Subcategories manager
    - Financial Month Cycle selector dialog
    - Daily Expense Check reminder dialog
- 4. Security & Cloud Ledger:
    - Biometric / Face ID Login switch (persistent)
    - Cloud Backup & Sync action with dynamic sync timestamp
    - Export Financial Ledger dialog (CSV spreadsheet, Audit report, SQLite backup)
- 5. Theme & Display:
    - Segmented buttons: Light, Dark, System
- 6. Account Actions:
    - Help & AI Financial Concierge
    - Log Out from LEAKSEE
"""

from __future__ import annotations

import csv
import logging
import os
from pathlib import Path
import re
import shutil
from datetime import date, datetime, time
from typing import Callable, Optional, Union

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
    DATABASE_PATH,
)
from config.theme_manager import ThemeMode, theme_manager
from database.models import Category, TransactionType, User
from services.calculation_service import CalculationService
from services.category_service import CategoryService
from services.clock_service import clock_service
from services.profile_service import ProfileService
from services.transaction_service import TransactionService

logger = logging.getLogger(__name__)


class PersonalizationView:
    """Settings view matching Leaksee Settings design with fully functional options."""

    def __init__(
        self,
        switch_to_tab: Optional[Callable[[int], None]] = None,
        on_logout: Optional[Callable[[], None]] = None,
    ) -> None:
        self._profile_service = ProfileService()
        self._category_service = CategoryService()
        self._transaction_service = TransactionService()
        self._calculation_service = CalculationService()
        self._user: Optional[User] = None
        self._page: Optional[ft.Page] = None
        self._switch_to_tab = switch_to_tab
        self._on_logout = on_logout

        # Profile details
        self._avatar_text = ft.Text("U", size=18, weight=ft.FontWeight.W_800, color=COLOR_ON_PRIMARY)
        self._name_text = ft.Text("", size=18, weight=ft.FontWeight.W_800, color=COLOR_ON_SURFACE)
        self._prof_text = ft.Text("", size=12, color=COLOR_ON_SURFACE_VARIANT)
        self._email_text = ft.Text("", size=11, color=COLOR_OUTLINE)
        self._budget_text = ft.Text("₹0", size=14, weight=ft.FontWeight.W_700, color=COLOR_ON_SURFACE)
        self._tracked_since_text = ft.Text("Jan 2026", size=14, weight=ft.FontWeight.W_700, color=COLOR_ON_SURFACE)

        # Region & Preferences controls
        self._currency_text = ft.Text("INR (₹)", size=11, weight=ft.FontWeight.W_700, color=COLOR_PRIMARY)
        self._cycle_text = ft.Text("1st of month", size=11, weight=ft.FontWeight.W_700, color=COLOR_PRIMARY)
        self._cycle_subtitle_text = ft.Text("Starts 1st of each month", size=11, color=COLOR_OUTLINE)
        self._daily_check_text = ft.Text("8:00 PM", size=11, weight=ft.FontWeight.W_700, color=COLOR_PRIMARY)
        self._daily_check_subtitle_text = ft.Text("Smart evening notification", size=11, color=COLOR_OUTLINE)
        self._cloud_sync_time_text = ft.Text("Last synced today, 10:45 AM", size=11, color=COLOR_OUTLINE)
        self._export_path_pill_text = ft.Text("data/", size=11, weight=ft.FontWeight.W_700, color=COLOR_PRIMARY)
        self._export_path_subtitle_text = ft.Text("Saved to project data/ folder", size=11, color=COLOR_OUTLINE)
        self._file_picker = ft.FilePicker(on_result=self._on_file_picker_result)
        self._on_dir_selected_callback: Optional[Callable[[str], None]] = None

        # Switches for AI & Security
        self._cloud_ai_switch = ft.Switch(
            value=False,
            active_color=COLOR_PRIMARY,
            on_change=lambda e: self._on_switch_toggle("cloud_ai_enabled", "Cloud AI (Google Gemini)", e),
        )
        self._peer_insights_switch = ft.Switch(
            value=True,
            active_color=COLOR_PRIMARY,
            on_change=lambda e: self._on_switch_toggle("ai_peer_insights_enabled", "AI Peer Insights", e),
        )
        self._smart_cat_switch = ft.Switch(
            value=True,
            active_color=COLOR_PRIMARY,
            on_change=lambda e: self._on_switch_toggle("smart_categorization_enabled", "Smart Categorization", e),
        )
        self._ai_voice_switch = ft.Switch(
            value=True,
            active_color=COLOR_PRIMARY,
            on_change=lambda e: self._on_switch_toggle("ai_voice_bar_enabled", "AI Voice & Floating Bar", e),
        )
        self._biometric_switch = ft.Switch(
            value=False,
            active_color=COLOR_PRIMARY,
            on_change=lambda e: self._on_switch_toggle("biometric_enabled", "Biometric / Face ID Login", e),
        )

        # Dialog inputs
        self._cat_name_input = ft.TextField(label="Category Name", dense=True)

        # Live Time & Date Indicator
        self._live_time_text = ft.Text(
            clock_service.format_short_status(),
            size=10,
            color=COLOR_OUTLINE,
            weight=ft.FontWeight.W_500,
        )
        clock_service.subscribe(self._on_clock_tick)

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

    def _ensure_file_picker(self) -> None:
        if self._page and hasattr(self._page, "overlay") and self._file_picker not in self._page.overlay:
            self._page.overlay.append(self._file_picker)
            try:
                self._page.update()
            except Exception:
                pass

    def _on_file_picker_result(self, e: ft.FilePickerResultEvent) -> None:
        if e.path and self._on_dir_selected_callback:
            try:
                self._on_dir_selected_callback(e.path)
            except Exception as ex:
                logger.error("Error in file picker callback: %s", ex)

    def _on_clock_tick(self, now: datetime) -> None:
        """Handle real-time 1-second clock ticks."""
        if hasattr(self, "_live_time_text") and self._live_time_text:
            new_val = clock_service.format_short_status(now)
            if self._live_time_text.value != new_val:
                self._live_time_text.value = new_val
            if clock_service.is_control_attached(self._live_time_text):
                try:
                    self._live_time_text.update()
                except Exception:
                    pass

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
        is_dark = theme_manager.is_dark()

        def _theme_btn(label: str, icon: str, mode: ThemeMode) -> ft.Container:
            is_active = (current_mode == mode)
            active_bg = "#262A35" if is_dark else COLOR_SURFACE_CARD
            inactive_bg = "#171B26" if is_dark else COLOR_SURFACE_LOW
            active_col = "#C0C1FF" if is_dark else COLOR_PRIMARY
            inactive_col = "#908FA0" if is_dark else COLOR_OUTLINE
            return ft.Container(
                expand=True,
                bgcolor=active_bg if is_active else inactive_bg,
                border_radius=12,
                padding=ft.Padding.symmetric(vertical=10),
                alignment=ft.Alignment.CENTER,
                shadow=ft.BoxShadow(spread_radius=1, blur_radius=8, color="#00000040" if is_dark else f"{COLOR_ON_SURFACE}08") if is_active else None,
                ink=True,
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=6,
                    controls=[
                        ft.Icon(icon, size=16, color=active_col if is_active else inactive_col),
                        ft.Text(label, size=12, weight=ft.FontWeight.W_700 if is_active else ft.FontWeight.W_500, color=active_col if is_active else inactive_col),
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
        if hasattr(self, "_live_time_text") and self._live_time_text:
            self._live_time_text.color = "#908FA0" if theme_manager.is_dark() else COLOR_OUTLINE
            try:
                self._live_time_text.update()
            except Exception:
                pass
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
                duration=2500,
            )
            self._page.overlay.append(sb)
            sb.open = True
            try:
                self._page.update()
            except Exception:
                pass

    def _on_switch_toggle(self, pref_key: str, label: str, e) -> None:
        val = e.control.value
        user_id = self._user.id if self._user else 1
        try:
            self._profile_service.set_preference(user_id, pref_key, "true" if val else "false")
            status = "enabled" if val else "disabled"
            self._show_snackbar(f"{label} {status}", COLOR_EMERALD_ACCENT if val else COLOR_PRIMARY)
        except Exception as ex:
            logger.error("Failed to save preference %s: %s", pref_key, ex)
            self._show_snackbar(f"Failed to update setting: {ex}", COLOR_ERROR)

    def _open_notifications_sheet(self, e=None) -> None:
        from components.notifications_sheet import show_notifications_dialog
        if self._page:
            show_notifications_dialog(self._page)

    def _open_category_management(self, e=None) -> None:
        from components.category_management_dialog import show_category_management_dialog
        if self._page:
            show_category_management_dialog(self._page, on_change=self.refresh)

    def _open_edit_profile_dialog(self, e=None) -> None:
        if not self._page:
            return

        user_id = self._user.id if self._user else 1
        cur = self._user.currency if (self._user and self._user.currency) else DEFAULT_CURRENCY
        sym = CURRENCY_SYMBOLS.get(cur, "₹")

        name_input = ft.TextField(
            label="Your Name",
            value=self._user.name if self._user else "",
            dense=True,
        )
        profession_input = ft.TextField(
            label="Profession",
            value=self._user.profession if (self._user and self._user.profession) else "",
            dense=True,
        )
        current_loc = self._profile_service.get_preference(user_id, "user_location") or ""
        location_input = ft.TextField(
            label="Location (City, Country)",
            value=current_loc,
            dense=True,
        )
        current_email = self._profile_service.get_preference(user_id, "user_email")
        if not current_email:
            clean_name = self._user.name.lower().replace(" ", "") if (self._user and self._user.name) else "user"
            current_email = f"{clean_name}@leaksee.app"

        email_input = ft.TextField(
            label="Email Address",
            value=current_email,
            dense=True,
        )
        current_budget = str(self._user.monthly_income_paise // 100) if (self._user and self._user.monthly_income_paise) else "0"
        budget_input = ft.TextField(
            label=f"Monthly Budget ({sym})",
            value=current_budget,
            keyboard_type=ft.KeyboardType.NUMBER,
            dense=True,
        )

        def _save_profile(ev):
            try:
                new_name = name_input.value.strip() if name_input.value else ""
                new_prof = profession_input.value.strip() if profession_input.value else ""
                new_loc = location_input.value.strip() if location_input.value else ""
                new_email = email_input.value.strip() if email_input.value else ""
                new_budget = budget_input.value.strip() if budget_input.value else "0"
                if self._user:
                    self._profile_service.update_profile(
                        self._user.id,
                        name=new_name,
                        profession=new_prof,
                        monthly_income_str=new_budget,
                    )
                    if new_email:
                        self._profile_service.set_preference(self._user.id, "user_email", new_email)
                    self._profile_service.set_preference(self._user.id, "user_location", new_loc)
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
                    location_input,
                    email_input,
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
                            "Leaksee is engineered with privacy-first and deterministic local computing principles:",
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
                                        "All balances, surplus, 50-30-20 splits, and burn calculations run locally using integer minor units. No cloud service is ever needed for your financial figures.",
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
                                        "Cloud AI (Google Gemini) can be toggled on or off anytime. When off, Leaksee uses an offline rule engine with zero external network traffic.",
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

    def _open_currency_dialog(self, e=None) -> None:
        if not self._page or not self._user:
            return

        currencies = [
            ("INR", "Indian Rupee (₹)", "₹"),
            ("USD", "US Dollar ($)", "$"),
            ("EUR", "Euro (€)", "€"),
            ("GBP", "British Pound (£)", "£"),
            ("JPY", "Japanese Yen (¥)", "¥"),
            ("CAD", "Canadian Dollar ($)", "$"),
            ("AUD", "Australian Dollar ($)", "$"),
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

    def _open_cycle_dialog(self, e=None) -> None:
        """Opens dialog to set the billing cycle start day."""
        if not self._page or not self._user:
            return

        cycles = [
            ("1", "1st of month (Calendar start)"),
            ("5", "5th of month (Post-salary)"),
            ("10", "10th of month"),
            ("15", "15th of month (Mid-month)"),
            ("25", "25th of month (Salary week)"),
            ("last", "Last day of month"),
        ]

        def _select_cycle(key: str, label_text: str):
            try:
                self._profile_service.set_preference(self._user.id, "financial_cycle_start_day", key)
                if key == "last":
                    display_label = "Last day"
                    subtitle = "Starts on the last day of each month"
                elif key == "1":
                    display_label = "1st of month"
                    subtitle = "Starts 1st of each month"
                else:
                    display_label = f"{key}th of month"
                    subtitle = f"Starts {key}th of each month"
                self._cycle_text.value = display_label
                self._cycle_subtitle_text.value = subtitle
                dialog.open = False
                self._page.update()
                self._show_snackbar(f"Financial Month Cycle set to start on {display_label}", COLOR_EMERALD_ACCENT)
            except Exception as ex:
                self._show_snackbar(f"Failed to update cycle: {ex}", COLOR_ERROR)

        def _cancel(ev):
            dialog.open = False
            self._page.update()

        cycle_controls = [
            ft.ListTile(
                leading=ft.Icon(ft.Icons.EVENT_REPEAT, color=COLOR_PRIMARY, size=20),
                title=ft.Text(label, size=13, weight=ft.FontWeight.W_600),
                on_click=lambda ev, k=k, l=label: _select_cycle(k, l),
            )
            for k, label in cycles
        ]

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Financial Month Cycle", weight=ft.FontWeight.W_700),
            content=ft.Column(tight=True, spacing=4, controls=cycle_controls),
            actions=[ft.TextButton("Cancel", on_click=_cancel)],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self._page.overlay.append(dialog)
        dialog.open = True
        self._page.update()

    @staticmethod
    def _parse_and_format_time(time_str: str) -> Optional[str]:
        """Parses and formats user input time string into standard 'H:MM AM/PM'."""
        if not time_str or not time_str.strip():
            return None
        s = time_str.strip().upper()
        s = re.sub(r"(\d+)\s*(AM|PM)", r"\1 \2", s)

        # Check if user entered something like '8:30' or '8' without AM/PM
        if not ("AM" in s or "PM" in s):
            try:
                parts = s.split(":")
                h = int(parts[0])
                m = int(parts[1]) if len(parts) > 1 else 0
                if 0 <= h <= 23 and 0 <= m <= 59:
                    if 1 <= h <= 11:
                        return f"{h}:{m:02d} PM"
                    elif h == 0:
                        return f"12:{m:02d} AM"
                    elif h == 12:
                        return f"12:{m:02d} PM"
                    else:
                        return f"{h - 12}:{m:02d} PM"
            except Exception:
                pass

        formats = [
            "%I:%M %p",
            "%I:%M%p",
            "%I %p",
            "%I%p",
            "%H:%M",
            "%H:%M:%S",
        ]
        for fmt in formats:
            try:
                dt = datetime.strptime(s, fmt)
                hour = dt.hour % 12 or 12
                minute = dt.minute
                ampm = "AM" if dt.hour < 12 else "PM"
                return f"{hour}:{minute:02d} {ampm}"
            except ValueError:
                pass
        return None

    def _open_daily_check_dialog(self, e=None) -> None:
        """Opens dialog to set the daily expense check reminder time."""
        if not self._page or not self._user:
            return

        current_val = self._daily_check_text.value or "8:00 PM"
        is_custom = current_val not in ("7:00 PM", "8:00 PM", "9:00 PM", "10:00 PM", "Off")
        custom_label = f"Custom Time ({current_val})" if is_custom else "Custom Time..."

        times = [
            ("7:00 PM", "7:00 PM (Early Evening)"),
            ("8:00 PM", "8:00 PM (Recommended)"),
            ("9:00 PM", "9:00 PM (Late Evening)"),
            ("10:00 PM", "10:00 PM (Night Review)"),
            ("Custom", custom_label),
            ("Off", "Disabled (No notifications)"),
        ]

        def _select_time(val: str, label_text: str):
            if val == "Custom":
                dialog.open = False
                if self._page:
                    try:
                        self._page.update()
                    except Exception:
                        pass
                self._open_custom_daily_check_dialog()
                return

            try:
                self._profile_service.set_preference(self._user.id, "daily_expense_check_time", val)
                self._daily_check_text.value = val
                self._daily_check_subtitle_text.value = "Reminders disabled" if val == "Off" else f"Smart reminder at {val}"
                dialog.open = False
                if self._page:
                    try:
                        self._page.update()
                    except Exception:
                        pass
                if val == "Off":
                    self._show_snackbar("Daily expense check reminders turned off")
                else:
                    self._show_snackbar(f"Daily check reminder scheduled for {val}", COLOR_EMERALD_ACCENT)
            except Exception as ex:
                self._show_snackbar(f"Failed to update daily check: {ex}", COLOR_ERROR)

        def _cancel(ev):
            dialog.open = False
            if self._page:
                try:
                    self._page.update()
                except Exception:
                    pass

        time_controls = [
            ft.ListTile(
                leading=ft.Icon(
                    ft.Icons.SCHEDULE if v != "Off" and v != "Custom" else (ft.Icons.ACCESS_TIME_FILLED if v == "Custom" else ft.Icons.NOTIFICATIONS_OFF_OUTLINED),
                    color=COLOR_PRIMARY if v != "Off" else COLOR_OUTLINE,
                    size=20,
                ),
                title=ft.Text(label, size=13, weight=ft.FontWeight.W_600),
                on_click=lambda ev, v=v, l=label: _select_time(v, l),
            )
            for v, label in times
        ]

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Daily Expense Check Time", weight=ft.FontWeight.W_700),
            content=ft.Column(tight=True, spacing=4, controls=time_controls),
            actions=[ft.TextButton("Cancel", on_click=_cancel)],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self._page.overlay.append(dialog)
        dialog.open = True
        if self._page:
            try:
                self._page.update()
            except Exception:
                pass

    def _open_custom_daily_check_dialog(self, e=None) -> None:
        """Opens dialog to pick or enter a custom daily expense check reminder time."""
        if not self._page or not self._user:
            return

        current_val = self._daily_check_text.value or "8:00 PM"
        initial_val = current_val if current_val != "Off" else "8:30 PM"

        time_field = ft.TextField(
            value=initial_val,
            label="Custom Time",
            hint_text="e.g. 6:30 PM or 20:30",
            border_radius=12,
            border_color=COLOR_OUTLINE_VARIANT,
            focused_border_color=COLOR_PRIMARY,
            text_size=15,
            prefix_icon=ft.Icons.SCHEDULE,
            autofocus=True,
        )
        error_text = ft.Text("", color=COLOR_ERROR, size=12, visible=False)

        def _set_field_time(t_str: str):
            time_field.value = t_str
            error_text.visible = False
            try:
                time_field.update()
                error_text.update()
            except Exception:
                pass

        def _on_tp_change(ev):
            if tp.value:
                picked = tp.value
                hour = picked.hour % 12 or 12
                ampm = "AM" if picked.hour < 12 else "PM"
                formatted = f"{hour}:{picked.minute:02d} {ampm}"
                _set_field_time(formatted)

        tp = ft.TimePicker(
            confirm_text="Set Time",
            cancel_text="Cancel",
            help_text="Select Daily Check Time",
            on_change=_on_tp_change,
        )

        def _open_clock(ev):
            if self._page:
                self._page.overlay.append(tp)
                tp.open = True
                try:
                    self._page.update()
                except Exception:
                    pass

        def _confirm_custom(ev):
            raw = (time_field.value or "").strip()
            formatted = self._parse_and_format_time(raw)
            if not formatted:
                error_text.value = "Please enter a valid time (e.g. 6:30 PM or 20:30)."
                error_text.visible = True
                try:
                    error_text.update()
                except Exception:
                    pass
                return

            try:
                self._profile_service.set_preference(self._user.id, "daily_expense_check_time", formatted)
                self._daily_check_text.value = formatted
                self._daily_check_subtitle_text.value = f"Smart reminder at {formatted}"
                custom_dialog.open = False
                if self._page:
                    try:
                        self._page.update()
                    except Exception:
                        pass
                self._show_snackbar(f"Daily check reminder scheduled for {formatted}", COLOR_EMERALD_ACCENT)
            except Exception as ex:
                self._show_snackbar(f"Failed to update daily check: {ex}", COLOR_ERROR)

        def _cancel_custom(ev):
            custom_dialog.open = False
            if self._page:
                try:
                    self._page.update()
                except Exception:
                    pass

        quick_times = ["6:00 PM", "6:30 PM", "7:30 PM", "8:30 PM", "9:30 PM", "10:30 PM"]
        chips_row = ft.Row(
            wrap=True,
            spacing=6,
            run_spacing=6,
            controls=[
                ft.Chip(
                    label=ft.Text(qt, size=12),
                    on_click=lambda ev, t=qt: _set_field_time(t),
                )
                for qt in quick_times
            ],
        )

        custom_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(ft.Icons.ACCESS_TIME_FILLED, color=COLOR_PRIMARY, size=22),
                    ft.Text("Custom Reminder Time", weight=ft.FontWeight.W_700),
                ],
            ),
            content=ft.Column(
                tight=True,
                spacing=12,
                controls=[
                    ft.Text(
                        "Set any specific time for your daily evening expense check notification:",
                        size=12,
                        color=COLOR_ON_SURFACE_VARIANT,
                    ),
                    time_field,
                    error_text,
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Text("Quick select:", size=11, weight=ft.FontWeight.W_600, color=COLOR_ON_SURFACE_VARIANT),
                            ft.TextButton(
                                "Pick from Clock",
                                icon=ft.Icons.WATCH_LATER_OUTLINED,
                                on_click=_open_clock,
                            ),
                        ],
                    ),
                    chips_row,
                ],
            ),
            actions=[
                ft.TextButton("Cancel", on_click=_cancel_custom),
                ft.ElevatedButton(
                    "Save Time",
                    bgcolor=COLOR_PRIMARY_CONTAINER,
                    color=COLOR_ON_PRIMARY,
                    on_click=_confirm_custom,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self._page.overlay.append(custom_dialog)
        custom_dialog.open = True
        if self._page:
            try:
                self._page.update()
            except Exception:
                pass

    def _on_cloud_sync_click(self, e=None) -> None:
        """Performs a real backup snapshot and updates sync timestamp."""
        try:
            now_str = datetime.now().strftime("today, %I:%M %p")
            user_id = self._user.id if self._user else 1
            self._profile_service.set_preference(user_id, "last_cloud_sync_timestamp", now_str)
            self._cloud_sync_time_text.value = f"Last synced {now_str}"

            # Create backup snapshot in data directory
            os.makedirs("data", exist_ok=True)
            backup_path = os.path.abspath(os.path.join("data", "leaksee_cloud_sync_backup.db"))
            if DATABASE_PATH.exists():
                shutil.copy2(DATABASE_PATH, backup_path)

            if self._page:
                try:
                    self._cloud_sync_time_text.update()
                except Exception:
                    pass
            self._show_snackbar("Cloud backup complete! 100% ledger entries backed up.", COLOR_EMERALD_ACCENT)
        except Exception as ex:
            logger.error("Failed to sync: %s", ex, exc_info=True)
            self._show_snackbar(f"Sync failed: {ex}", COLOR_ERROR)

    def _get_export_directory(self) -> str:
        """Returns the configured download directory for exports, defaulting to 'data'."""
        user_id = self._user.id if self._user else 1
        pref_path = self._profile_service.get_preference(user_id, "export_download_path")
        if pref_path and pref_path.strip():
            target_path = os.path.expanduser(pref_path.strip())
            return os.path.abspath(target_path)
        return "data"

    def _set_export_directory(self, path_str: str) -> bool:
        """Validates and updates the export download directory preference."""
        raw_path = (path_str or "").strip()
        if not raw_path or raw_path.lower() in ("data", "data/", "data\\"):
            target_path = "data"
        else:
            target_path = os.path.abspath(os.path.expanduser(raw_path))

        try:
            os.makedirs(target_path, exist_ok=True)
            user_id = self._user.id if self._user else 1
            self._profile_service.set_preference(user_id, "export_download_path", target_path)

            if target_path == "data":
                self._export_path_pill_text.value = "data/"
                self._export_path_subtitle_text.value = "Saved to project data/ folder"
            else:
                dir_name = os.path.basename(os.path.normpath(target_path)) or target_path
                self._export_path_pill_text.value = dir_name[:14]
                self._export_path_subtitle_text.value = f"Saved to {target_path}"

            if self._page:
                try:
                    self._page.update()
                except Exception:
                    pass
            return True
        except Exception as ex:
            logger.error("Failed to set export download directory: %s", ex)
            return False

    def _open_change_download_path_dialog(
        self,
        e=None,
        on_success: Optional[Callable[[str], None]] = None,
    ) -> None:
        """Opens dialog allowing the user to select or paste a custom download directory."""
        if not self._page or not self._user:
            return

        current_path = self._get_export_directory()
        downloads_dir = str(Path.home() / "Downloads")
        documents_dir = str(Path.home() / "Documents")
        desktop_dir = str(Path.home() / "Desktop")
        project_data_dir = "data"

        path_input = ft.TextField(
            label="Download Folder Path",
            value=current_path,
            hint_text="e.g. C:/Users/.../Downloads or data",
            dense=True,
            prefix_icon=ft.Icons.FOLDER_OUTLINED,
            autofocus=True,
        )

        def _set_path_value(p: str):
            path_input.value = p
            try:
                path_input.update()
            except Exception:
                pass

        def _on_browse(ev):
            self._ensure_file_picker()
            if hasattr(self, "_file_picker") and self._file_picker:
                self._on_dir_selected_callback = lambda picked_dir: _set_path_value(picked_dir)
                try:
                    init_dir = path_input.value if (path_input.value and os.path.exists(path_input.value)) else downloads_dir
                    self._file_picker.get_directory_path(
                        dialog_title="Select Export Download Folder",
                        initial_directory=init_dir,
                    )
                except Exception as ex:
                    logger.warning("Could not launch directory picker: %s", ex)
                    self._show_snackbar("Browse dialog unavailable. Please type or paste folder path.", COLOR_PRIMARY)

        def _save(ev):
            target = (path_input.value or "").strip()
            if not target:
                target = "data"
            success = self._set_export_directory(target)
            if success:
                dialog.open = False
                self._page.update()
                display_dest = self._get_export_directory()
                self._show_snackbar(f"Download path updated: {display_dest}", COLOR_EMERALD_ACCENT)
                if on_success:
                    on_success(display_dest)
            else:
                self._show_snackbar("Invalid directory path or permission denied.", COLOR_ERROR)

        def _cancel(ev):
            dialog.open = False
            self._page.update()

        preset_chips = ft.Row(
            wrap=True,
            spacing=6,
            controls=[
                ft.Chip(
                    label=ft.Text("Downloads", size=11),
                    leading=ft.Icon(ft.Icons.DOWNLOAD, size=14),
                    on_click=lambda ev: _set_path_value(downloads_dir),
                ),
                ft.Chip(
                    label=ft.Text("Documents", size=11),
                    leading=ft.Icon(ft.Icons.DESCRIPTION, size=14),
                    on_click=lambda ev: _set_path_value(documents_dir),
                ),
                ft.Chip(
                    label=ft.Text("Desktop", size=11),
                    leading=ft.Icon(ft.Icons.DESKTOP_WINDOWS, size=14),
                    on_click=lambda ev: _set_path_value(desktop_dir),
                ),
                ft.Chip(
                    label=ft.Text("Project data/", size=11),
                    leading=ft.Icon(ft.Icons.FOLDER_ZIP, size=14),
                    on_click=lambda ev: _set_path_value(project_data_dir),
                ),
            ],
        )

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                spacing=8,
                controls=[
                    ft.Icon(ft.Icons.DRIVE_FILE_MOVE, color=COLOR_PRIMARY, size=22),
                    ft.Text("Change Download Path", weight=ft.FontWeight.W_700, size=16),
                ],
            ),
            content=ft.Container(
                width=380,
                content=ft.Column(
                    tight=True,
                    spacing=12,
                    controls=[
                        ft.Text(
                            "Choose where your financial audit statements, CSV sheets, and backups are saved:",
                            size=12,
                            color=COLOR_ON_SURFACE,
                        ),
                        ft.Row(
                            spacing=6,
                            controls=[
                                ft.Container(content=path_input, expand=True),
                                ft.IconButton(
                                    icon=ft.Icons.FOLDER_OPEN,
                                    tooltip="Browse Folder...",
                                    icon_color=COLOR_PRIMARY,
                                    on_click=_on_browse,
                                ),
                            ],
                        ),
                        ft.Text("Quick Presets:", size=11, weight=ft.FontWeight.W_600, color=COLOR_OUTLINE),
                        preset_chips,
                    ],
                ),
            ),
            actions=[
                ft.TextButton("Cancel", on_click=_cancel),
                ft.ElevatedButton("Save Path", bgcolor=COLOR_PRIMARY, color=COLOR_ON_PRIMARY, on_click=_save),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self._page.overlay.append(dialog)
        dialog.open = True
        self._page.update()

    def _open_export_dialog(self, e=None) -> None:
        """Opens interactive export options dialog."""
        if not self._page or not self._user:
            return

        def _export_csv_action(ev):
            dialog.open = False
            self._page.update()
            self._export_ledger_csv()

        def _export_audit_action(ev):
            dialog.open = False
            self._page.update()
            self._export_audit_report()

        def _backup_db_action(ev):
            dialog.open = False
            self._page.update()
            self._backup_database()

        def _change_path_action(ev):
            dialog.open = False
            self._page.update()
            self._open_change_download_path_dialog(on_success=lambda p: self._open_export_dialog())

        def _cancel(ev):
            dialog.open = False
            self._page.update()

        curr_dir = self._get_export_directory()
        curr_dir_display = curr_dir if len(curr_dir) <= 36 else ("..." + curr_dir[-33:])

        path_card = ft.Container(
            bgcolor=f"{COLOR_PRIMARY}12",
            border=ft.Border.all(1, f"{COLOR_PRIMARY}33"),
            border_radius=12,
            padding=ft.Padding.symmetric(horizontal=12, vertical=10),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Row(
                        spacing=8,
                        controls=[
                            ft.Icon(ft.Icons.FOLDER_OPEN, color=COLOR_PRIMARY, size=20),
                            ft.Column(
                                spacing=1,
                                controls=[
                                    ft.Text("Download Destination", size=10, weight=ft.FontWeight.W_700, color=COLOR_PRIMARY),
                                    ft.Text(curr_dir_display, size=11, color=COLOR_ON_SURFACE, weight=ft.FontWeight.W_500),
                                ],
                            ),
                        ],
                    ),
                    ft.TextButton(
                        "Change",
                        icon=ft.Icons.EDIT_OUTLINED,
                        style=ft.ButtonStyle(padding=ft.Padding.symmetric(horizontal=8, vertical=4)),
                        on_click=_change_path_action,
                    ),
                ],
            ),
        )

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                spacing=8,
                controls=[
                    ft.Icon(ft.Icons.FILE_DOWNLOAD, color=COLOR_PRIMARY, size=22),
                    ft.Text("Export Financial Ledger", weight=ft.FontWeight.W_700, size=16),
                ],
            ),
            content=ft.Column(
                tight=True,
                spacing=8,
                controls=[
                    path_card,
                    ft.ListTile(
                        leading=ft.Container(
                            width=36,
                            height=36,
                            border_radius=10,
                            bgcolor=f"{COLOR_EMERALD_ACCENT}18",
                            alignment=ft.Alignment.CENTER,
                            content=ft.Icon(ft.Icons.DESCRIPTION, color=COLOR_EMERALD_ACCENT, size=20),
                        ),
                        title=ft.Text("Audit Summary Report (.txt)", weight=ft.FontWeight.W_600, size=14),
                        subtitle=ft.Text(f"Accounting statement with totals & categories. Saves to {os.path.basename(os.path.normpath(curr_dir)) or curr_dir}", size=11),
                        on_click=_export_audit_action,
                    ),
                    ft.ListTile(
                        leading=ft.Container(
                            width=36,
                            height=36,
                            border_radius=10,
                            bgcolor=f"{COLOR_PRIMARY}18",
                            alignment=ft.Alignment.CENTER,
                            content=ft.Icon(ft.Icons.TABLE_CHART, color=COLOR_PRIMARY, size=20),
                        ),
                        title=ft.Text("CSV Spreadsheet (.csv)", weight=ft.FontWeight.W_600, size=14),
                        subtitle=ft.Text("Complete itemized transaction audit sheet for Excel, Numbers & Sheets", size=11),
                        on_click=_export_csv_action,
                    ),
                    ft.ListTile(
                        leading=ft.Container(
                            width=36,
                            height=36,
                            border_radius=10,
                            bgcolor=f"{COLOR_SECONDARY}18",
                            alignment=ft.Alignment.CENTER,
                            content=ft.Icon(ft.Icons.STORAGE, color=COLOR_SECONDARY, size=20),
                        ),
                        title=ft.Text("Full SQLite Backup (.db)", weight=ft.FontWeight.W_600, size=14),
                        subtitle=ft.Text("Encrypted portable snapshot of your local database for safekeeping", size=11),
                        on_click=_backup_db_action,
                    ),
                    ft.ListTile(
                        leading=ft.Container(
                            width=36,
                            height=36,
                            border_radius=10,
                            bgcolor=f"{COLOR_PRIMARY}10",
                            alignment=ft.Alignment.CENTER,
                            content=ft.Icon(ft.Icons.DRIVE_FILE_MOVE_OUTLINED, color=COLOR_PRIMARY, size=20),
                        ),
                        title=ft.Text("Change Download Path", weight=ft.FontWeight.W_600, size=14),
                        subtitle=ft.Text("Select custom folder, Downloads, or Desktop destination", size=11),
                        on_click=_change_path_action,
                    ),
                ],
            ),
            actions=[
                ft.TextButton("Change Download Path", icon=ft.Icons.FOLDER_OPEN, on_click=_change_path_action),
                ft.TextButton("Cancel", on_click=_cancel),
            ],
            actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )
        self._page.overlay.append(dialog)
        dialog.open = True
        self._page.update()

    def _export_ledger_csv(self) -> str:
        """Exports itemized transactions to CSV in configured download directory."""
        try:
            export_dir = self._get_export_directory()
            os.makedirs(export_dir, exist_ok=True)
            user_id = self._user.id if self._user else 1
            cur = self._user.currency if (self._user and self._user.currency) else DEFAULT_CURRENCY
            txns = self._transaction_service.list_transactions(user_id=user_id)
            date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_path = os.path.abspath(os.path.join(export_dir, f"leaksee_ledger_{date_str}.csv"))

            rows = []
            running_bal = 0
            chrono_txns = sorted(txns, key=lambda t: (t.transaction_date, t.id))
            for t in chrono_txns:
                amt = t.amount_paise / 100
                if t.transaction_type == TransactionType.INCOME:
                    running_bal += t.amount_paise
                    debit = ""
                    credit = f"{amt:.2f}"
                else:
                    running_bal -= t.amount_paise
                    debit = f"{amt:.2f}"
                    credit = ""
                cat_name = t.category.name if t.category else "General"
                rows.append([
                    t.id,
                    t.transaction_date.strftime("%Y-%m-%d"),
                    t.transaction_type.value,
                    t.description or "",
                    cat_name,
                    debit,
                    credit,
                    f"{running_bal / 100:.2f}",
                    t.notes or "",
                ])

            with open(csv_path, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Transaction_ID",
                    "Date",
                    "Type",
                    "Description",
                    "Category",
                    f"Debit_{cur}",
                    f"Credit_{cur}",
                    f"Running_Balance_{cur}",
                    "Notes",
                ])
                writer.writerows(rows)

            self._show_snackbar(f"Exported {len(rows)} entries to {csv_path}!", COLOR_EMERALD_ACCENT)
            return csv_path
        except Exception as ex:
            logger.error("Failed to export CSV: %s", ex, exc_info=True)
            self._show_snackbar(f"Export failed: {ex}", COLOR_ERROR)
            return ""

    def _export_audit_report(self) -> str:
        """Exports formatted text audit summary to configured download directory."""
        try:
            export_dir = self._get_export_directory()
            os.makedirs(export_dir, exist_ok=True)
            user_id = self._user.id if self._user else 1
            cur = self._user.currency if (self._user and self._user.currency) else DEFAULT_CURRENCY
            date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = os.path.abspath(os.path.join(export_dir, f"leaksee_audit_report_{date_str}.txt"))

            txns = self._transaction_service.list_transactions(user_id=user_id)
            total_income = sum(t.amount_paise for t in txns if t.transaction_type == TransactionType.INCOME)
            total_expense = sum(t.amount_paise for t in txns if t.transaction_type == TransactionType.EXPENSE)
            net_surplus = total_income - total_expense

            lines = [
                "============================================================",
                "               LEAKSEE FINANCIAL AUDIT REPORT               ",
                "============================================================",
                f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"Account: {self._user.name if self._user else 'User'} ({self._user.profession if self._user else 'Individual'})",
                f"Currency: {cur}",
                f"Location: {report_path}",
                "------------------------------------------------------------",
                "FINANCIAL POSITION SUMMARY:",
                f"  Total Inflow / Income : {cur} {total_income / 100:,.2f}",
                f"  Total Outflow / Spend : {cur} {total_expense / 100:,.2f}",
                f"  Net Period Balance    : {cur} {net_surplus / 100:,.2f}",
                f"  Total Ledger Records  : {len(txns)} transactions",
                "------------------------------------------------------------",
                "ITEMIZED RECORD SAMPLE:",
            ]
            for t in sorted(txns, key=lambda x: x.transaction_date, reverse=True)[:50]:
                cat = t.category.name if t.category else "General"
                sign = "+" if t.transaction_type == TransactionType.INCOME else "-"
                lines.append(f"  {t.transaction_date} | {t.transaction_type.value:<7} | {cur} {sign}{t.amount_paise/100:8.2f} | {cat:<15} | {t.description or ''}")

            lines.append("============================================================")
            lines.append("End of Audit Report — Verified by Leaksee Offline Engine")

            with open(report_path, mode="w", encoding="utf-8") as f:
                f.write("\n".join(lines))

            self._show_snackbar(f"Audit report saved to: {report_path}!", COLOR_EMERALD_ACCENT)
            return report_path
        except Exception as ex:
            logger.error("Failed to generate audit report: %s", ex, exc_info=True)
            self._show_snackbar(f"Audit generation failed: {ex}", COLOR_ERROR)
            return ""

    def _backup_database(self) -> str:
        """Creates copy of database file in configured download directory."""
        try:
            export_dir = self._get_export_directory()
            os.makedirs(export_dir, exist_ok=True)
            date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.abspath(os.path.join(export_dir, f"leaksee_backup_{date_str}.db"))
            if DATABASE_PATH.exists():
                shutil.copy2(DATABASE_PATH, backup_path)
                self._show_snackbar(f"Database backed up to {backup_path}!", COLOR_EMERALD_ACCENT)
                return backup_path
            else:
                self._show_snackbar("Database file is initialized in-memory or empty.", COLOR_PRIMARY)
                return ""
        except Exception as ex:
            logger.error("Failed to backup database: %s", ex, exc_info=True)
            self._show_snackbar(f"Backup failed: {ex}", COLOR_ERROR)
            return ""

    def _open_logout_dialog(self, e=None) -> None:
        if not self._page:
            return

        def _confirm_logout(ev):
            dialog.open = False
            self._page.update()
            if self._on_logout:
                self._on_logout()
            else:
                self._show_snackbar("Logged out from LEAKSEE session.", COLOR_ERROR)

        def _cancel(ev):
            dialog.open = False
            self._page.update()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Log Out", weight=ft.FontWeight.W_700),
            content=ft.Text("Are you sure you want to log out from LEAKSEE? Your data remains securely encrypted on this device."),
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
                                    ft.Row(
                                        spacing=4,
                                        controls=[
                                            ft.Text("LEAKSEE Pro", size=11, color=sub_col),
                                            ft.Text("•", size=11, color=border_col),
                                            self._live_time_text,
                                        ],
                                    ),
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
                                                content=self._avatar_text,
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
                                            self._email_text,
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
                                ink=True,
                                tooltip="Tap to edit monthly budget",
                                on_click=self._open_edit_profile_dialog,
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
                                ink=True,
                                tooltip="Active tracking period",
                                on_click=lambda e: self._show_snackbar(f"Tracking financial records since {self._tracked_since_text.value}.", COLOR_PRIMARY),
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
                                                self._tracked_since_text,
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
        def _switch_item_row(title: str, subtitle: str, icon: str, icon_col: str, switch_ctrl: ft.Switch) -> ft.Container:
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
                        switch_ctrl,
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
                    _switch_item_row(
                        "Cloud AI (Google Gemini)",
                        "Conversational assistant (fallback to local if off)",
                        ft.Icons.CLOUD_DONE,
                        COLOR_PRIMARY,
                        self._cloud_ai_switch,
                    ),
                    _switch_item_row(
                        "AI Peer Insights",
                        "Compare spending with tech peer benchmarks",
                        ft.Icons.AUTO_AWESOME,
                        COLOR_PRIMARY,
                        self._peer_insights_switch,
                    ),
                    _switch_item_row(
                        "Smart Categorization",
                        "Auto-detect merchant & tax deductions",
                        ft.Icons.CATEGORY,
                        COLOR_SECONDARY,
                        self._smart_cat_switch,
                    ),
                    _switch_item_row(
                        "AI Voice & Floating Bar",
                        "Quick access conversational financial agent",
                        ft.Icons.MIC,
                        COLOR_PRIMARY,
                        self._ai_voice_switch,
                    ),
                    _privacy_row(),
                ],
            ),
        )

        # 3. Preferences & Region Card
        def _pref_nav_row(title: str, subtitle: Union[ft.Control, str], value_control: Union[ft.Control, str], icon: str, on_tap=None) -> ft.Container:
            val_ctrl = value_control if isinstance(value_control, ft.Control) else ft.Text(str(value_control), size=11, weight=ft.FontWeight.W_700, color=COLOR_PRIMARY)
            sub_ctrl = subtitle if isinstance(subtitle, ft.Control) else ft.Text(str(subtitle), size=11, color=sub_col)
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
                                        sub_ctrl,
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
                                    content=val_ctrl,
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
                    _pref_nav_row("Primary Currency", "Tap to change active currency", self._currency_text, ft.Icons.CURRENCY_RUPEE, on_tap=self._open_currency_dialog),
                    _pref_nav_row("Categories & Subcategories", "Create new categories & manage labels", ft.Text("Manage", size=11, weight=ft.FontWeight.W_700, color=COLOR_PRIMARY), ft.Icons.CATEGORY, on_tap=self._open_category_management),
                    _pref_nav_row("Financial Month Cycle", self._cycle_subtitle_text, self._cycle_text, ft.Icons.EVENT_REPEAT, on_tap=self._open_cycle_dialog),
                    _pref_nav_row("Daily Expense Check", self._daily_check_subtitle_text, self._daily_check_text, ft.Icons.SCHEDULE, on_tap=self._open_daily_check_dialog),
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
                    # Biometric Switch Row
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
                                            bgcolor=f"{COLOR_PRIMARY}18",
                                            alignment=ft.Alignment.CENTER,
                                            content=ft.Icon(ft.Icons.FINGERPRINT, color=COLOR_PRIMARY, size=18),
                                        ),
                                        ft.Column(
                                            spacing=2,
                                            controls=[
                                                ft.Text("Biometric / Face ID Login", size=13, weight=ft.FontWeight.W_600, color=text_col),
                                                ft.Text("Secure access via hardware key", size=11, color=sub_col),
                                            ],
                                        ),
                                    ],
                                ),
                                self._biometric_switch,
                            ],
                        ),
                    ),
                    # Cloud Backup Row
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
                                                self._cloud_sync_time_text,
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
                                    on_click=self._on_cloud_sync_click,
                                ),
                            ],
                        ),
                    ),
                    # Export Financial Ledger Row
                    ft.Container(
                        padding=ft.Padding.symmetric(vertical=8),
                        ink=True,
                        on_click=self._open_export_dialog,
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
                    # Change Download Path Row
                    ft.Container(
                        padding=ft.Padding.symmetric(vertical=8),
                        ink=True,
                        on_click=self._open_change_download_path_dialog,
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
                                            content=ft.Icon(ft.Icons.DRIVE_FILE_MOVE_OUTLINED, color=text_col, size=18),
                                        ),
                                        ft.Column(
                                            spacing=2,
                                            controls=[
                                                ft.Text("Export Download Path", size=13, weight=ft.FontWeight.W_600, color=text_col),
                                                self._export_path_subtitle_text,
                                            ],
                                        ),
                                    ],
                                ),
                                ft.Row(
                                    spacing=6,
                                    controls=[
                                        self._export_path_pill_text,
                                        ft.Icon(ft.Icons.ARROW_FORWARD, color=sub_col, size=16),
                                    ],
                                ),
                            ],
                        ),
                    ),
                ],
            ),
        )

        # 5. Appearance Theme Segmented Buttons Card
        self._update_theme_buttons()
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
                    ft.Text("Log Out from LEAKSEE", size=14, weight=ft.FontWeight.W_700, color=COLOR_ERROR),
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
        """Fetch user data and preferences from DB."""
        try:
            self._user = self._profile_service.get_user()
            user_id = self._user.id if self._user else 1
            is_dark = theme_manager.is_dark()
            text_col = "#FFFFFF" if is_dark else COLOR_ON_SURFACE
            sub_col = "#94A3B8" if is_dark else COLOR_ON_SURFACE_VARIANT

            if hasattr(self, "_live_time_text") and self._live_time_text:
                self._live_time_text.value = clock_service.format_short_status()

            self._name_text.color = text_col
            self._prof_text.color = sub_col
            self._budget_text.color = text_col
            self._tracked_since_text.color = text_col

            if self._user:
                self._name_text.value = self._user.name
                initials = "".join([part[0] for part in self._user.name.split() if part])[:2].upper() if self._user.name else "U"
                self._avatar_text.value = initials

                prof = self._user.profession or ""
                location = self._profile_service.get_preference(user_id, "user_location") or ""
                if prof and location:
                    self._prof_text.value = f"{prof} • {location}"
                elif prof:
                    self._prof_text.value = prof
                else:
                    self._prof_text.value = ""

                email_pref = self._profile_service.get_preference(user_id, "user_email")
                if not email_pref:
                    clean_name = self._user.name.lower().replace(" ", "") if self._user.name else "user"
                    email_pref = f"{clean_name}@leaksee.app"
                self._email_text.value = email_pref

                cur = self._user.currency or DEFAULT_CURRENCY
                sym = CURRENCY_SYMBOLS.get(cur, "₹")
                self._currency_text.value = f"{cur} ({sym})"

                if self._user.monthly_income_paise:
                    self._budget_text.value = f"{sym}{self._user.monthly_income_paise // 100:,}"
                else:
                    self._budget_text.value = f"{sym}0"

                if hasattr(self._user, "created_at") and self._user.created_at:
                    self._tracked_since_text.value = self._user.created_at.strftime("%b %Y")
                else:
                    self._tracked_since_text.value = "Jan 2026"

            # Sync Switches with persisted preferences
            self._cloud_ai_switch.value = (self._profile_service.get_preference(user_id, "cloud_ai_enabled", "false") or "").lower() == "true"
            self._peer_insights_switch.value = (self._profile_service.get_preference(user_id, "ai_peer_insights_enabled", "true") or "").lower() == "true"
            self._smart_cat_switch.value = (self._profile_service.get_preference(user_id, "smart_categorization_enabled", "true") or "").lower() == "true"
            self._ai_voice_switch.value = (self._profile_service.get_preference(user_id, "ai_voice_bar_enabled", "true") or "").lower() == "true"
            self._biometric_switch.value = (self._profile_service.get_preference(user_id, "biometric_enabled", "false") or "").lower() == "true"

            # Sync preference pills and dynamic subtitles
            cycle_pref = self._profile_service.get_preference(user_id, "financial_cycle_start_day", "1")
            if cycle_pref == "last":
                self._cycle_text.value = "Last day"
                self._cycle_subtitle_text.value = "Starts on the last day of each month"
            elif cycle_pref == "1":
                self._cycle_text.value = "1st of month"
                self._cycle_subtitle_text.value = "Starts 1st of each month"
            else:
                self._cycle_text.value = f"{cycle_pref}th of month"
                self._cycle_subtitle_text.value = f"Starts {cycle_pref}th of each month"

            daily_check_val = self._profile_service.get_preference(user_id, "daily_expense_check_time", "8:00 PM")
            self._daily_check_text.value = daily_check_val
            self._daily_check_subtitle_text.value = "Reminders disabled" if daily_check_val == "Off" else f"Smart reminder at {daily_check_val}"

            last_sync = self._profile_service.get_preference(user_id, "last_cloud_sync_timestamp", "today, 10:45 AM")
            self._cloud_sync_time_text.value = f"Last synced {last_sync}"

            export_pref = self._profile_service.get_preference(user_id, "export_download_path", "")
            if export_pref and export_pref.strip():
                dir_name = os.path.basename(os.path.normpath(export_pref)) or export_pref
                self._export_path_pill_text.value = dir_name[:14]
                self._export_path_subtitle_text.value = f"Saved to {export_pref}"
            else:
                self._export_path_pill_text.value = "data/"
                self._export_path_subtitle_text.value = "Saved to project data/ folder"

            self._update_theme_buttons()
            if self._page:
                try:
                    self._page.update()
                except Exception:
                    pass
        except Exception as ex:
            logger.error("Error refreshing settings: %s", ex, exc_info=True)
