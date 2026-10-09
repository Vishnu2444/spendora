"""
Leaksee — Dashboard Screen (Flet).

faithfully reproduces the "LEAKSEE - Dashboard" screen:
- Top Header: Leaksee coin icon, "LEAKSEE", greeting, user avatar with status ring
- Hero Card: "LEAKSEE CARD"
    - Electric Blue gradient background (from-[#1E58FF] via-[#2A5BFF] to-[#0036BB])
    - Contactless chip icon (gold gradient)
    - Live Sync pill with pulsing indicator
    - Real-time Balance display
    - Bottom formula: "Salary − Expenses" (e.g. ₹66,280 − ₹24,000)
- Quick Action Pills:
    - "+ Add Expense" (Coral gradient #FF5A36 to #E03E1A)
    - "Categories" (White pill + badge)
    - "Analytics" (White pill with trending_up)
- Spending Breakdown Card:
    - Multi-colored Donut Chart with total in center
    - High-contrast legend table (Label, Amount, colored dots)
- Recent Expenses Feed:
    - Item cards with soft-colored icon squares, timestamp, amount, and category pill
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Callable, Optional

import flet as ft
import flet_charts as fc

from services.clock_service import clock_service

from components.transaction_card import build_transaction_card
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
    COLOR_SURFACE_CARD,
    COLOR_SURFACE_CONTAINER,
    COLOR_SURFACE_LOW,
    COLOR_TERTIARY_CONTAINER,
    DEFAULT_CURRENCY,
    CURRENCY_SYMBOLS,
)
from config.theme_manager import theme_manager
from database.models import Transaction, User
from services.analytics_service import AnalyticsService
from services.calculation_service import CalculationService
from services.profile_service import ProfileService
from services.transaction_service import TransactionService
from utils.date_utils import date_range_this_month
from utils.formatting import format_currency

logger = logging.getLogger(__name__)


class DashboardView:
    """Dashboard view matching Leaksee design."""

    def __init__(
        self,
        navigate_to_add_txn: Optional[Callable[[], None]] = None,
        navigate_to_edit_txn: Optional[Callable[[Transaction], None]] = None,
        switch_to_tab: Optional[Callable[[int], None]] = None,
    ) -> None:
        self._profile_service = ProfileService()
        self._calculation_service = CalculationService()
        self._analytics_service = AnalyticsService()
        self._transaction_service = TransactionService()
        self._user: Optional[User] = None
        self._navigate_to_add_txn = navigate_to_add_txn
        self._navigate_to_edit_txn = navigate_to_edit_txn
        self._switch_to_tab = switch_to_tab
        self._page: Optional[ft.Page] = None

        # Theme toggle icon
        self._theme_icon = ft.IconButton(
            icon=ft.Icons.LIGHT_MODE if theme_manager.is_dark() else ft.Icons.DARK_MODE,
            icon_color=COLOR_ON_SURFACE_VARIANT,
            icon_size=20,
            tooltip="Toggle Dark Mode",
            on_click=lambda e: theme_manager.toggle(self._page),
        )
        theme_manager.register_listener(self._on_theme_changed)

        # Dynamic Controls
        self._greeting_title = ft.Text(
            clock_service.get_greeting_str(),
            size=20,
            weight=ft.FontWeight.W_800,
            color=COLOR_ON_SURFACE,
        )
        self._greeting_subtext = ft.Text(
            spans=[
                ft.TextSpan("", style=ft.TextStyle(color=COLOR_PRIMARY, weight=ft.FontWeight.W_700, size=13)),
                ft.TextSpan(" • ", style=ft.TextStyle(color=COLOR_OUTLINE_VARIANT, size=12)),
                ft.TextSpan("", style=ft.TextStyle(color=COLOR_ON_SURFACE_VARIANT, weight=ft.FontWeight.W_500, size=12)),
            ]
        )
        self._date_subtext = ft.Text(
            clock_service.format_live_display(),
            size=11,
            color=COLOR_OUTLINE,
            weight=ft.FontWeight.W_600,
        )
        self._live_indicator_dot = ft.Container(
            width=6,
            height=6,
            border_radius=3,
            bgcolor=COLOR_EMERALD_ACCENT,
        )
        self._live_date_badge = ft.Container(
            bgcolor="#10B98115",
            border=ft.Border.all(1, "#10B98133"),
            border_radius=8,
            padding=ft.Padding.symmetric(horizontal=7, vertical=3),
            content=ft.Row(
                spacing=5,
                tight=True,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    self._live_indicator_dot,
                    self._date_subtext,
                ],
            ),
        )
        clock_service.subscribe(self._on_clock_tick)

        # LEAKSEE CARD Controls
        self._balance_text = ft.Text(
            "₹0.00",
            size=30,
            weight=ft.FontWeight.W_800,
            color=COLOR_ON_PRIMARY,
        )
        self._deduction_text = ft.Text(
            "Income: ₹0.00  •  Expenses: ₹0.00",
            size=12,
            weight=ft.FontWeight.W_700,
            color=COLOR_ON_PRIMARY,
        )

        # Breakdown Donut Chart
        self._donut_container = ft.Container(height=160, alignment=ft.Alignment.CENTER)
        self._legend_column = ft.Column(spacing=8)

        # Recent Transactions
        self._recent_list = ft.Column(spacing=10)

    def set_page(self, page: ft.Page) -> None:
        self._page = page

    def _on_clock_tick(self, now: datetime) -> None:
        """Handle real-time 1-second clock ticks."""
        if hasattr(self, "_date_subtext") and self._date_subtext:
            new_text = clock_service.format_live_display(now)
            if self._date_subtext.value != new_text:
                self._date_subtext.value = new_text
            if clock_service.is_control_attached(self._date_subtext):
                try:
                    self._date_subtext.update()
                except Exception:
                    pass

        if hasattr(self, "_greeting_title") and self._greeting_title:
            new_greet = clock_service.get_greeting_str(now)
            if self._greeting_title.value != new_greet:
                self._greeting_title.value = new_greet
            if clock_service.is_control_attached(self._greeting_title):
                try:
                    self._greeting_title.update()
                except Exception:
                    pass

    def _on_theme_changed(self, is_dark: bool) -> None:
        self._theme_icon.icon = ft.Icons.LIGHT_MODE if is_dark else ft.Icons.DARK_MODE
        self._theme_icon.icon_color = "#F8FAFC" if is_dark else COLOR_ON_SURFACE_VARIANT
        text_col = "#FFFFFF" if is_dark else COLOR_ON_SURFACE
        sub_col = "#908FA0" if is_dark else COLOR_ON_SURFACE_VARIANT
        if hasattr(self, "_greeting_title") and self._greeting_title:
            self._greeting_title.color = text_col
            try:
                self._greeting_title.update()
            except Exception:
                pass
        if hasattr(self, "_date_subtext") and self._date_subtext:
            self._date_subtext.color = sub_col
            try:
                self._date_subtext.update()
            except Exception:
                pass
        if hasattr(self, "_top_bar") and self._top_bar:
            self._top_bar.bgcolor = "#1E293B" if is_dark else COLOR_SURFACE_CARD
            try:
                self._top_bar.update()
            except Exception:
                pass
        try:
            self._theme_icon.update()
        except Exception:
            pass

    def _on_live_sync_click(self, e) -> None:
        self.refresh()
        if self._page:
            self._page.snack_bar = ft.SnackBar(
                ft.Text("Ledger balance synchronized with live transactions.", color="#FFFFFF"),
                bgcolor="#10B981",
                duration=2000,
            )
            self._page.snack_bar.open = True
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

    def _open_quick_add_modal(self, e=None, txn_type: str = "EXPENSE") -> None:
        if not self._page:
            if self._navigate_to_add_txn:
                self._navigate_to_add_txn()
            return

        is_dark = theme_manager.is_dark()
        card_bg = "#151D30" if is_dark else COLOR_SURFACE_CARD
        border_col = "#222E48" if is_dark else COLOR_OUTLINE_VARIANT
        text_col = "#FFFFFF" if is_dark else COLOR_ON_SURFACE

        is_income = (txn_type.upper() == "INCOME")
        accent_color = COLOR_EMERALD_ACCENT if is_income else COLOR_CORAL_ACCENT
        gradient_colors = [COLOR_EMERALD_ACCENT, "#059669"] if is_income else [COLOR_CORAL_ACCENT, "#E03E1A"]
        modal_title = "Add Income" if is_income else "Add Expense"
        hint_desc = "e.g. Salary, Freelance, Bonus" if is_income else "e.g. Lunch at Cafe"
        default_desc = "Income" if is_income else "Expense"
        save_btn_label = "Save Income" if is_income else "Save Expense"

        # Ensure current user is loaded
        user = self._profile_service.get_current_user()
        if user:
            self._user = user
        user_id = self._user.id if self._user else 1
        currency = self._user.currency if (self._user and self._user.currency) else DEFAULT_CURRENCY
        curr_symbol = CURRENCY_SYMBOLS.get(currency, "₹")

        amt_input = ft.TextField(
            label=f"Amount ({curr_symbol})",
            hint_text="e.g. 350",
            autofocus=True,
            keyboard_type=ft.KeyboardType.NUMBER,
            border_color=border_col,
            focused_border_color=accent_color,
            text_size=18,
            dense=True,
        )

        desc_input = ft.TextField(
            label="Description / Source" if is_income else "Description / Store",
            hint_text=hint_desc,
            border_color=border_col,
            focused_border_color=COLOR_PRIMARY,
            text_size=14,
            dense=True,
        )

        from services.category_service import CategoryService
        cat_service = CategoryService()
        cats = cat_service.list_categories(user_id) or []
        if not cats:
            prof = self._user.profession if (self._user and self._user.profession) else "Other"
            suggestions = cat_service.get_suggestions_for_profession(prof)
            if suggestions:
                try:
                    cats = cat_service.accept_suggestions(user_id, suggestions)
                except Exception as ex:
                    logger.warning("Could not auto-seed suggestions: %s", ex)
            if not cats:
                try:
                    cat = cat_service.create_category(user_id=user_id, name="General")
                    cats = [cat]
                except Exception as ex:
                    logger.warning("Could not create general category: %s", ex)

        cat_options = [ft.dropdown.Option(text=c.name, key=str(c.id)) for c in cats]
        cat_dropdown = ft.Dropdown(
            label="Category",
            options=cat_options,
            value=cat_options[0].key if cat_options else None,
            border_color=border_col,
            dense=True,
        )

        err_text = ft.Text("", color=COLOR_ERROR, size=12, visible=False)

        def _close_dlg(ev=None):
            dialog.open = False
            if hasattr(self._page, "close"):
                try:
                    self._page.close(dialog)
                except Exception:
                    pass
            if self._page:
                try:
                    self._page.update()
                except Exception:
                    pass

        def _save_transaction(ev):
            val = (amt_input.value or "").strip().replace(",", "")
            try:
                amt_float = float(val)
                if amt_float <= 0:
                    err_text.value = "Please enter an amount greater than 0"
                    err_text.visible = True
                    if self._page:
                        self._page.update()
                    return
            except ValueError:
                err_text.value = "Please enter a valid numeric amount"
                err_text.visible = True
                if self._page:
                    self._page.update()
                return

            c_id = int(cat_dropdown.value) if (cat_dropdown.value and cat_dropdown.value.isdigit()) else None
            valid_ids = {c.id for c in cats}
            if c_id not in valid_ids:
                c_id = None

            desc = (desc_input.value or "").strip() or default_desc

            try:
                self._transaction_service.create_transaction(
                    user_id=user_id,
                    amount_str=f"{amt_float:.2f}",
                    transaction_type="INCOME" if is_income else "EXPENSE",
                    category_id=c_id,
                    description=desc,
                    transaction_date=date.today(),
                    currency=currency,
                )
                _close_dlg()
                if self._page:
                    sign = "+" if is_income else "−"
                    self._page.snack_bar = ft.SnackBar(
                        ft.Text(f"Logged {sign}{curr_symbol}{amt_float:,.2f} for {desc}", color="#FFFFFF"),
                        bgcolor="#10B981",
                        duration=2500,
                    )
                    self._page.snack_bar.open = True
                    self._page.update()
                self.refresh()
            except Exception as ex:
                logger.error("Failed to save quick %s: %s", "income" if is_income else "expense", ex, exc_info=True)
                err_text.value = f"Error: {ex}"
                err_text.visible = True
                if self._page:
                    self._page.update()

        dialog = ft.AlertDialog(
            bgcolor=card_bg,
            title=ft.Row(
                spacing=8,
                controls=[
                    ft.Container(
                        width=32,
                        height=32,
                        border_radius=16,
                        gradient=ft.LinearGradient(colors=gradient_colors),
                        alignment=ft.Alignment.CENTER,
                        content=ft.Icon(ft.Icons.ADD, color="#FFFFFF", size=18),
                    ),
                    ft.Text(modal_title, size=18, weight=ft.FontWeight.W_800, color=text_col),
                ],
            ),
            content=ft.Container(
                width=360,
                content=ft.Column(
                    spacing=14,
                    tight=True,
                    controls=[
                        amt_input,
                        desc_input,
                        cat_dropdown,
                        err_text,
                    ],
                ),
            ),
            actions=[
                ft.TextButton("Cancel", on_click=_close_dlg),
                ft.ElevatedButton(
                    content=ft.Row(
                        spacing=4,
                        tight=True,
                        controls=[
                            ft.Icon(ft.Icons.CHECK, color="#FFFFFF", size=16),
                            ft.Text(save_btn_label, color="#FFFFFF", weight=ft.FontWeight.W_700),
                        ],
                    ),
                    bgcolor=accent_color,
                    on_click=_save_transaction,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        self._page.overlay.append(dialog)
        dialog.open = True
        self._page.update()

    def _open_quick_add_income_modal(self, e=None) -> None:
        self._open_quick_add_modal(e, txn_type="INCOME")

    def build(self) -> ft.Control:
        is_dark = theme_manager.is_dark()
        card_bg = "#151D30" if is_dark else COLOR_SURFACE_CARD
        border_col = "#222E48" if is_dark else COLOR_OUTLINE_VARIANT
        text_col = "#FFFFFF" if is_dark else COLOR_ON_SURFACE
        sub_col = "#94A3B8" if is_dark else COLOR_OUTLINE

        # Top Status / Header Area
        top_bar = ft.Container(
            bgcolor="#151D30" if is_dark else COLOR_SURFACE_CARD,
            border=ft.Border.only(bottom=ft.BorderSide(1, border_col)),
            padding=ft.Padding.symmetric(horizontal=16, vertical=12),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Column(
                        spacing=2,
                        controls=[
                            ft.Row(
                                spacing=6,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                controls=[
                                    ft.Image(
                                        src="icon.png",
                                        width=20,
                                        height=20,
                                        fit="contain",
                                    ),
                                    ft.Text(
                                        "LEAKSEE",
                                        size=12,
                                        weight=ft.FontWeight.W_800,
                                        color=COLOR_PRIMARY,
                                    ),
                                ],
                            ),
                            self._greeting_title,
                            self._greeting_subtext,
                            self._live_date_badge,
                        ],
                    ),
                    ft.Row(
                        spacing=4,
                        controls=[
                            # Notification icon with unread badge
                            ft.Container(
                                content=ft.Stack(
                                    controls=[
                                        ft.IconButton(
                                            icon=ft.Icons.NOTIFICATIONS_OUTLINED,
                                            icon_color=sub_col,
                                            icon_size=22,
                                            tooltip="Notifications & Activity",
                                            on_click=self._open_notifications_sheet,
                                        ),
                                        ft.Container(
                                            width=8,
                                            height=8,
                                            border_radius=4,
                                            bgcolor=COLOR_CORAL_ACCENT,
                                            right=6,
                                            top=6,
                                        ),
                                    ],
                                ),
                            ),
                            self._theme_icon,
                            # User Avatar with online indicator (Clickable -> Settings)
                            ft.Container(
                                ink=True,
                                border_radius=21,
                                tooltip="Open Profile & Settings",
                                on_click=lambda e: self._switch_to_tab(4) if self._switch_to_tab else None,
                                content=ft.Stack(
                                    controls=[
                                        ft.Container(
                                            width=42,
                                            height=42,
                                            border_radius=21,
                                            gradient=ft.LinearGradient(
                                                begin=ft.Alignment.TOP_LEFT,
                                                end=ft.Alignment.BOTTOM_RIGHT,
                                                colors=[COLOR_PRIMARY, COLOR_SECONDARY],
                                            ),
                                            padding=ft.Padding.all(2),
                                            content=ft.Container(
                                                border_radius=19,
                                                bgcolor=card_bg,
                                                alignment=ft.Alignment.CENTER,
                                                content=ft.Icon(ft.Icons.PERSON, color=COLOR_PRIMARY, size=24),
                                            ),
                                        ),
                                        ft.Container(
                                            width=11,
                                            height=11,
                                            border_radius=6,
                                            bgcolor=COLOR_EMERALD_ACCENT,
                                            border=ft.Border.all(2, card_bg),
                                            right=0,
                                            bottom=0,
                                        ),
                                    ],
                                ),
                            ),
                        ],
                    ),
                ],
            ),
        )
        self._top_bar = top_bar

        # LEAKSEE CARD Hero
        hero_card = ft.Container(
            border_radius=24,
            padding=ft.Padding.all(20),
            gradient=ft.LinearGradient(
                begin=ft.Alignment.TOP_LEFT,
                end=ft.Alignment.BOTTOM_RIGHT,
                colors=["#1E58FF", "#2A5BFF", "#0036BB"],
            ),
            shadow=ft.BoxShadow(
                spread_radius=1,
                blur_radius=24,
                color=f"{COLOR_PRIMARY_CONTAINER}44",
                offset=ft.Offset(0, 8),
            ),
            content=ft.Column(
                spacing=14,
                controls=[
                    # Header: Branding + Live Sync Pill + Contactless Chip
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                        controls=[
                            ft.Column(
                                spacing=4,
                                controls=[
                                    ft.Row(
                                        spacing=6,
                                        controls=[
                                            ft.Text(
                                                "LEAKSEE CARD",
                                                size=10,
                                                weight=ft.FontWeight.W_800,
                                                color=COLOR_PRIMARY_FIXED,
                                            ),
                                            ft.Container(
                                                bgcolor=f"{COLOR_ON_PRIMARY}25",
                                                border_radius=10,
                                                padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                                                ink=True,
                                                tooltip="Click to sync ledger",
                                                on_click=self._on_live_sync_click,
                                                content=ft.Row(
                                                    spacing=4,
                                                    tight=True,
                                                    controls=[
                                                        ft.Container(
                                                            width=6,
                                                            height=6,
                                                            border_radius=3,
                                                            bgcolor=COLOR_EMERALD_ACCENT,
                                                        ),
                                                        ft.Text("Live Sync", size=9, weight=ft.FontWeight.W_700, color=COLOR_ON_PRIMARY),
                                                    ],
                                                ),
                                            ),
                                        ],
                                    ),
                                    ft.Text("Real-time Balance", size=12, color=f"{COLOR_ON_PRIMARY}CC", weight=ft.FontWeight.W_500),
                                    self._balance_text,
                                ],
                            ),
                            # Stylized Gold Chip Icon
                            ft.Container(
                                width=40,
                                height=30,
                                border_radius=8,
                                gradient=ft.LinearGradient(
                                    colors=["#F6D365", "#FDA085"],
                                ),
                                alignment=ft.Alignment.CENTER,
                                content=ft.Icon(ft.Icons.CONTACTLESS, color=COLOR_ON_PRIMARY, size=18),
                            ),
                        ],
                    ),
                    # Bottom Formula: Salary - Expenses
                    ft.Container(
                        border=ft.Border.only(top=ft.BorderSide(1, f"{COLOR_ON_PRIMARY}30")),
                        padding=ft.Padding.only(top=10),
                        content=ft.Column(
                            spacing=3,
                            controls=[
                                ft.Row(
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                    controls=[
                                        ft.Row(
                                            spacing=4,
                                            controls=[
                                                ft.Icon(ft.Icons.SYNC_ALT, color=COLOR_PRIMARY_FIXED, size=14),
                                                ft.Text("Cashflow", size=11, color=COLOR_PRIMARY_FIXED, weight=ft.FontWeight.W_600),
                                            ],
                                        ),
                                        self._deduction_text,
                                    ],
                                ),
                                ft.Text(
                                    "Real-time auto-deducted from recorded income",
                                    size=10,
                                    color=f"{COLOR_PRIMARY_FIXED}CC",
                                ),
                            ],
                        ),
                    ),
                ],
            ),
        )

        # Quick Action Pills Row (Stitch Design)
        add_btn = ft.Container(
            gradient=ft.LinearGradient(
                colors=[COLOR_CORAL_ACCENT, "#E03E1A"],
            ),
            border_radius=20,
            padding=ft.Padding.symmetric(horizontal=16, vertical=10),
            ink=True,
            shadow=ft.BoxShadow(spread_radius=1, blur_radius=12, color=f"{COLOR_CORAL_ACCENT}55", offset=ft.Offset(0, 4)),
            content=ft.Row(
                spacing=6,
                tight=True,
                controls=[
                    ft.Icon(ft.Icons.ADD_CIRCLE, color=COLOR_ON_PRIMARY, size=18),
                    ft.Text("Add Expense", size=13, weight=ft.FontWeight.W_700, color=COLOR_ON_PRIMARY),
                ],
            ),
            on_click=lambda e: self._open_quick_add_modal(e, txn_type="EXPENSE"),
        )

        add_income_btn = ft.Container(
            gradient=ft.LinearGradient(
                colors=[COLOR_EMERALD_ACCENT, "#059669"],
            ),
            border_radius=20,
            padding=ft.Padding.symmetric(horizontal=16, vertical=10),
            ink=True,
            shadow=ft.BoxShadow(spread_radius=1, blur_radius=12, color=f"{COLOR_EMERALD_ACCENT}55", offset=ft.Offset(0, 4)),
            content=ft.Row(
                spacing=6,
                tight=True,
                controls=[
                    ft.Icon(ft.Icons.ADD_CIRCLE, color=COLOR_ON_PRIMARY, size=18),
                    ft.Text("Add Income", size=13, weight=ft.FontWeight.W_700, color=COLOR_ON_PRIMARY),
                ],
            ),
            on_click=lambda e: self._open_quick_add_modal(e, txn_type="INCOME"),
        )

        cat_btn = ft.Container(
            bgcolor=card_bg,
            border=ft.Border.all(1, border_col),
            border_radius=20,
            padding=ft.Padding.symmetric(horizontal=14, vertical=10),
            ink=True,
            content=ft.Row(
                spacing=6,
                tight=True,
                controls=[
                    ft.Icon(ft.Icons.DASHBOARD_CUSTOMIZE, color=COLOR_PRIMARY, size=18),
                    ft.Text("Categories", size=13, weight=ft.FontWeight.W_600, color=text_col),
                    ft.Container(
                        width=16,
                        height=16,
                        border_radius=8,
                        bgcolor=f"{COLOR_PRIMARY}33",
                        alignment=ft.Alignment.CENTER,
                        content=ft.Text("+", size=10, weight=ft.FontWeight.W_800, color=COLOR_PRIMARY),
                    ),
                ],
            ),
            on_click=self._open_category_management,
        )

        analytics_btn = ft.Container(
            bgcolor=card_bg,
            border=ft.Border.all(1, border_col),
            border_radius=20,
            padding=ft.Padding.symmetric(horizontal=14, vertical=10),
            ink=True,
            content=ft.Row(
                spacing=6,
                tight=True,
                controls=[
                    ft.Icon(ft.Icons.TRENDING_UP, color=COLOR_SECONDARY, size=18),
                    ft.Text("Analytics", size=13, weight=ft.FontWeight.W_600, color=text_col),
                ],
            ),
            on_click=lambda e: self._switch_to_tab(3) if self._switch_to_tab else None,  # Analytics tab
        )

        quick_actions_row = ft.Row(
            scroll=ft.ScrollMode.HIDDEN,
            spacing=10,
            controls=[add_btn, add_income_btn, cat_btn, analytics_btn],
        )

        # Spending Breakdown Card with Donut Chart
        breakdown_card = ft.Container(
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
                            ft.Text("Spending Breakdown", size=16, weight=ft.FontWeight.W_700, color=text_col),
                            ft.Text("Monthly", size=13, weight=ft.FontWeight.W_600, color=COLOR_PRIMARY),
                        ],
                    ),
                    ft.Row(
                        spacing=12,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Container(
                                expand=6,
                                content=self._legend_column,
                            ),
                            ft.Container(
                                expand=5,
                                content=self._donut_container,
                            ),
                        ],
                    ),
                ],
            ),
        )

        # Recent Expenses Section
        recent_header = ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Text("Recent Expenses", size=17, weight=ft.FontWeight.W_700, color=text_col),
                ft.TextButton(
                    content=ft.Row(
                        spacing=2,
                        tight=True,
                        controls=[
                            ft.Text("View All", size=13, weight=ft.FontWeight.W_600, color=COLOR_TERTIARY_CONTAINER),
                            ft.Icon(ft.Icons.CHEVRON_RIGHT, size=16, color=COLOR_TERTIARY_CONTAINER),
                        ],
                    ),
                    on_click=lambda e: self._switch_to_tab(1) if self._switch_to_tab else None,  # History tab
                ),
            ],
        )

        scroll_content = ft.ListView(
            expand=True,
            spacing=16,
            padding=ft.Padding.symmetric(horizontal=16, vertical=12),
            controls=[
                hero_card,
                quick_actions_row,
                breakdown_card,
                recent_header,
                self._recent_list,
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
        """Load database records and update all dashboard widgets."""
        try:
            self._user = self._profile_service.get_current_user()
            user_id = self._user.id if self._user else 1
            user_name = self._user.name if self._user and self._user.name else ""
            profession = self._user.profession if self._user and self._user.profession else ""
            currency = self._user.currency if self._user and self._user.currency else DEFAULT_CURRENCY
            start_d, end_d = date_range_this_month()

            is_dark = theme_manager.is_dark()
            primary_col = "#C0C1FF" if is_dark else COLOR_PRIMARY
            sub_col = "#908FA0" if is_dark else COLOR_ON_SURFACE_VARIANT
            card_bg = "#151D30" if is_dark else COLOR_SURFACE_CARD
            border_col = "#222E48" if is_dark else COLOR_OUTLINE_VARIANT
            text_col = "#FFFFFF" if is_dark else COLOR_ON_SURFACE

            # Update Header User Spans
            self._greeting_subtext.spans = [
                ft.TextSpan(user_name, style=ft.TextStyle(color=primary_col, weight=ft.FontWeight.W_700, size=13)),
                ft.TextSpan(" • ", style=ft.TextStyle(color=border_col, size=12)),
                ft.TextSpan(profession, style=ft.TextStyle(color=sub_col, weight=ft.FontWeight.W_500, size=12)),
            ]
            self._greeting_subtext.value = None
            self._greeting_title.value = clock_service.get_greeting_str()
            self._greeting_title.color = text_col
            self._date_subtext.value = clock_service.format_live_display()
            self._date_subtext.color = sub_col

            # Real-time Balance is derived from user income minus expenses
            user_salary = (self._user.monthly_income_paise if (self._user and self._user.monthly_income_paise) else 0)
            summary = self._calculation_service.calculate_period_summary(user_id, start_d, end_d)
            income_extra = summary.get("total_income_paise", 0)
            expense = summary.get("total_expenses_paise", 0)

            display_salary = user_salary + income_extra
            display_expense = expense
            real_time_bal = display_salary - display_expense

            bal_str = format_currency(real_time_bal, currency)
            self._balance_text.value = bal_str
            inc_str = format_currency(display_salary, currency)
            exp_str = format_currency(display_expense, currency)
            self._deduction_text.value = f"Income: {inc_str}  •  Expenses: {exp_str}"

            # Spending Breakdown Donut Chart
            dist = self._analytics_service.get_category_spending_distribution(user_id, start_d, end_d)
            donut_palette = ["#0041DC", "#FF7A5C", "#712AE2", "#10B981", "#FF5A36"]
            sections = []
            self._legend_column.controls.clear()

            if dist and display_expense > 0:
                self._legend_column.controls.append(
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text("Label", size=11, weight=ft.FontWeight.W_700, color=COLOR_OUTLINE),
                            ft.Text("Amount", size=11, weight=ft.FontWeight.W_700, color=COLOR_OUTLINE),
                        ],
                    )
                )
                for idx, item in enumerate(dist[:5]):
                    c_name = item.get("name") or item.get("category_name") or "Expense"
                    amt = item.get("amount_paise") or item.get("total_paise") or 0
                    pct = float(item.get("percentage") or 0.0)
                    c_col = item.get("color") or donut_palette[idx % len(donut_palette)]
                    sections.append(
                        fc.PieChartSection(
                            value=pct if pct > 0 else 1.0,
                            color=c_col,
                            radius=16,
                            title="",
                        )
                    )
                    self._legend_column.controls.append(
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Row(
                                    spacing=6,
                                    tight=True,
                                    controls=[
                                        ft.Container(width=8, height=8, border_radius=4, bgcolor=c_col),
                                        ft.Text(c_name, size=12, weight=ft.FontWeight.W_500, color=text_col),
                                    ],
                                ),
                                ft.Text(format_currency(amt, currency), size=12, weight=ft.FontWeight.W_700, color=text_col),
                            ],
                        )
                    )

                self._donut_container.content = ft.Stack(
                    alignment=ft.Alignment.CENTER,
                    controls=[
                        fc.PieChart(
                            sections=sections,
                            sections_space=3,
                            center_space_radius=36,
                            height=140,
                        ),
                        ft.Column(
                            spacing=0,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            alignment=ft.MainAxisAlignment.CENTER,
                            controls=[
                                ft.Text("TOTAL", size=9, weight=ft.FontWeight.W_800, color=COLOR_OUTLINE),
                                ft.Text(
                                    format_currency(display_expense, currency),
                                    size=13,
                                    weight=ft.FontWeight.W_800,
                                    color=text_col,
                                ),
                            ],
                        ),
                    ],
                )
            else:
                self._legend_column.controls.append(
                    ft.Container(
                        padding=ft.Padding.symmetric(vertical=24),
                        content=ft.Text("No expenses yet", size=13, weight=ft.FontWeight.W_500, color=sub_col),
                    )
                )
                self._donut_container.content = ft.Container(
                    height=140,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Column(
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=6,
                        controls=[
                            ft.Icon(ft.Icons.PIE_CHART_OUTLINE, size=32, color=sub_col),
                            ft.Text("No expenses yet", size=12, weight=ft.FontWeight.W_600, color=sub_col),
                        ],
                    ),
                )

            # Recent Transactions Feed
            recent_txns = self._transaction_service.get_recent_transactions(user_id=user_id, limit=5)
            self._recent_list.controls.clear()

            if recent_txns:
                for txn in recent_txns:
                    self._recent_list.controls.append(
                        build_transaction_card(
                            txn,
                            currency=currency,
                            on_tap=self._navigate_to_edit_txn,
                        )
                    )
            else:
                self._recent_list.controls.append(
                    ft.Container(
                        bgcolor=card_bg,
                        border=ft.Border.all(1, border_col),
                        border_radius=16,
                        padding=ft.Padding.symmetric(vertical=28, horizontal=16),
                        alignment=ft.Alignment.CENTER,
                        content=ft.Column(
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=8,
                            controls=[
                                ft.Icon(ft.Icons.RECEIPT_LONG_OUTLINED, size=32, color=sub_col),
                                ft.Text("No expenses yet", size=14, weight=ft.FontWeight.W_700, color=text_col),
                                ft.Text("Your recorded transactions will appear here", size=11, color=sub_col),
                            ],
                        ),
                    )
                )

            if self._page:
                try:
                    self._page.update()
                except Exception:
                    pass

        except Exception as ex:
            logger.error("Error refreshing dashboard: %s", ex, exc_info=True)