"""
Spendora — Date Range Picker Dialog (Flet).

Enables calculating between any 2 arbitrary dates:
- Custom Year / Month / Day selection for Start Date and End Date
- Quick presets: "This Month", "Last Month (31 Days)", "Last 90 Days", "Year to Date"
- Visual verification of days selected
- Direct callback with (start_date, end_date) to recalculate gain/loss summaries
"""

from __future__ import annotations

import calendar
from datetime import date, timedelta
from typing import Callable
import flet as ft

from config.settings import COLOR_PRIMARY, COLOR_ON_PRIMARY
from config.theme_manager import theme_manager


def show_date_range_dialog(
    page: ft.Page,
    current_start: date,
    current_end: date,
    on_apply: Callable[[date, date], None],
) -> None:
    """Display interactive date range selection dialog."""
    is_dark = theme_manager.is_dark()
    bg_color = "#0B0F19" if is_dark else "#FAF8FF"
    card_bg = "#151D30" if is_dark else "#FFFFFF"
    input_bg = "#0F1726" if is_dark else "#F8FAFC"
    border_color = "#222E48" if is_dark else "#E2E8F0"
    text_primary = "#FFFFFF" if is_dark else "#151B2B"
    text_secondary = "#94A3B8" if is_dark else "#747688"
    accent_purple = "#8B5CF6" if is_dark else COLOR_PRIMARY

    start_val = [current_start]
    end_val = [current_end]

    start_text = ft.Text(current_start.strftime("%d %B %Y"), size=14, weight=ft.FontWeight.W_700, color=text_primary)
    end_text = ft.Text(current_end.strftime("%d %B %Y"), size=14, weight=ft.FontWeight.W_700, color=text_primary)
    days_badge = ft.Text(f"{(current_end - current_start).days + 1} Days Selected", size=11, weight=ft.FontWeight.W_700, color=accent_purple)

    def _update_ui():
        num_days = (end_val[0] - start_val[0]).days + 1
        start_text.value = start_val[0].strftime("%d %B %Y")
        end_text.value = end_val[0].strftime("%d %B %Y")
        days_badge.value = f"{num_days} Days Selected"
        try:
            start_text.update()
            end_text.update()
            days_badge.update()
        except Exception:
            pass

    def _apply_preset(s: date, e: date):
        start_val[0] = s
        end_val[0] = e
        _update_ui()

    today = date.today()

    # Presets
    def _set_this_month(e):
        s = date(today.year, today.month, 1)
        _apply_preset(s, today)

    def _set_last_month(e):
        first_this = date(today.year, today.month, 1)
        prev_end = first_this - timedelta(days=1)
        prev_start = date(prev_end.year, prev_end.month, 1)
        _apply_preset(prev_start, prev_end)

    def _set_last_90(e):
        s = today - timedelta(days=90)
        _apply_preset(s, today)

    # Date adjustments (+/- days)
    def _shift_start(days: int):
        new_d = start_val[0] + timedelta(days=days)
        if new_d <= end_val[0]:
            start_val[0] = new_d
            _update_ui()

    def _shift_end(days: int):
        new_d = end_val[0] + timedelta(days=days)
        if new_d >= start_val[0]:
            end_val[0] = new_d
            _update_ui()

    preset_chips = ft.Row(
        spacing=8,
        controls=[
            ft.Container(
                bgcolor=input_bg,
                border=ft.Border.all(1, border_color),
                border_radius=12,
                padding=ft.Padding.symmetric(horizontal=10, vertical=6),
                ink=True,
                content=ft.Text("This Month", size=11, color=text_primary, weight=ft.FontWeight.W_600),
                on_click=_set_this_month,
            ),
            ft.Container(
                bgcolor=input_bg,
                border=ft.Border.all(1, border_color),
                border_radius=12,
                padding=ft.Padding.symmetric(horizontal=10, vertical=6),
                ink=True,
                content=ft.Text("Last Month", size=11, color=text_primary, weight=ft.FontWeight.W_600),
                on_click=_set_last_month,
            ),
            ft.Container(
                bgcolor=input_bg,
                border=ft.Border.all(1, border_color),
                border_radius=12,
                padding=ft.Padding.symmetric(horizontal=10, vertical=6),
                ink=True,
                content=ft.Text("Last 90 Days", size=11, color=text_primary, weight=ft.FontWeight.W_600),
                on_click=_set_last_90,
            ),
        ],
    )

    def _date_selector_box(label: str, text_ctrl: ft.Text, on_minus: Callable, on_plus: Callable, on_jump_month: Callable) -> ft.Container:
        return ft.Container(
            bgcolor=card_bg,
            border=ft.Border.all(1, border_color),
            border_radius=16,
            padding=ft.Padding.all(12),
            content=ft.Column(
                spacing=8,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text(label, size=11, weight=ft.FontWeight.W_700, color=text_secondary),
                            ft.IconButton(
                                icon=ft.Icons.CALENDAR_MONTH,
                                icon_size=16,
                                icon_color=accent_purple,
                                tooltip="Jump by month",
                                on_click=on_jump_month,
                            ),
                        ],
                    ),
                    text_ctrl,
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.IconButton(ft.Icons.REMOVE_CIRCLE_OUTLINE, icon_size=20, icon_color=accent_purple, on_click=lambda ev: on_minus(-1)),
                            ft.Text("Adjust Day", size=10, color=text_secondary),
                            ft.IconButton(ft.Icons.ADD_CIRCLE_OUTLINE, icon_size=20, icon_color=accent_purple, on_click=lambda ev: on_plus(1)),
                        ],
                    ),
                ],
            ),
        )

    def _jump_start_month(e):
        # subtract 1 month
        y = start_val[0].year
        m = start_val[0].month - 1
        if m < 1:
            m = 12
            y -= 1
        d = min(start_val[0].day, calendar.monthrange(y, m)[1])
        new_d = date(y, m, d)
        if new_d <= end_val[0]:
            start_val[0] = new_d
            _update_ui()

    def _jump_end_month(e):
        # add 1 month
        y = end_val[0].year
        m = end_val[0].month + 1
        if m > 12:
            m = 1
            y += 1
        d = min(end_val[0].day, calendar.monthrange(y, m)[1])
        new_d = date(y, m, d)
        if new_d >= start_val[0]:
            end_val[0] = new_d
            _update_ui()

    def _close(e=None):
        dlg.open = False
        try:
            page.update()
        except Exception:
            pass

    def _confirm(e):
        dlg.open = False
        try:
            page.update()
        except Exception:
            pass
        on_apply(start_val[0], end_val[0])

    dlg = ft.AlertDialog(
        modal=True,
        bgcolor=bg_color,
        content_padding=ft.Padding.all(18),
        shape=ft.RoundedRectangleBorder(radius=24),
        content=ft.Container(
            width=380,
            content=ft.Column(
                tight=True,
                spacing=14,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text("Select Calculation Window", size=16, weight=ft.FontWeight.W_800, color=text_primary),
                            ft.Container(
                                bgcolor=input_bg,
                                border_radius=12,
                                padding=ft.Padding.symmetric(horizontal=8, vertical=3),
                                content=days_badge,
                            ),
                        ],
                    ),
                    ft.Text("Quick Presets", size=11, color=text_secondary, weight=ft.FontWeight.W_600),
                    preset_chips,
                    ft.Divider(color=border_color, height=8),
                    _date_selector_box("Start Date (From)", start_text, _shift_start, _shift_start, _jump_start_month),
                    _date_selector_box("End Date (To)", end_text, _shift_end, _shift_end, _jump_end_month),
                ],
            ),
        ),
        actions=[
            ft.TextButton("Cancel", on_click=_close),
            ft.ElevatedButton(
                "Apply & Calculate",
                bgcolor=accent_purple,
                color="#FFFFFF",
                on_click=_confirm,
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    page.overlay.append(dlg)
    dlg.open = True
    try:
        page.update()
    except Exception:
        pass
