"""
Leaksee — Main Application Entry Point (Flet 1.0).

Engineered to match Google Stitch "Trackz AI Expense Tracker" design:
- Dual Responsive Shell: Centers beautifully on Desktop/Web, expands seamlessly on Mobile
- Centralized Dark Mode & Dynamic Theme Toggling
- Responsive 5-Slot Dock Navigation Bar:
    - Tab 0: Home (Dashboard with Balance, Sparkline, Overview, AI Insight, Recent Transactions)
    - Tab 1: History (Searchable & Filterable transactions list with active chips)
    - Tab 2: AI Log (AI Financial Concierge chat & actionable insights)
    - Tab 3: Analytics (Net Gain/Loss, Category charts, Simulation sandbox)
    - Tab 4: Settings (Profile edit, Currency picker, Cloud backup, Theme segmented buttons)

Run with:
    python main.py         # Desktop / Mobile preview
    python main.py --web   # Web browser mode
"""

from __future__ import annotations

import logging
import os
import sys
import warnings

# Clean console warnings for Flet 1.0
warnings.filterwarnings("ignore", category=DeprecationWarning)

from datetime import datetime
import flet as ft
import utils.flet_compat  # Flet 1.0 structural and control compatibility layer

from services.clock_service import clock_service

from config.settings import (
    COLOR_BACKGROUND,
    COLOR_ON_PRIMARY,
    COLOR_ON_SURFACE,
    COLOR_OUTLINE_VARIANT,
    COLOR_PRIMARY,
    COLOR_PRIMARY_CONTAINER,
    COLOR_SECONDARY,
    COLOR_SURFACE_CARD,
    COLOR_SURFACE_CONTAINER,
    COLOR_SURFACE_LOW,
    DEBUG,
    LOG_LEVEL,
)
from config.theme_manager import ThemeMode, theme_manager
from database.database import init_db
from database.models import Transaction
from screens.analytics.analytics_screen import AnalyticsView
from screens.assistant.assistant_screen import AssistantView
from screens.dashboard.dashboard_screen import DashboardView
from screens.onboarding.welcome_screen import WelcomeView
from screens.personalization.personalization_screen import PersonalizationView
from screens.transactions.add_edit_transaction_screen import AddEditTransactionView
from screens.transactions.transactions_screen import TransactionsView
from services.profile_service import ProfileService

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


def main(page: ft.Page) -> None:
    """Flet application bootstrap with responsive Web and Mobile support."""
    # 1. Initialize SQLite Database & Tables
    init_db()

    # 2. Window & Page Settings
    page.title = "LEAKSEE — Intelligent Financial AI"
    page.padding = 0
    page.spacing = 0

    # Mobile viewport defaults (for desktop preview window)
    if hasattr(page, "window") and page.window:
        page.window.width = 440
        page.window.height = 890
        page.window.min_width = 360
        page.window.min_height = 680
        try:
            page.window.icon = "assets/icon.png"
        except Exception:
            pass

    # 3. Theme Initialization
    theme_manager.set_page(page)
    theme_manager.load_saved_preference(page)
    active_colors = theme_manager.get_colors()
    page.bgcolor = active_colors["background"]
    page.theme_mode = ft.ThemeMode.DARK if theme_manager.is_dark() else ft.ThemeMode.LIGHT

    profile_service = ProfileService()

    # 4. Responsive Container Shell
    # On Mobile devices (< 500px width), it stretches fluidly (100% width).
    # On Web/Desktop (>= 500px width), it stays centered within a 440px phone canvas.
    content_area = ft.Container(expand=True)

    def _is_wide() -> bool:
        return page.width is not None and page.width >= 500

    app_container = ft.Container(
        content=content_area,
        width=440 if _is_wide() else None,
        expand=True,
        alignment=ft.Alignment.TOP_CENTER,
    )

    shell_wrapper = ft.Container(
        content=app_container,
        alignment=ft.Alignment.TOP_CENTER,
        expand=True,
        bgcolor=active_colors["background"],
    )

    def _on_page_resize(e):
        wide = _is_wide()
        app_container.width = 440 if wide else None
        try:
            app_container.update()
        except Exception:
            pass

    page.on_resize = _on_page_resize

    # 5. Bottom Navigation Dock (Google Stitch 5-Slot Dock)
    # [ Home | History | (Floating AI Assist) | Analytics | Settings ]
    current_tab = [0]
    dock_slot_controls = []

    def _get_dock_colors():
        c = theme_manager.get_colors()
        active_col = c["primary"]
        inactive_col = c["outline"]
        bg_col = c["surface_card"]
        border_col = c["outline_variant"]
        return active_col, inactive_col, bg_col, border_col

    def _update_dock_ui():
        active_col, inactive_col, bg_col, border_col = _get_dock_colors()
        cur = current_tab[0]
        stitch_dock.bgcolor = bg_col
        stitch_dock.border = ft.Border.only(top=ft.BorderSide(1, border_col))
        for idx, (icon_ctrl, dot_ctrl) in enumerate(dock_slot_controls):
            if icon_ctrl is not None:
                is_active = (idx == cur)
                icon_ctrl.color = active_col if is_active else inactive_col
                dot_ctrl.bgcolor = active_col if is_active else "transparent"
        try:
            stitch_dock.update()
        except Exception:
            pass

    def _build_dock_slot(idx: int, icon_name: str, tooltip_str: str) -> ft.Container:
        active_col, inactive_col, _, _ = _get_dock_colors()
        is_active = (idx == current_tab[0])
        icon_ctrl = ft.Icon(icon_name, size=24, color=active_col if is_active else inactive_col)
        dot_ctrl = ft.Container(
            width=5,
            height=5,
            border_radius=3,
            bgcolor=active_col if is_active else "transparent",
            margin=ft.Margin(top=2, left=0, right=0, bottom=0),
        )
        dock_slot_controls.append((icon_ctrl, dot_ctrl))
        return ft.Container(
            ink=True,
            border_radius=16,
            padding=ft.Padding.symmetric(horizontal=12, vertical=6),
            tooltip=tooltip_str,
            on_click=lambda e, i=idx: _switch_tab(i),
            content=ft.Column(
                spacing=0,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                tight=True,
                controls=[icon_ctrl, dot_ctrl],
            ),
        )

    # Slots 0 and 1
    slot_0 = _build_dock_slot(0, ft.Icons.HOME, "Home")
    slot_1 = _build_dock_slot(1, ft.Icons.RECEIPT_LONG, "History")

    # Slot 2: Center Elevated Floating AI Assist Action Button
    dock_slot_controls.append((None, None))
    slot_2_fab = ft.Container(
        margin=ft.Margin(top=-22, left=0, right=0, bottom=0),
        width=52,
        height=52,
        border_radius=26,
        gradient=ft.LinearGradient(
            begin=ft.Alignment.TOP_LEFT,
            end=ft.Alignment.BOTTOM_RIGHT,
            colors=["#1E58FF", "#712AE2"],
        ),
        shadow=ft.BoxShadow(
            spread_radius=1,
            blur_radius=16,
            color="#712AE266",
            offset=ft.Offset(0, 4),
        ),
        alignment=ft.Alignment.CENTER,
        ink=True,
        tooltip="Leaksee AI Concierge",
        on_click=lambda e: _switch_tab(2),
        content=ft.Icon(ft.Icons.AUTO_AWESOME, color="#FFFFFF", size=24),
    )

    # Slots 3 and 4
    slot_3 = _build_dock_slot(3, ft.Icons.BAR_CHART, "Analytics")
    slot_4 = _build_dock_slot(4, ft.Icons.SETTINGS, "Settings")

    stitch_dock = ft.Container(
        bgcolor=active_colors["surface_card"],
        border=ft.Border.only(top=ft.BorderSide(1, active_colors["outline_variant"])),
        border_radius=ft.BorderRadius(top_left=28, top_right=28, bottom_left=0, bottom_right=0),
        shadow=ft.BoxShadow(spread_radius=1, blur_radius=20, color="#00000018", offset=ft.Offset(0, -4)),
        padding=ft.Padding.symmetric(horizontal=16, vertical=6),
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_AROUND,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[slot_0, slot_1, slot_2_fab, slot_3, slot_4],
        ),
    )

    # 5.5 Universal Real-Time Top Status Bar (Visible everywhere across all views)
    status_day_date_text = ft.Text(
        clock_service.format_day_and_date(),
        size=11,
        weight=ft.FontWeight.W_600,
        color=active_colors["on_surface_variant"],
    )
    status_time_text = ft.Text(
        clock_service.get_time_formatted(),
        size=11,
        weight=ft.FontWeight.W_800,
        color=active_colors["primary"],
    )
    status_live_chip = ft.Container(
        bgcolor="#10B9811A",
        border=ft.Border.all(1, "#10B98144"),
        border_radius=8,
        padding=ft.Padding.symmetric(horizontal=6, vertical=2),
        content=ft.Row(
            spacing=4,
            tight=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(width=5, height=5, border_radius=2.5, bgcolor="#10B981"),
                ft.Text("LIVE", size=9, weight=ft.FontWeight.W_800, color="#10B981"),
            ],
        ),
    )
    universal_status_bar = ft.Container(
        bgcolor=active_colors["surface_card"],
        border=ft.Border.only(bottom=ft.BorderSide(1, active_colors["outline_variant"])),
        padding=ft.Padding.symmetric(horizontal=16, vertical=5),
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Row(
                    spacing=5,
                    tight=True,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Icon(ft.Icons.CALENDAR_MONTH, size=13, color=active_colors["primary"]),
                        status_day_date_text,
                    ],
                ),
                ft.Row(
                    spacing=5,
                    tight=True,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Icon(ft.Icons.SCHEDULE, size=13, color=active_colors["primary"]),
                        status_time_text,
                    ],
                ),
                status_live_chip,
            ],
        ),
    )

    def _on_clock_tick_global(now: datetime) -> None:
        new_date = clock_service.format_day_and_date(now)
        new_time = clock_service.get_time_formatted(now)
        updated = False
        if status_day_date_text.value != new_date:
            status_day_date_text.value = new_date
            updated = True
        if status_time_text.value != new_time:
            status_time_text.value = new_time
            updated = True
        if updated and clock_service.is_control_attached(universal_status_bar):
            try:
                status_day_date_text.update()
                status_time_text.update()
            except Exception:
                pass

    clock_service.subscribe(_on_clock_tick_global)

    app_layout = ft.Column(
        spacing=0,
        expand=True,
        controls=[
            universal_status_bar,
            content_area,
            stitch_dock,
        ],
    )
    app_container.content = app_layout

    # 6. Navigation State & Helpers
    current_tab = [0]
    current_nav_state = {"view": "tab", "txn": None, "type": "EXPENSE"}
    welcome_view_ref: list[Optional[WelcomeView]] = [None]

    def _switch_tab(index: int) -> None:
        current_tab[0] = index
        current_nav_state["view"] = "tab"
        current_nav_state["txn"] = None
        _update_dock_ui()
        if index == 0:
            content_area.content = dashboard_control
            dashboard_view.refresh()
        elif index == 1:
            content_area.content = transactions_control
            transactions_view.refresh()
        elif index == 2:
            content_area.content = assistant_control
            assistant_view.refresh()
        elif index == 3:
            content_area.content = analytics_control
            analytics_view.refresh()
        elif index == 4:
            content_area.content = personalization_control
            personalization_view.refresh()
        try:
            page.update()
        except Exception:
            content_area.update()

    def _navigate_to_add(txn_type: str = "EXPENSE") -> None:
        current_nav_state["view"] = "add_edit"
        current_nav_state["txn"] = None
        current_nav_state["type"] = txn_type
        content_area.content = add_edit_view.build(None, initial_type=txn_type)
        try:
            page.update()
        except Exception:
            content_area.update()

    def _navigate_to_edit(txn: Transaction) -> None:
        current_nav_state["view"] = "add_edit"
        current_nav_state["txn"] = txn
        t_type = txn.transaction_type.value if hasattr(txn.transaction_type, "value") else str(txn.transaction_type)
        current_nav_state["type"] = t_type
        content_area.content = add_edit_view.build(txn)
        try:
            page.update()
        except Exception:
            content_area.update()

    def _go_back() -> None:
        current_nav_state["view"] = "tab"
        current_nav_state["txn"] = None
        _switch_tab(current_tab[0])

    def _on_logout() -> None:
        """Reset session to welcome screen."""
        page.clean()
        welcome_view = WelcomeView(on_complete=_start_main_app)
        welcome_view.set_page(page)
        welcome_view_ref[0] = welcome_view
        content_area.content = welcome_view.build()
        app_container.content = content_area
        page.add(shell_wrapper)
        page.update()

    # 7. Instantiate Views
    dashboard_view = DashboardView(
        navigate_to_add_txn=_navigate_to_add,
        navigate_to_edit_txn=_navigate_to_edit,
        switch_to_tab=_switch_tab,
    )
    dashboard_view.set_page(page)

    transactions_view = TransactionsView(
        navigate_to_add_txn=_navigate_to_add,
        navigate_to_edit_txn=_navigate_to_edit,
        switch_to_tab=_switch_tab,
    )
    transactions_view.set_page(page)

    add_edit_view = AddEditTransactionView(go_back_fn=_go_back)
    add_edit_view.set_page(page)

    analytics_view = AnalyticsView(switch_to_tab=_switch_tab)
    analytics_view.set_page(page)

    assistant_view = AssistantView(switch_to_tab=_switch_tab)
    assistant_view.set_page(page)

    personalization_view = PersonalizationView(
        switch_to_tab=_switch_tab,
        on_logout=_on_logout,
    )
    personalization_view.set_page(page)

    dashboard_control = dashboard_view.build()
    transactions_control = transactions_view.build()
    add_edit_control = add_edit_view.build()
    analytics_control = analytics_view.build()
    assistant_control = assistant_view.build()
    personalization_control = personalization_view.build()

    # 8. Rebuild Views & Global Theme Listener Callback
    def _rebuild_all_views() -> None:
        nonlocal dashboard_control, transactions_control, add_edit_control, analytics_control, assistant_control, personalization_control
        dashboard_control = dashboard_view.build()
        transactions_control = transactions_view.build()
        add_edit_control = add_edit_view.build(
            current_nav_state["txn"],
            initial_type=current_nav_state["type"],
        )
        analytics_control = analytics_view.build()
        assistant_control = assistant_view.build()
        personalization_control = personalization_view.build()

    def _on_app_theme_changed(is_dark: bool):
        c = theme_manager.get_colors()
        page.theme_mode = ft.ThemeMode.DARK if is_dark else ft.ThemeMode.LIGHT
        page.bgcolor = c["background"]
        shell_wrapper.bgcolor = c["background"]
        universal_status_bar.bgcolor = c["surface_card"]
        universal_status_bar.border = ft.Border.only(bottom=ft.BorderSide(1, c["outline_variant"]))
        status_day_date_text.color = c["on_surface_variant"]
        status_time_text.color = c["primary"]
        try:
            universal_status_bar.update()
        except Exception:
            pass
        _update_dock_ui()

        if not profile_service.has_profile() and welcome_view_ref[0]:
            content_area.content = welcome_view_ref[0].build()
        elif current_nav_state["view"] == "add_edit":
            _rebuild_all_views()
            content_area.content = add_edit_control
        else:
            _rebuild_all_views()
            _switch_tab(current_tab[0])

        try:
            page.update()
        except Exception:
            pass

    theme_manager.register_listener(_on_app_theme_changed)

    # 9. App Router: Onboarding vs Main Application
    def _start_main_app() -> None:
        page.clean()
        content_area.content = dashboard_control
        dashboard_view.refresh()
        app_container.content = app_layout
        _update_dock_ui()
        page.add(shell_wrapper)
        page.update()

    if not profile_service.has_profile():
        welcome_view = WelcomeView(on_complete=_start_main_app)
        welcome_view.set_page(page)
        welcome_view_ref[0] = welcome_view
        content_area.content = welcome_view.build()
        app_container.content = content_area
        page.add(shell_wrapper)
        page.update()
    else:
        _start_main_app()


if __name__ == "__main__":
    is_web = "--web" in sys.argv or "-w" in sys.argv or os.environ.get("LEAKSEE_WEB") == "1" or os.environ.get("SPENDORA_WEB") == "1"
    if is_web:
        port = int(os.environ.get("PORT", 8550))
        print(f"🚀 Launching LEAKSEE on Web browser at http://localhost:{port}")
        ft.run(main, view=ft.AppView.WEB_BROWSER, port=port)
    else:
        ft.run(main)
