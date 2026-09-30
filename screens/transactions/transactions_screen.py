"""
Spendora — Expenses List Screen (Flet).

Matches Google Stitch "Expenses List" screen with comprehensive filtering:
- Top Navigation Bar with Back button, "Expenses List", Search, Filter & Refine modal, Theme toggle
- Pill search input field
- Interactive filter chips row:
  * Filter & Refine (with active badge count)
  * Transaction Type (All / Expenses Only / Income Only)
  * Time Period (This Month, Last Month, This Week, Today, Last 90 Days, This Year, All Time, Custom)
  * Category Selector (All Categories or user-specific categories)
  * Amount Range (Any Amount, Under ₹500, ₹500 - ₹2k, ₹2k - ₹10k, Above ₹10k, Custom)
  * Sort Order (Newest, Oldest, Highest Amount, Lowest Amount)
  * Clear/Reset Filters (visible whenever filters are applied)
- Active filter summary strip:
  * Matching transaction count
  * Total Outflow (-₹) and Inflow (+₹) metrics
  * Individual dismissible filter tags [x]
- Filter & Refine Modal Sheet dialog for multi-attribute filtering
- Date-grouped transaction cards with category icons, colors, amounts, edit & delete actions
- Zero-results empty state with "Reset Filters" action
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Callable, Dict, List, Optional

import flet as ft

from components.transaction_card import _resolve_icon, build_transaction_card
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
    COLOR_SECONDARY_CONTAINER,
    COLOR_SURFACE_CARD,
    COLOR_SURFACE_CONTAINER,
    COLOR_SURFACE_LOW,
    COLOR_TERTIARY_CONTAINER,
    DEFAULT_CURRENCY,
)
from config.theme_manager import theme_manager
from database.models import Category, Transaction, TransactionType, User
from services.category_service import CategoryService
from services.profile_service import ProfileService
from services.transaction_service import TransactionService
from utils.date_utils import (
    date_range_last_month,
    date_range_this_month,
    date_range_this_week,
    date_range_this_year,
    date_range_today,
    today,
)
from utils.formatting import format_currency

logger = logging.getLogger(__name__)

PERIOD_LABELS: Dict[str, str] = {
    "THIS_MONTH": "This Month",
    "LAST_MONTH": "Last Month",
    "THIS_WEEK": "This Week",
    "TODAY": "Today",
    "LAST_90_DAYS": "Last 90 Days",
    "THIS_YEAR": "This Year",
    "ALL_TIME": "All Time",
    "CUSTOM": "Custom Range",
}

AMOUNT_LABELS: Dict[str, str] = {
    "ALL": "Any Amount",
    "UNDER_500": "< ₹500",
    "500_TO_2000": "₹500 - ₹2,000",
    "2000_TO_10000": "₹2,000 - ₹10,000",
    "ABOVE_10000": "> ₹10,000",
    "CUSTOM": "Custom Range",
}

SORT_LABELS: Dict[str, str] = {
    "DATE_DESC": "Newest",
    "DATE_ASC": "Oldest",
    "AMOUNT_DESC": "Highest ₹",
    "AMOUNT_ASC": "Lowest ₹",
}


class TransactionsView:
    """Expenses List view with comprehensive filters matching Stitch aesthetic."""

    def __init__(
        self,
        navigate_to_add_txn: Optional[Callable[[], None]] = None,
        navigate_to_edit_txn: Optional[Callable[[Transaction], None]] = None,
        switch_to_tab: Optional[Callable[[int], None]] = None,
    ) -> None:
        self._transaction_service = TransactionService()
        self._profile_service = ProfileService()
        self._category_service = CategoryService()
        self._user: Optional[User] = None
        self._navigate_to_add_txn = navigate_to_add_txn
        self._navigate_to_edit_txn = navigate_to_edit_txn
        self._switch_to_tab = switch_to_tab
        self._page: Optional[ft.Page] = None

        # Filter state
        self._active_chip: str = "THIS_MONTH"
        self._filter_period: str = "THIS_MONTH"
        self._custom_start_date: Optional[date] = None
        self._custom_end_date: Optional[date] = None
        self._filter_type: Optional[str] = None  # None (all), "EXPENSE", "INCOME"
        self._filter_category_id: Optional[int] = None
        self._filter_category_name: Optional[str] = None
        self._filter_amount_preset: str = "ALL"
        self._custom_min_rupees: Optional[int] = None
        self._custom_max_rupees: Optional[int] = None
        self._sort_order: str = "DATE_DESC"
        self._search_term: str = ""

        # Theme toggle icon
        self._theme_icon = ft.IconButton(
            icon=ft.Icons.LIGHT_MODE if theme_manager.is_dark() else ft.Icons.DARK_MODE,
            icon_color=COLOR_ON_SURFACE,
            icon_size=20,
            tooltip="Toggle Dark Mode",
            on_click=lambda e: theme_manager.toggle(self._page),
        )
        theme_manager.register_listener(self._on_theme_changed)

        # Search Bar
        self._search_input = ft.TextField(
            hint_text="Search expenses, stores, categories...",
            hint_style=ft.TextStyle(color=COLOR_OUTLINE, size=13),
            text_style=ft.TextStyle(color=COLOR_ON_SURFACE, size=14),
            border_color=COLOR_OUTLINE_VARIANT,
            focused_border_color=COLOR_PRIMARY,
            border_radius=24,
            bgcolor=COLOR_SURFACE_CARD,
            prefix_icon=ft.Icons.SEARCH,
            dense=True,
            on_change=self._on_search_change,
        )

        # Summary strip and tag controls
        self._summary_container = ft.Container(visible=True)
        self._active_tags_wrap = ft.Row(wrap=True, spacing=6, run_spacing=6)
        self._grouped_column = ft.Column(spacing=16)

        # Filter badge indicator
        self._filter_badge_text = ft.Text("0", size=10, weight=ft.FontWeight.W_800, color="#FFFFFF")
        self._filter_badge_container = ft.Container(
            bgcolor=COLOR_CORAL_ACCENT,
            border_radius=8,
            padding=ft.Padding.symmetric(horizontal=5, vertical=1),
            content=self._filter_badge_text,
            visible=False,
        )

        # Chips
        self._chip_filter_btn = ft.Container()
        self._chip_type = ft.Container()
        self._chip_this_month = ft.Container()
        self._chip_all_cats = ft.Container()
        self._chip_range = ft.Container()
        self._chip_sort = ft.Container()
        self._chip_reset = ft.Container()

    def set_page(self, page: ft.Page) -> None:
        self._page = page

    def _on_theme_changed(self, is_dark: bool) -> None:
        self._theme_icon.icon = ft.Icons.LIGHT_MODE if is_dark else ft.Icons.DARK_MODE
        self._theme_icon.icon_color = "#F8FAFC" if is_dark else COLOR_ON_SURFACE
        if hasattr(self, "_top_bar") and self._top_bar:
            self._top_bar.bgcolor = "#151D30" if is_dark else COLOR_SURFACE_CARD
            try:
                self._top_bar.update()
            except Exception:
                pass
        try:
            self._theme_icon.update()
        except Exception:
            pass
        self._update_chip_styles()

    def _on_search_change(self, e) -> None:
        self._search_term = (self._search_input.value or "").strip()
        self.refresh()

    def _get_active_filters_count(self) -> int:
        """Count active non-default filters."""
        count = 0
        if self._filter_type is not None:
            count += 1
        if self._filter_period != "THIS_MONTH":
            count += 1
        if self._filter_category_id is not None:
            count += 1
        if self._filter_amount_preset != "ALL":
            count += 1
        if self._sort_order != "DATE_DESC":
            count += 1
        if bool(self._search_term):
            count += 1
        return count

    def _reset_all_filters(self, e=None) -> None:
        """Reset all filter states to defaults."""
        self._active_chip = "THIS_MONTH"
        self._filter_period = "THIS_MONTH"
        self._custom_start_date = None
        self._custom_end_date = None
        self._filter_type = None
        self._filter_category_id = None
        self._filter_category_name = None
        self._filter_amount_preset = "ALL"
        self._custom_min_rupees = None
        self._custom_max_rupees = None
        self._sort_order = "DATE_DESC"
        self._search_term = ""
        self._search_input.value = ""
        try:
            self._search_input.update()
        except Exception:
            pass
        self._update_chip_styles()
        self.refresh()

    def _toggle_type_filter(self, e=None) -> None:
        """Cycle through: All -> Expenses Only -> Income Only -> All."""
        if self._filter_type is None:
            self._filter_type = "EXPENSE"
        elif self._filter_type == "EXPENSE":
            self._filter_type = "INCOME"
        else:
            self._filter_type = None
        self._update_chip_styles()
        self.refresh()

    def _cycle_period_filter(self, e=None) -> None:
        """Cycle period presets or open period modal."""
        presets = ["THIS_MONTH", "LAST_MONTH", "THIS_WEEK", "TODAY", "LAST_90_DAYS", "THIS_YEAR", "ALL_TIME"]
        try:
            curr_idx = presets.index(self._filter_period)
            self._filter_period = presets[(curr_idx + 1) % len(presets)]
        except ValueError:
            self._filter_period = "THIS_MONTH"
        self._active_chip = self._filter_period
        self._update_chip_styles()
        self.refresh()

    def _cycle_amount_filter(self, e=None) -> None:
        """Cycle amount presets: ALL -> UNDER_500 -> 500_TO_2000 -> 2000_TO_10000 -> ABOVE_10000 -> ALL."""
        presets = ["ALL", "UNDER_500", "500_TO_2000", "2000_TO_10000", "ABOVE_10000"]
        try:
            curr_idx = presets.index(self._filter_amount_preset)
            self._filter_amount_preset = presets[(curr_idx + 1) % len(presets)]
        except ValueError:
            self._filter_amount_preset = "UNDER_500"
        self._active_chip = "RANGE" if self._filter_amount_preset != "ALL" else "THIS_MONTH"
        self._update_chip_styles()
        self.refresh()

    def _cycle_sort_order(self, e=None) -> None:
        """Cycle sort order: Newest -> Oldest -> Highest -> Lowest."""
        orders = ["DATE_DESC", "DATE_ASC", "AMOUNT_DESC", "AMOUNT_ASC"]
        try:
            curr_idx = orders.index(self._sort_order)
            self._sort_order = orders[(curr_idx + 1) % len(orders)]
        except ValueError:
            self._sort_order = "DATE_DESC"
        self._update_chip_styles()
        self.refresh()

    def _set_chip_filter(self, chip: str) -> None:
        """Backwards-compatible chip filter handler."""
        self._active_chip = chip
        if chip == "ALL":
            self._filter_period = "ALL_TIME"
            self._filter_category_id = None
            self._filter_category_name = None
            self._filter_type = None
            self._filter_amount_preset = "ALL"
        elif chip == "THIS_MONTH":
            self._filter_period = "THIS_MONTH"
        elif chip == "RANGE":
            self._cycle_amount_filter()
            return

        self._update_chip_styles()
        self.refresh()

    def _update_chip_styles(self) -> None:
        """Sync chip visual styles with current filter properties."""
        is_dark = theme_manager.is_dark()
        card_bg = "#151D30" if is_dark else COLOR_SURFACE_CARD
        border_col = "#222E48" if is_dark else COLOR_OUTLINE_VARIANT
        text_col = "#FFFFFF" if is_dark else COLOR_ON_SURFACE
        sub_col = "#94A3B8" if is_dark else COLOR_OUTLINE
        primary_col = "#8B5CF6" if is_dark else COLOR_PRIMARY

        active_count = self._get_active_filters_count()

        # 1. Filter & Refine button with active count
        if hasattr(self, "_chip_filter_btn") and self._chip_filter_btn:
            is_filtered = active_count > 0
            self._chip_filter_btn.bgcolor = f"{COLOR_PRIMARY}22" if (is_filtered and is_dark) else (COLOR_PRIMARY_CONTAINER if is_filtered else card_bg)
            self._chip_filter_btn.border = ft.Border.all(1.5, primary_col) if is_filtered else ft.Border.all(1, border_col)
            if hasattr(self, "_filter_badge_container"):
                self._filter_badge_container.visible = active_count > 0
                self._filter_badge_text.value = str(active_count)

        # 2. Type Chip
        if hasattr(self, "_chip_type") and self._chip_type:
            if self._filter_type == "EXPENSE":
                self._chip_type.bgcolor = f"{COLOR_CORAL_ACCENT}22" if is_dark else "#FEE2E2"
                self._chip_type.border = ft.Border.all(1.5, COLOR_CORAL_ACCENT)
                self._chip_type.content.controls[0].name = ft.Icons.ARROW_UPWARD
                self._chip_type.content.controls[0].color = COLOR_CORAL_ACCENT
                self._chip_type.content.controls[1].value = "Expenses Only"
                self._chip_type.content.controls[1].color = COLOR_CORAL_ACCENT
            elif self._filter_type == "INCOME":
                self._chip_type.bgcolor = f"{COLOR_EMERALD_ACCENT}22" if is_dark else "#D1FAE5"
                self._chip_type.border = ft.Border.all(1.5, COLOR_EMERALD_ACCENT)
                self._chip_type.content.controls[0].name = ft.Icons.ARROW_DOWNWARD
                self._chip_type.content.controls[0].color = COLOR_EMERALD_ACCENT
                self._chip_type.content.controls[1].value = "Income Only"
                self._chip_type.content.controls[1].color = COLOR_EMERALD_ACCENT
            else:
                self._chip_type.bgcolor = card_bg
                self._chip_type.border = ft.Border.all(1, border_col)
                self._chip_type.content.controls[0].name = ft.Icons.SWAP_VERT
                self._chip_type.content.controls[0].color = sub_col
                self._chip_type.content.controls[1].value = "All Types"
                self._chip_type.content.controls[1].color = text_col

        # 3. Period Chip ("This Month")
        if hasattr(self, "_chip_this_month") and self._chip_this_month:
            is_active_tm = self._active_chip == "THIS_MONTH" or self._filter_period == "THIS_MONTH"
            is_non_default_period = self._filter_period != "THIS_MONTH"
            self._chip_this_month.content.value = PERIOD_LABELS.get(self._filter_period, "This Month")

            if is_non_default_period:
                self._chip_this_month.bgcolor = f"{primary_col}22" if is_dark else COLOR_PRIMARY_CONTAINER
                self._chip_this_month.border = ft.Border.all(1.5, primary_col)
                self._chip_this_month.content.color = "#FFFFFF" if is_dark else primary_col
                self._chip_this_month.content.weight = ft.FontWeight.W_700
            elif is_active_tm:
                self._chip_this_month.bgcolor = primary_col
                self._chip_this_month.border = None
                self._chip_this_month.content.color = COLOR_ON_PRIMARY
                self._chip_this_month.content.weight = ft.FontWeight.W_700
            else:
                self._chip_this_month.bgcolor = card_bg
                self._chip_this_month.border = ft.Border.all(1, border_col)
                self._chip_this_month.content.color = text_col
                self._chip_this_month.content.weight = ft.FontWeight.W_500

        # 4. Category Chip
        if hasattr(self, "_chip_all_cats") and self._chip_all_cats:
            is_active_all = self._active_chip == "ALL"
            has_cat = self._filter_category_id is not None
            cat_display = self._filter_category_name or "All Categories"
            self._chip_all_cats.content.controls[0].value = cat_display

            if has_cat:
                self._chip_all_cats.bgcolor = f"{COLOR_CORAL_ACCENT}22" if is_dark else "#FEE2E2"
                self._chip_all_cats.border = ft.Border.all(1.5, COLOR_CORAL_ACCENT)
                self._chip_all_cats.content.controls[0].color = COLOR_CORAL_ACCENT
                self._chip_all_cats.content.controls[0].weight = ft.FontWeight.W_700
            elif is_active_all:
                self._chip_all_cats.bgcolor = COLOR_TERTIARY_CONTAINER
                self._chip_all_cats.border = None
                self._chip_all_cats.content.controls[0].color = COLOR_ON_PRIMARY
                self._chip_all_cats.content.controls[0].weight = ft.FontWeight.W_700
            else:
                self._chip_all_cats.bgcolor = card_bg
                self._chip_all_cats.border = ft.Border.all(1, border_col)
                self._chip_all_cats.content.controls[0].color = text_col
                self._chip_all_cats.content.controls[0].weight = ft.FontWeight.W_500

        # 5. Amount Chip
        if hasattr(self, "_chip_range") and self._chip_range:
            is_active_range = self._active_chip == "RANGE" or self._filter_amount_preset != "ALL"
            amount_display = AMOUNT_LABELS.get(self._filter_amount_preset, "₹ 0 - ₹ 10,000")
            if self._filter_amount_preset == "ALL":
                amount_display = "Any Amount"
            self._chip_range.content.value = amount_display

            if is_active_range and self._filter_amount_preset != "ALL":
                self._chip_range.bgcolor = f"{COLOR_EMERALD_ACCENT}22" if is_dark else "#D1FAE5"
                self._chip_range.border = ft.Border.all(1.5, COLOR_EMERALD_ACCENT)
                self._chip_range.content.color = COLOR_EMERALD_ACCENT
                self._chip_range.content.weight = ft.FontWeight.W_700
            elif is_active_range and self._active_chip == "RANGE":
                self._chip_range.bgcolor = COLOR_TERTIARY_CONTAINER
                self._chip_range.border = None
                self._chip_range.content.color = COLOR_ON_PRIMARY
                self._chip_range.content.weight = ft.FontWeight.W_700
            else:
                self._chip_range.bgcolor = card_bg
                self._chip_range.border = ft.Border.all(1, border_col)
                self._chip_range.content.color = text_col
                self._chip_range.content.weight = ft.FontWeight.W_500

        # 6. Sort Chip
        if hasattr(self, "_chip_sort") and self._chip_sort:
            is_sorted = self._sort_order != "DATE_DESC"
            sort_lbl = SORT_LABELS.get(self._sort_order, "Newest")
            self._chip_sort.content.controls[1].value = f"⇅ {sort_lbl}"
            if is_sorted:
                self._chip_sort.bgcolor = f"{primary_col}22" if is_dark else COLOR_PRIMARY_CONTAINER
                self._chip_sort.border = ft.Border.all(1.5, primary_col)
                self._chip_sort.content.controls[1].color = "#FFFFFF" if is_dark else primary_col
                self._chip_sort.content.controls[1].weight = ft.FontWeight.W_700
            else:
                self._chip_sort.bgcolor = card_bg
                self._chip_sort.border = ft.Border.all(1, border_col)
                self._chip_sort.content.controls[1].color = text_col
                self._chip_sort.content.controls[1].weight = ft.FontWeight.W_500

        # 7. Reset Chip visibility
        if hasattr(self, "_chip_reset") and self._chip_reset:
            self._chip_reset.visible = active_count > 0

        # Push updates if mounted
        for ctrl in [
            self._chip_filter_btn,
            self._chip_type,
            self._chip_this_month,
            self._chip_all_cats,
            self._chip_range,
            self._chip_sort,
            self._chip_reset,
        ]:
            try:
                ctrl.update()
            except Exception:
                pass

    def build(self) -> ft.Control:
        is_dark = theme_manager.is_dark()
        bar_bg = "#151D30" if is_dark else COLOR_SURFACE_CARD
        card_bg = "#151D30" if is_dark else COLOR_SURFACE_CARD
        border_col = "#222E48" if is_dark else COLOR_OUTLINE_VARIANT
        text_col = "#FFFFFF" if is_dark else COLOR_ON_SURFACE
        sub_col = "#94A3B8" if is_dark else COLOR_OUTLINE
        primary_col = "#8B5CF6" if is_dark else COLOR_PRIMARY

        # Top App Bar
        top_bar = ft.Container(
            bgcolor=bar_bg,
            border=ft.Border.only(bottom=ft.BorderSide(1, border_col)),
            padding=ft.Padding.symmetric(horizontal=16, vertical=10),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.IconButton(
                        icon=ft.Icons.CHEVRON_LEFT,
                        icon_color=text_col,
                        icon_size=24,
                        tooltip="Back to Home",
                        on_click=lambda e: self._switch_to_tab(0) if self._switch_to_tab else None,
                    ),
                    ft.Text(
                        "Expenses List",
                        color=text_col,
                        size=18,
                        weight=ft.FontWeight.W_800,
                    ),
                    ft.Row(
                        spacing=2,
                        controls=[
                            ft.IconButton(
                                icon=ft.Icons.SEARCH,
                                icon_color=text_col,
                                icon_size=20,
                                tooltip="Search",
                                on_click=lambda e: self._search_input.focus(),
                            ),
                            ft.IconButton(
                                icon=ft.Icons.FILTER_ALT,
                                icon_color=COLOR_PRIMARY if self._get_active_filters_count() > 0 else text_col,
                                icon_size=20,
                                tooltip="Filter & Refine",
                                on_click=lambda e: self._open_filter_modal(),
                            ),
                            self._theme_icon,
                        ],
                    ),
                ],
            ),
        )
        self._top_bar = top_bar

        # Search field styling
        self._search_input.bgcolor = card_bg
        self._search_input.border_color = border_col
        self._search_input.text_style = ft.TextStyle(color=text_col, size=14)
        self._search_input.hint_style = ft.TextStyle(color=sub_col, size=13)

        # 1. Filter & Refine Chip (Opens Modal)
        self._chip_filter_btn = ft.Container(
            bgcolor=card_bg,
            border=ft.Border.all(1, border_col),
            border_radius=20,
            padding=ft.Padding.symmetric(horizontal=12, vertical=8),
            ink=True,
            tooltip="Open Full Filter Sheet",
            on_click=lambda e: self._open_filter_modal(),
            content=ft.Row(
                spacing=5,
                tight=True,
                controls=[
                    ft.Icon(ft.Icons.TUNE, size=15, color=primary_col),
                    ft.Text("Filters", size=12, weight=ft.FontWeight.W_700, color=text_col),
                    self._filter_badge_container,
                ],
            ),
        )

        # 2. Transaction Type Chip (Cycles: All / Expenses / Income)
        self._chip_type = ft.Container(
            bgcolor=card_bg,
            border=ft.Border.all(1, border_col),
            border_radius=20,
            padding=ft.Padding.symmetric(horizontal=12, vertical=8),
            ink=True,
            tooltip="Filter Type (All / Expense / Income)",
            on_click=self._toggle_type_filter,
            content=ft.Row(
                spacing=4,
                tight=True,
                controls=[
                    ft.Icon(ft.Icons.SWAP_VERT, size=15, color=sub_col),
                    ft.Text("All Types", size=12, weight=ft.FontWeight.W_500, color=text_col),
                ],
            ),
        )

        # 3. Period Chip (Keeps exact structure for test compatibility)
        self._chip_this_month = ft.Container(
            bgcolor=primary_col,
            border_radius=20,
            padding=ft.Padding.symmetric(horizontal=14, vertical=8),
            ink=True,
            tooltip="Pick Period Range",
            content=ft.Text("This Month", size=12, weight=ft.FontWeight.W_700, color="#FFFFFF"),
            on_click=lambda e: self._open_period_picker_modal(),
        )

        # 4. Category Chip (Keeps exact structure for test compatibility)
        self._chip_all_cats = ft.Container(
            bgcolor=card_bg,
            border=ft.Border.all(1, border_col),
            border_radius=20,
            padding=ft.Padding.symmetric(horizontal=12, vertical=8),
            ink=True,
            tooltip="Select Category",
            content=ft.Row(
                spacing=4,
                tight=True,
                controls=[
                    ft.Text("All Categories", size=12, weight=ft.FontWeight.W_500, color=text_col),
                    ft.Icon(ft.Icons.KEYBOARD_ARROW_DOWN, size=16, color=sub_col),
                ],
            ),
            on_click=lambda e: self._open_category_picker_modal(),
        )

        # 5. Amount Chip (Keeps exact structure for test compatibility)
        self._chip_range = ft.Container(
            bgcolor=card_bg,
            border=ft.Border.all(1, border_col),
            border_radius=20,
            padding=ft.Padding.symmetric(horizontal=12, vertical=8),
            ink=True,
            tooltip="Filter Amount",
            content=ft.Text("Any Amount", size=12, weight=ft.FontWeight.W_500, color=text_col),
            on_click=lambda e: self._open_amount_picker_modal(),
        )

        # 6. Sort Order Chip
        self._chip_sort = ft.Container(
            bgcolor=card_bg,
            border=ft.Border.all(1, border_col),
            border_radius=20,
            padding=ft.Padding.symmetric(horizontal=12, vertical=8),
            ink=True,
            tooltip="Sort Order",
            content=ft.Row(
                spacing=4,
                tight=True,
                controls=[
                    ft.Icon(ft.Icons.SORT, size=14, color=sub_col),
                    ft.Text("⇅ Newest", size=12, weight=ft.FontWeight.W_500, color=text_col),
                ],
            ),
            on_click=self._cycle_sort_order,
        )

        # 7. Reset Filters Chip (Visible when filters applied)
        self._chip_reset = ft.Container(
            bgcolor=f"{COLOR_CORAL_ACCENT}1A",
            border=ft.Border.all(1, COLOR_CORAL_ACCENT),
            border_radius=20,
            padding=ft.Padding.symmetric(horizontal=12, vertical=8),
            ink=True,
            visible=False,
            tooltip="Reset All Filters",
            on_click=self._reset_all_filters,
            content=ft.Row(
                spacing=4,
                tight=True,
                controls=[
                    ft.Icon(ft.Icons.CLOSE, size=14, color=COLOR_CORAL_ACCENT),
                    ft.Text("Reset", size=12, weight=ft.FontWeight.W_700, color=COLOR_CORAL_ACCENT),
                ],
            ),
        )

        filters_row = ft.Row(
            scroll=ft.ScrollMode.HIDDEN,
            spacing=8,
            controls=[
                self._chip_filter_btn,
                self._chip_type,
                self._chip_this_month,
                self._chip_all_cats,
                self._chip_range,
                self._chip_sort,
                self._chip_reset,
            ],
        )

        scroll_content = ft.ListView(
            expand=True,
            spacing=12,
            padding=ft.Padding.symmetric(horizontal=16, vertical=12),
            controls=[
                self._search_input,
                filters_row,
                self._summary_container,
                self._grouped_column,
                ft.Container(height=80),
            ],
        )

        add_fab = ft.Container(
            right=16,
            bottom=24,
            width=52,
            height=52,
            border_radius=26,
            gradient=ft.LinearGradient(
                colors=[COLOR_EMERALD_ACCENT, "#059669"],
            ),
            alignment=ft.Alignment.CENTER,
            shadow=ft.BoxShadow(spread_radius=1, blur_radius=14, color=f"{COLOR_EMERALD_ACCENT}66", offset=ft.Offset(0, 4)),
            ink=True,
            tooltip="Add Income",
            on_click=self._open_add_income,
            content=ft.Icon(ft.Icons.ADD, color=COLOR_ON_PRIMARY, size=24),
        )

        return ft.Stack(
            expand=True,
            controls=[
                ft.Column(
                    expand=True,
                    spacing=0,
                    controls=[
                        top_bar,
                        scroll_content,
                    ],
                ),
                add_fab,
            ],
        )

    def _open_add_income(self, e=None) -> None:
        """Connect directly to Add Income page."""
        if self._navigate_to_add_txn:
            self._navigate_to_add_txn("INCOME")

    # -------------------------------------------------------------------------
    # Dialogs & Pickers
    # -------------------------------------------------------------------------

    def _open_filter_modal(self) -> None:
        """Open comprehensive Filter & Refine modal dialog."""
        if not self._page:
            return

        is_dark = theme_manager.is_dark()
        card_bg = "#151D30" if is_dark else COLOR_SURFACE_CARD
        text_col = "#FFFFFF" if is_dark else COLOR_ON_SURFACE
        sub_col = "#94A3B8" if is_dark else COLOR_OUTLINE
        primary_col = "#8B5CF6" if is_dark else COLOR_PRIMARY
        border_col = "#222E48" if is_dark else COLOR_OUTLINE_VARIANT

        temp_type = self._filter_type
        temp_period = self._filter_period
        temp_cat_id = self._filter_category_id
        temp_cat_name = self._filter_category_name
        temp_amount = self._filter_amount_preset
        temp_sort = self._sort_order

        # Fetch active user categories
        user_id = self._user.id if self._user else 1
        categories = self._category_service.list_categories(user_id)

        # Inputs for custom dates & amounts
        start_date_field = ft.TextField(
            label="Start Date (YYYY-MM-DD)",
            value=self._custom_start_date.isoformat() if self._custom_start_date else "",
            dense=True,
            text_size=12,
            border_radius=12,
            border_color=border_col,
        )
        end_date_field = ft.TextField(
            label="End Date (YYYY-MM-DD)",
            value=self._custom_end_date.isoformat() if self._custom_end_date else "",
            dense=True,
            text_size=12,
            border_radius=12,
            border_color=border_col,
        )
        min_amt_field = ft.TextField(
            label="Min ₹",
            value=str(self._custom_min_rupees) if self._custom_min_rupees else "",
            dense=True,
            text_size=12,
            border_radius=12,
            border_color=border_col,
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        max_amt_field = ft.TextField(
            label="Max ₹",
            value=str(self._custom_max_rupees) if self._custom_max_rupees else "",
            dense=True,
            text_size=12,
            border_radius=12,
            border_color=border_col,
            keyboard_type=ft.KeyboardType.NUMBER,
        )

        def _close_modal(e=None):
            dialog.open = False
            try:
                self._page.update()
            except Exception:
                pass

        def _apply_filters(e=None):
            nonlocal temp_type, temp_period, temp_cat_id, temp_cat_name, temp_amount, temp_sort
            self._filter_type = temp_type
            self._filter_period = temp_period
            self._filter_category_id = temp_cat_id
            self._filter_category_name = temp_cat_name
            self._filter_amount_preset = temp_amount
            self._sort_order = temp_sort

            # Parse custom dates if entered
            if temp_period == "CUSTOM":
                try:
                    if start_date_field.value:
                        self._custom_start_date = datetime.strptime(start_date_field.value.strip(), "%Y-%m-%d").date()
                    if end_date_field.value:
                        self._custom_end_date = datetime.strptime(end_date_field.value.strip(), "%Y-%m-%d").date()
                except Exception:
                    pass

            # Parse custom amounts if entered
            if temp_amount == "CUSTOM":
                try:
                    if min_amt_field.value:
                        self._custom_min_rupees = int(min_amt_field.value.strip())
                    if max_amt_field.value:
                        self._custom_max_rupees = int(max_amt_field.value.strip())
                except Exception:
                    pass

            _close_modal()
            self._update_chip_styles()
            self.refresh()

        def _reset_modal(e=None):
            nonlocal temp_type, temp_period, temp_cat_id, temp_cat_name, temp_amount, temp_sort
            temp_type = None
            temp_period = "THIS_MONTH"
            temp_cat_id = None
            temp_cat_name = None
            temp_amount = "ALL"
            temp_sort = "DATE_DESC"
            start_date_field.value = ""
            end_date_field.value = ""
            min_amt_field.value = ""
            max_amt_field.value = ""
            _rebuild_content()
            try:
                self._page.update()
            except Exception:
                pass

        content_col = ft.Column(spacing=16, scroll=ft.ScrollMode.ADAPTIVE)

        def _rebuild_content():
            content_col.controls.clear()

            # Section 1: Transaction Type
            type_chips = []
            for t_val, t_lbl, t_icon, t_col in [
                (None, "All Types", ft.Icons.SWAP_VERT, primary_col),
                ("EXPENSE", "Expenses (-₹)", ft.Icons.ARROW_UPWARD, COLOR_CORAL_ACCENT),
                ("INCOME", "Income (+₹)", ft.Icons.ARROW_DOWNWARD, COLOR_EMERALD_ACCENT),
            ]:
                is_sel = temp_type == t_val
                type_chips.append(
                    ft.Container(
                        bgcolor=f"{t_col}22" if is_sel else card_bg,
                        border=ft.Border.all(1.5, t_col) if is_sel else ft.Border.all(1, border_col),
                        border_radius=16,
                        padding=ft.Padding.symmetric(horizontal=10, vertical=7),
                        ink=True,
                        on_click=lambda e, val=t_val: _select_type(val),
                        content=ft.Row(
                            spacing=4,
                            tight=True,
                            controls=[
                                ft.Icon(t_icon, size=14, color=t_col if is_sel else sub_col),
                                ft.Text(t_lbl, size=11, weight=ft.FontWeight.W_700 if is_sel else ft.FontWeight.W_500, color=t_col if is_sel else text_col),
                            ],
                        ),
                    )
                )

            # Section 2: Period Range
            period_chips = []
            for p_code, p_name in PERIOD_LABELS.items():
                is_sel = temp_period == p_code
                period_chips.append(
                    ft.Container(
                        bgcolor=f"{primary_col}22" if is_sel else card_bg,
                        border=ft.Border.all(1.5, primary_col) if is_sel else ft.Border.all(1, border_col),
                        border_radius=16,
                        padding=ft.Padding.symmetric(horizontal=10, vertical=6),
                        ink=True,
                        on_click=lambda e, code=p_code: _select_period(code),
                        content=ft.Text(p_name, size=11, weight=ft.FontWeight.W_700 if is_sel else ft.FontWeight.W_500, color="#FFFFFF" if (is_sel and is_dark) else (primary_col if is_sel else text_col)),
                    )
                )

            # Section 3: Categories
            cat_chips = []
            # "All Categories" option
            is_all_cat = temp_cat_id is None
            cat_chips.append(
                ft.Container(
                    bgcolor=f"{primary_col}22" if is_all_cat else card_bg,
                    border=ft.Border.all(1.5, primary_col) if is_all_cat else ft.Border.all(1, border_col),
                    border_radius=16,
                    padding=ft.Padding.symmetric(horizontal=10, vertical=6),
                    ink=True,
                    on_click=lambda e: _select_cat(None, None),
                    content=ft.Text("All Categories", size=11, weight=ft.FontWeight.W_700 if is_all_cat else ft.FontWeight.W_500, color=primary_col if is_all_cat else text_col),
                )
            )
            for cat in categories:
                is_sel = temp_cat_id == cat.id
                c_icon = _resolve_icon(cat.icon or "")
                c_col = cat.color or primary_col
                cat_chips.append(
                    ft.Container(
                        bgcolor=f"{c_col}22" if is_sel else card_bg,
                        border=ft.Border.all(1.5, c_col) if is_sel else ft.Border.all(1, border_col),
                        border_radius=16,
                        padding=ft.Padding.symmetric(horizontal=10, vertical=6),
                        ink=True,
                        on_click=lambda e, cid=cat.id, cname=cat.name: _select_cat(cid, cname),
                        content=ft.Row(
                            spacing=4,
                            tight=True,
                            controls=[
                                ft.Icon(c_icon, size=13, color=c_col),
                                ft.Text(cat.name, size=11, weight=ft.FontWeight.W_700 if is_sel else ft.FontWeight.W_500, color=c_col if is_sel else text_col),
                            ],
                        ),
                    )
                )

            # Section 4: Amount Presets
            amount_chips = []
            for a_code, a_name in AMOUNT_LABELS.items():
                is_sel = temp_amount == a_code
                amount_chips.append(
                    ft.Container(
                        bgcolor=f"{COLOR_EMERALD_ACCENT}22" if is_sel else card_bg,
                        border=ft.Border.all(1.5, COLOR_EMERALD_ACCENT) if is_sel else ft.Border.all(1, border_col),
                        border_radius=16,
                        padding=ft.Padding.symmetric(horizontal=10, vertical=6),
                        ink=True,
                        on_click=lambda e, code=a_code: _select_amount(code),
                        content=ft.Text(a_name, size=11, weight=ft.FontWeight.W_700 if is_sel else ft.FontWeight.W_500, color=COLOR_EMERALD_ACCENT if is_sel else text_col),
                    )
                )

            # Section 5: Sort Order
            sort_chips = []
            for s_code, s_name in SORT_LABELS.items():
                is_sel = temp_sort == s_code
                sort_chips.append(
                    ft.Container(
                        bgcolor=f"{primary_col}22" if is_sel else card_bg,
                        border=ft.Border.all(1.5, primary_col) if is_sel else ft.Border.all(1, border_col),
                        border_radius=16,
                        padding=ft.Padding.symmetric(horizontal=10, vertical=6),
                        ink=True,
                        on_click=lambda e, code=s_code: _select_sort(code),
                        content=ft.Text(s_name, size=11, weight=ft.FontWeight.W_700 if is_sel else ft.FontWeight.W_500, color=primary_col if is_sel else text_col),
                    )
                )

            # Append assembled sections
            content_col.controls.extend([
                # 1. Type
                ft.Column(
                    spacing=6,
                    controls=[
                        ft.Text("Transaction Type", size=13, weight=ft.FontWeight.W_700, color=text_col),
                        ft.Row(wrap=True, spacing=8, controls=type_chips),
                    ],
                ),
                # 2. Period
                ft.Column(
                    spacing=6,
                    controls=[
                        ft.Text("Time Period", size=13, weight=ft.FontWeight.W_700, color=text_col),
                        ft.Row(wrap=True, spacing=6, run_spacing=6, controls=period_chips),
                        ft.Row(spacing=8, controls=[start_date_field, end_date_field], visible=(temp_period == "CUSTOM")),
                    ],
                ),
                # 3. Category
                ft.Column(
                    spacing=6,
                    controls=[
                        ft.Text("Category", size=13, weight=ft.FontWeight.W_700, color=text_col),
                        ft.Row(wrap=True, spacing=6, run_spacing=6, controls=cat_chips),
                    ],
                ),
                # 4. Amount Range
                ft.Column(
                    spacing=6,
                    controls=[
                        ft.Text("Amount Range", size=13, weight=ft.FontWeight.W_700, color=text_col),
                        ft.Row(wrap=True, spacing=6, run_spacing=6, controls=amount_chips),
                        ft.Row(spacing=8, controls=[min_amt_field, max_amt_field], visible=(temp_amount == "CUSTOM")),
                    ],
                ),
                # 5. Sort
                ft.Column(
                    spacing=6,
                    controls=[
                        ft.Text("Sort By", size=13, weight=ft.FontWeight.W_700, color=text_col),
                        ft.Row(wrap=True, spacing=6, controls=sort_chips),
                    ],
                ),
            ])

        def _select_type(val):
            nonlocal temp_type
            temp_type = val
            _rebuild_content()
            try:
                self._page.update()
            except Exception:
                pass

        def _select_period(code):
            nonlocal temp_period
            temp_period = code
            _rebuild_content()
            try:
                self._page.update()
            except Exception:
                pass

        def _select_cat(cid, cname):
            nonlocal temp_cat_id, temp_cat_name
            temp_cat_id = cid
            temp_cat_name = cname
            _rebuild_content()
            try:
                self._page.update()
            except Exception:
                pass

        def _select_amount(code):
            nonlocal temp_amount
            temp_amount = code
            _rebuild_content()
            try:
                self._page.update()
            except Exception:
                pass

        def _select_sort(code):
            nonlocal temp_sort
            temp_sort = code
            _rebuild_content()
            try:
                self._page.update()
            except Exception:
                pass

        _rebuild_content()

        dialog = ft.AlertDialog(
            bgcolor=card_bg,
            shape=ft.RoundedRectangleBorder(radius=20),
            title=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Row(
                        spacing=8,
                        controls=[
                            ft.Icon(ft.Icons.TUNE, color=primary_col, size=20),
                            ft.Text("Filter & Refine", size=17, weight=ft.FontWeight.W_800, color=text_col),
                        ],
                    ),
                    ft.IconButton(ft.Icons.CLOSE, icon_color=text_col, icon_size=18, on_click=_close_modal),
                ],
            ),
            content=ft.Container(
                width=380,
                height=450,
                content=content_col,
            ),
            actions=[
                ft.TextButton("Reset All", on_click=_reset_modal),
                ft.ElevatedButton(
                    "Apply Filters",
                    bgcolor=primary_col,
                    color=COLOR_ON_PRIMARY,
                    on_click=_apply_filters,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

        self._page.overlay.append(dialog)
        dialog.open = True
        try:
            self._page.update()
        except Exception:
            pass

    def _open_category_picker_modal(self) -> None:
        """Quick Category picker modal sheet."""
        if not self._page:
            return

        is_dark = theme_manager.is_dark()
        card_bg = "#151D30" if is_dark else COLOR_SURFACE_CARD
        text_col = "#FFFFFF" if is_dark else COLOR_ON_SURFACE
        primary_col = "#8B5CF6" if is_dark else COLOR_PRIMARY

        user_id = self._user.id if self._user else 1
        categories = self._category_service.list_categories(user_id)

        def _select_and_close(cat_id: Optional[int], cat_name: Optional[str]):
            self._filter_category_id = cat_id
            self._filter_category_name = cat_name
            self._active_chip = "ALL" if cat_id is None else "CAT"
            dialog.open = False
            try:
                self._page.update()
            except Exception:
                pass
            self._update_chip_styles()
            self.refresh()

        items = [
            ft.ListTile(
                leading=ft.Icon(ft.Icons.APPS, color=primary_col),
                title=ft.Text("All Categories", weight=ft.FontWeight.W_700, color=text_col),
                subtitle=ft.Text("View transactions from every category", size=11, color="#94A3B8"),
                on_click=lambda e: _select_and_close(None, None),
            )
        ]

        for cat in categories:
            c_icon = _resolve_icon(cat.icon or "")
            c_col = cat.color or primary_col
            items.append(
                ft.ListTile(
                    leading=ft.Container(
                        width=36,
                        height=36,
                        border_radius=12,
                        bgcolor=f"{c_col}22",
                        alignment=ft.Alignment.CENTER,
                        content=ft.Icon(c_icon, color=c_col, size=18),
                    ),
                    title=ft.Text(cat.name, weight=ft.FontWeight.W_600, color=text_col),
                    trailing=ft.Icon(ft.Icons.CHECK, color=primary_col, size=18) if self._filter_category_id == cat.id else None,
                    on_click=lambda e, cid=cat.id, cname=cat.name: _select_and_close(cid, cname),
                )
            )

        dialog = ft.AlertDialog(
            bgcolor=card_bg,
            shape=ft.RoundedRectangleBorder(radius=20),
            title=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Text("Filter by Category", size=16, weight=ft.FontWeight.W_800, color=text_col),
                    ft.IconButton(ft.Icons.CLOSE, icon_color=text_col, icon_size=18, on_click=lambda e: _select_and_close(self._filter_category_id, self._filter_category_name)),
                ],
            ),
            content=ft.Container(
                width=340,
                height=380,
                content=ft.ListView(controls=items, spacing=4),
            ),
        )

        self._page.overlay.append(dialog)
        dialog.open = True
        try:
            self._page.update()
        except Exception:
            pass

    def _open_period_picker_modal(self) -> None:
        """Quick Period picker modal sheet."""
        if not self._page:
            return

        is_dark = theme_manager.is_dark()
        card_bg = "#151D30" if is_dark else COLOR_SURFACE_CARD
        text_col = "#FFFFFF" if is_dark else COLOR_ON_SURFACE
        primary_col = "#8B5CF6" if is_dark else COLOR_PRIMARY

        def _select_period_and_close(code: str):
            self._filter_period = code
            self._active_chip = code
            dialog.open = False
            try:
                self._page.update()
            except Exception:
                pass
            self._update_chip_styles()
            self.refresh()

        items = []
        for p_code, p_name in PERIOD_LABELS.items():
            if p_code == "CUSTOM":
                continue
            is_active = self._filter_period == p_code
            items.append(
                ft.ListTile(
                    leading=ft.Icon(ft.Icons.CALENDAR_TODAY, color=primary_col if is_active else "#94A3B8", size=18),
                    title=ft.Text(p_name, weight=ft.FontWeight.W_700 if is_active else ft.FontWeight.W_500, color=primary_col if is_active else text_col),
                    trailing=ft.Icon(ft.Icons.CHECK, color=primary_col, size=18) if is_active else None,
                    on_click=lambda e, code=p_code: _select_period_and_close(code),
                )
            )

        dialog = ft.AlertDialog(
            bgcolor=card_bg,
            shape=ft.RoundedRectangleBorder(radius=20),
            title=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Text("Select Time Period", size=16, weight=ft.FontWeight.W_800, color=text_col),
                    ft.IconButton(ft.Icons.CLOSE, icon_color=text_col, icon_size=18, on_click=lambda e: _select_period_and_close(self._filter_period)),
                ],
            ),
            content=ft.Container(
                width=320,
                height=350,
                content=ft.ListView(controls=items, spacing=2),
            ),
        )

        self._page.overlay.append(dialog)
        dialog.open = True
        try:
            self._page.update()
        except Exception:
            pass

    def _open_amount_picker_modal(self) -> None:
        """Quick Amount Range picker modal."""
        if not self._page:
            self._cycle_amount_filter()
            return

        is_dark = theme_manager.is_dark()
        card_bg = "#151D30" if is_dark else COLOR_SURFACE_CARD
        text_col = "#FFFFFF" if is_dark else COLOR_ON_SURFACE
        primary_col = "#8B5CF6" if is_dark else COLOR_PRIMARY

        def _select_amount_and_close(code: str):
            self._filter_amount_preset = code
            self._active_chip = "RANGE" if code != "ALL" else "THIS_MONTH"
            dialog.open = False
            try:
                self._page.update()
            except Exception:
                pass
            self._update_chip_styles()
            self.refresh()

        items = []
        for a_code, a_name in AMOUNT_LABELS.items():
            if a_code == "CUSTOM":
                continue
            is_active = self._filter_amount_preset == a_code
            items.append(
                ft.ListTile(
                    leading=ft.Icon(ft.Icons.PAYMENTS_OUTLINED, color=COLOR_EMERALD_ACCENT if is_active else "#94A3B8", size=18),
                    title=ft.Text(a_name, weight=ft.FontWeight.W_700 if is_active else ft.FontWeight.W_500, color=COLOR_EMERALD_ACCENT if is_active else text_col),
                    trailing=ft.Icon(ft.Icons.CHECK, color=COLOR_EMERALD_ACCENT, size=18) if is_active else None,
                    on_click=lambda e, code=a_code: _select_amount_and_close(code),
                )
            )

        dialog = ft.AlertDialog(
            bgcolor=card_bg,
            shape=ft.RoundedRectangleBorder(radius=20),
            title=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Text("Filter by Amount", size=16, weight=ft.FontWeight.W_800, color=text_col),
                    ft.IconButton(ft.Icons.CLOSE, icon_color=text_col, icon_size=18, on_click=lambda e: _select_amount_and_close(self._filter_amount_preset)),
                ],
            ),
            content=ft.Container(
                width=320,
                height=320,
                content=ft.ListView(controls=items, spacing=2),
            ),
        )

        self._page.overlay.append(dialog)
        dialog.open = True
        try:
            self._page.update()
        except Exception:
            pass

    def _delete_transaction_with_confirm(self, txn: Transaction) -> None:
        """Confirm and delete a transaction."""
        if not txn:
            return

        def _confirm_delete(e):
            try:
                user = self._profile_service.get_current_user()
                user_id = user.id if user else 1
                self._transaction_service.delete_transaction(txn.id, user_id=user_id)
                if hasattr(dialog, "open"):
                    dialog.open = False
                if self._page:
                    try:
                        self._page.update()
                    except Exception:
                        pass
                self.refresh()
            except Exception as ex:
                logger.error("Failed to delete transaction: %s", ex)

        def _cancel_delete(e):
            dialog.open = False
            if self._page:
                try:
                    self._page.update()
                except Exception:
                    pass

        dialog = ft.AlertDialog(
            title=ft.Text("Delete Transaction", weight=ft.FontWeight.W_700),
            content=ft.Text(f"Are you sure you want to delete '{txn.description or 'Expense'}'?"),
            actions=[
                ft.TextButton("Cancel", on_click=_cancel_delete),
                ft.ElevatedButton("Delete", bgcolor=COLOR_ERROR, color=COLOR_ON_PRIMARY, on_click=_confirm_delete),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        if self._page:
            self._page.overlay.append(dialog)
            dialog.open = True
            try:
                self._page.update()
            except Exception:
                pass
        else:
            _confirm_delete(None)

    def _build_item(
        self,
        title: str,
        dt_str: str,
        amount_paise: int,
        icon: str,
        icon_color: str,
        currency: str,
        txn: Optional[Transaction] = None,
        category_name: str = "",
        is_income: bool = False,
    ) -> ft.Container:
        """Build individual transaction card item."""
        is_dark = theme_manager.is_dark()
        text_color = "#FFFFFF" if is_dark else COLOR_ON_SURFACE
        sub_color = "#94A3B8" if is_dark else COLOR_OUTLINE
        sign = "+" if is_income else "-"
        amt_color = COLOR_EMERALD_ACCENT if is_income else text_color

        return ft.Container(
            padding=ft.Padding.symmetric(vertical=6, horizontal=4),
            border_radius=12,
            ink=True,
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Container(
                        expand=True,
                        on_click=lambda e: self._navigate_to_edit_txn(txn) if (txn and self._navigate_to_edit_txn) else None,
                        content=ft.Row(
                            spacing=12,
                            controls=[
                                ft.Container(
                                    width=40,
                                    height=40,
                                    border_radius=14,
                                    bgcolor=f"{icon_color}22",
                                    alignment=ft.Alignment.CENTER,
                                    content=ft.Icon(icon, color=icon_color, size=20),
                                ),
                                ft.Column(
                                    spacing=2,
                                    controls=[
                                        ft.Text(title, size=14, weight=ft.FontWeight.W_600, color=text_color),
                                        ft.Text(dt_str, size=11, color=sub_color),
                                    ],
                                ),
                            ],
                        ),
                    ),
                    ft.Row(
                        spacing=6,
                        tight=True,
                        controls=[
                            ft.Column(
                                spacing=2,
                                horizontal_alignment=ft.CrossAxisAlignment.END,
                                controls=[
                                    ft.Text(
                                        f"{sign}{format_currency(amount_paise, currency)}",
                                        size=14,
                                        weight=ft.FontWeight.W_800,
                                        color=amt_color,
                                    ),
                                    ft.Text(
                                        category_name.upper(),
                                        size=9,
                                        weight=ft.FontWeight.W_700,
                                        color=icon_color,
                                    ) if category_name else ft.Container(),
                                ],
                            ),
                            ft.IconButton(
                                icon=ft.Icons.DELETE_OUTLINE,
                                icon_color="#EF4444" if is_dark else COLOR_ERROR,
                                icon_size=18,
                                tooltip="Delete Entry",
                                on_click=lambda e, t=txn: self._delete_transaction_with_confirm(t),
                            ) if txn else ft.Container(),
                        ],
                    ),
                ],
            ),
        )

    def _build_section_card(self, header_title: str, items: list[ft.Control]) -> ft.Container:
        """Build grouped section card."""
        is_dark = theme_manager.is_dark()
        card_bg = "#151D30" if is_dark else COLOR_SURFACE_CARD
        card_border = "#222E48" if is_dark else COLOR_OUTLINE_VARIANT
        title_color = "#FFFFFF" if is_dark else COLOR_ON_SURFACE
        div_color = "#1E283E" if is_dark else COLOR_SURFACE_CONTAINER

        dividers_and_items = []
        for i, item in enumerate(items):
            dividers_and_items.append(item)
            if i < len(items) - 1:
                dividers_and_items.append(ft.Divider(color=div_color, height=1))

        return ft.Column(
            spacing=8,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Text(header_title, size=15, weight=ft.FontWeight.W_800, color=title_color),
                        ft.TextButton(
                            content=ft.Row(
                                spacing=2,
                                tight=True,
                                controls=[
                                    ft.Text("View All", size=12, weight=ft.FontWeight.W_600, color=COLOR_TERTIARY_CONTAINER),
                                    ft.Icon(ft.Icons.CHEVRON_RIGHT, size=14, color=COLOR_TERTIARY_CONTAINER),
                                ],
                            ),
                        ),
                    ],
                ),
                ft.Container(
                    bgcolor=card_bg,
                    border=ft.Border.all(1, card_border),
                    border_radius=20,
                    padding=ft.Padding.all(12),
                    shadow=ft.BoxShadow(spread_radius=1, blur_radius=14, color="#00000028" if is_dark else "#0D132208", offset=ft.Offset(0, 3)),
                    content=ft.Column(spacing=4, controls=dividers_and_items),
                ),
            ],
        )

    def _render_dismissible_tag(self, label: str, on_remove: Callable[[], None]) -> ft.Container:
        """Build a small active filter pill with [x] remove button."""
        is_dark = theme_manager.is_dark()
        tag_bg = "#1E293B" if is_dark else "#F1F5F9"
        border_col = "#334155" if is_dark else "#CBD5E1"
        text_col = "#E2E8F0" if is_dark else "#334155"

        return ft.Container(
            bgcolor=tag_bg,
            border=ft.Border.all(1, border_col),
            border_radius=12,
            padding=ft.Padding.only(left=8, right=4, top=3, bottom=3),
            content=ft.Row(
                spacing=4,
                tight=True,
                controls=[
                    ft.Text(label, size=11, weight=ft.FontWeight.W_600, color=text_col),
                    ft.IconButton(
                        icon=ft.Icons.CLOSE,
                        icon_size=12,
                        icon_color="#94A3B8",
                        on_click=lambda e: on_remove(),
                    ),
                ],
            ),
        )

    def refresh(self) -> None:
        """Fetch transactions from DB applying multi-criteria filters."""
        try:
            self._user = self._profile_service.get_current_user()
            user_id = self._user.id if self._user else 1
            currency = self._user.currency if self._user and self._user.currency else DEFAULT_CURRENCY
            is_dark = theme_manager.is_dark()
            card_bg = "#151D30" if is_dark else COLOR_SURFACE_CARD
            border_col = "#222E48" if is_dark else COLOR_OUTLINE_VARIANT
            text_col = "#FFFFFF" if is_dark else COLOR_ON_SURFACE
            sub_col = "#94A3B8" if is_dark else COLOR_OUTLINE
            primary_col = "#8B5CF6" if is_dark else COLOR_PRIMARY

            # 1. Resolve date range
            start_date: Optional[date] = None
            end_date: Optional[date] = None
            if self._filter_period == "THIS_MONTH":
                start_date, end_date = date_range_this_month()
            elif self._filter_period == "LAST_MONTH":
                start_date, end_date = date_range_last_month()
            elif self._filter_period == "THIS_WEEK":
                start_date, end_date = date_range_this_week()
            elif self._filter_period == "TODAY":
                start_date, end_date = date_range_today()
            elif self._filter_period == "LAST_90_DAYS":
                start_date, end_date = today() - timedelta(days=90), today()
            elif self._filter_period == "THIS_YEAR":
                start_date, end_date = date_range_this_year()
            elif self._filter_period == "CUSTOM":
                start_date, end_date = self._custom_start_date, self._custom_end_date
            elif self._filter_period == "ALL_TIME":
                start_date, end_date = None, None

            # 2. Query transactions from repository
            raw_txns = self._transaction_service.list_transactions(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date,
                transaction_type=self._filter_type,
                category_id=self._filter_category_id,
                search_term=self._search_term or None,
                limit=500,
            )

            # 3. Post-filter by amount
            filtered_txns = []
            for t in raw_txns:
                # Amount preset check
                amt = t.amount_paise
                if self._filter_amount_preset == "UNDER_500" and amt >= 50000:
                    continue
                elif self._filter_amount_preset == "500_TO_2000" and (amt < 50000 or amt > 200000):
                    continue
                elif self._filter_amount_preset == "2000_TO_10000" and (amt < 200000 or amt > 1000000):
                    continue
                elif self._filter_amount_preset == "ABOVE_10000" and amt <= 1000000:
                    continue
                elif self._filter_amount_preset == "CUSTOM":
                    if self._custom_min_rupees and amt < self._custom_min_rupees * 100:
                        continue
                    if self._custom_max_rupees and amt > self._custom_max_rupees * 100:
                        continue

                filtered_txns.append(t)

            # 4. Sort transactions
            if self._sort_order == "DATE_ASC":
                filtered_txns.sort(key=lambda x: (x.transaction_date, x.id or 0))
            elif self._sort_order == "AMOUNT_DESC":
                filtered_txns.sort(key=lambda x: (x.amount_paise, x.transaction_date), reverse=True)
            elif self._sort_order == "AMOUNT_ASC":
                filtered_txns.sort(key=lambda x: (x.amount_paise, x.transaction_date))
            else:  # DATE_DESC (default)
                filtered_txns.sort(key=lambda x: (x.transaction_date, x.id or 0), reverse=True)

            # 5. Build Live Metrics & Active Filter Tags Strip
            total_outflow = sum(t.amount_paise for t in filtered_txns if t.transaction_type == TransactionType.EXPENSE)
            total_inflow = sum(t.amount_paise for t in filtered_txns if t.transaction_type == TransactionType.INCOME)
            total_count = len(filtered_txns)

            tags = []
            if self._filter_type:
                type_lbl = "Expenses Only" if self._filter_type == "EXPENSE" else "Income Only"
                tags.append(self._render_dismissible_tag(type_lbl, lambda: self._toggle_type_filter()))
            if self._filter_period != "THIS_MONTH":
                tags.append(self._render_dismissible_tag(f"Period: {PERIOD_LABELS.get(self._filter_period, self._filter_period)}", lambda: self._set_chip_filter("THIS_MONTH")))
            if self._filter_category_id is not None:
                tags.append(self._render_dismissible_tag(f"Category: {self._filter_category_name or 'Custom'}", lambda: self._remove_category_filter()))
            if self._filter_amount_preset != "ALL":
                tags.append(self._render_dismissible_tag(f"Amount: {AMOUNT_LABELS.get(self._filter_amount_preset, self._filter_amount_preset)}", lambda: self._remove_amount_filter()))
            if self._sort_order != "DATE_DESC":
                tags.append(self._render_dismissible_tag(f"Sort: {SORT_LABELS.get(self._sort_order, self._sort_order)}", lambda: self._remove_sort_filter()))
            if self._search_term:
                tags.append(self._render_dismissible_tag(f'Search: "{self._search_term}"', lambda: self._clear_search()))

            # Update summary container
            self._summary_container.content = ft.Container(
                bgcolor=card_bg,
                border=ft.Border.all(1, border_col),
                border_radius=16,
                padding=ft.Padding.symmetric(horizontal=12, vertical=10),
                content=ft.Column(
                    spacing=8,
                    controls=[
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Container(
                                    bgcolor=f"{primary_col}22" if is_dark else COLOR_PRIMARY_CONTAINER,
                                    border_radius=10,
                                    padding=ft.Padding.symmetric(horizontal=8, vertical=4),
                                    content=ft.Text(f"{total_count} Found", size=11, weight=ft.FontWeight.W_800, color="#FFFFFF" if is_dark else primary_col),
                                ),
                                ft.Row(
                                    spacing=8,
                                    tight=True,
                                    controls=[
                                        ft.Row(
                                            spacing=2,
                                            tight=True,
                                            controls=[
                                                ft.Icon(ft.Icons.ARROW_UPWARD, size=12, color=COLOR_CORAL_ACCENT),
                                                ft.Text(f"-{format_currency(total_outflow, currency)}", size=11, weight=ft.FontWeight.W_700, color=COLOR_CORAL_ACCENT),
                                            ],
                                        ),
                                        ft.Row(
                                            spacing=2,
                                            tight=True,
                                            controls=[
                                                ft.Icon(ft.Icons.ARROW_DOWNWARD, size=12, color=COLOR_EMERALD_ACCENT),
                                                ft.Text(f"+{format_currency(total_inflow, currency)}", size=11, weight=ft.FontWeight.W_700, color=COLOR_EMERALD_ACCENT),
                                            ],
                                        ),
                                    ],
                                ),
                            ],
                        ),
                        ft.Row(wrap=True, spacing=6, run_spacing=6, controls=tags) if tags else ft.Container(),
                    ],
                ),
            )
            try:
                self._summary_container.update()
            except Exception:
                pass

            # 6. Render Grouped Transactions
            self._grouped_column.controls.clear()

            if filtered_txns:
                groups: Dict[str, List[Transaction]] = {}
                today_str = date.today().isoformat()
                yesterday_str = (date.today() - timedelta(days=1)).isoformat()

                for txn in filtered_txns:
                    t_date = txn.transaction_date.isoformat() if hasattr(txn.transaction_date, "isoformat") else str(txn.transaction_date)
                    if t_date == today_str:
                        lbl = "Today"
                    elif t_date == yesterday_str:
                        lbl = "Yesterday"
                    else:
                        lbl = txn.transaction_date.strftime("%B %d, %Y") if hasattr(txn.transaction_date, "strftime") else t_date
                    groups.setdefault(lbl, []).append(txn)

                for section_label, group_txns in groups.items():
                    item_controls = []
                    for t in group_txns:
                        cat_name = t.category.name if t.category else (t.description or "Expense")
                        item_title = t.description or cat_name
                        c_icon = _resolve_icon(t.category.icon if t.category else "")
                        c_color = getattr(t.category, "color", None) or (COLOR_PRIMARY if t.transaction_type == TransactionType.INCOME else "#CA3513")
                        is_inc = t.transaction_type == TransactionType.INCOME

                        item_controls.append(
                            self._build_item(
                                title=item_title,
                                dt_str=t.transaction_date.strftime("%I:%M %p") if hasattr(t.transaction_date, "strftime") else "Logged",
                                amount_paise=t.amount_paise,
                                icon=c_icon,
                                icon_color=c_color,
                                currency=currency,
                                txn=t,
                                category_name=cat_name,
                                is_income=is_inc,
                            )
                        )
                    self._grouped_column.controls.append(self._build_section_card(section_label, item_controls))

            else:
                # Check if this is an empty result due to filters vs truly empty database
                has_active_filters = self._get_active_filters_count() > 0 or bool(self._search_term)

                if has_active_filters:
                    # Show Empty State with Reset Filters Action
                    empty_card = ft.Container(
                        bgcolor=card_bg,
                        border=ft.Border.all(1, border_col),
                        border_radius=20,
                        padding=ft.Padding.symmetric(vertical=36, horizontal=20),
                        alignment=ft.Alignment.CENTER,
                        content=ft.Column(
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=12,
                            controls=[
                                ft.Container(
                                    width=56,
                                    height=56,
                                    border_radius=28,
                                    bgcolor=f"{COLOR_CORAL_ACCENT}1A" if is_dark else "#FEE2E2",
                                    alignment=ft.Alignment.CENTER,
                                    content=ft.Icon(ft.Icons.FILTER_ALT_OFF, size=28, color=COLOR_CORAL_ACCENT),
                                ),
                                ft.Text("No Matching Transactions", size=15, weight=ft.FontWeight.W_800, color=text_col),
                                ft.Text(
                                    "No entries match your active filter criteria. Try adjusting your date period, category, or amount limits.",
                                    size=12,
                                    color=sub_col,
                                    text_align=ft.TextAlign.CENTER,
                                ),
                                ft.ElevatedButton(
                                    "Reset All Filters",
                                    icon=ft.Icons.REFRESH,
                                    bgcolor=primary_col,
                                    color=COLOR_ON_PRIMARY,
                                    on_click=self._reset_all_filters,
                                ),
                            ],
                        ),
                    )
                    self._grouped_column.controls.append(empty_card)
                else:
                    # Showcase samples matching Stitch aesthetic
                    today_items = [
                        self._build_item("Lunch", "Today, 12:30 PM", 35000, ft.Icons.RESTAURANT, "#8A4CFC", currency, category_name="Food & Drink"),
                        self._build_item("Uber", "Today, 9:15 AM", 18000, ft.Icons.DIRECTIONS_CAR, "#10B981", currency, category_name="Transport"),
                        self._build_item("Groceries", "Yesterday", 55000, ft.Icons.SHOPPING_CART, "#CA3513", currency, category_name="Market"),
                    ]
                    self._grouped_column.controls.append(self._build_section_card("Today", today_items))

                    yesterday_items = [
                        self._build_item("Grocery", "Yesterday, 2:30 PM", 120000, ft.Icons.SHOPPING_BAG, "#CA3513", currency, category_name="Supermarket"),
                        self._build_item("CNG", "Yesterday, 11:50 AM", 15000, ft.Icons.LOCAL_GAS_STATION, "#0041DC", currency, category_name="Automotive"),
                    ]
                    self._grouped_column.controls.append(self._build_section_card("Yesterday", yesterday_items))

                    apr_items = [
                        self._build_item("Movie Ticket", "April 22, 7:00 PM", 60000, ft.Icons.MOVIE, "#8A4CFC", currency, category_name="Entertainment"),
                    ]
                    self._grouped_column.controls.append(self._build_section_card("April 22", apr_items))

            try:
                self._grouped_column.update()
            except Exception:
                pass

        except Exception as ex:
            logger.error("Error loading transactions: %s", ex, exc_info=True)

    def _remove_category_filter(self) -> None:
        self._filter_category_id = None
        self._filter_category_name = None
        self._update_chip_styles()
        self.refresh()

    def _remove_amount_filter(self) -> None:
        self._filter_amount_preset = "ALL"
        self._custom_min_rupees = None
        self._custom_max_rupees = None
        self._update_chip_styles()
        self.refresh()

    def _remove_sort_filter(self) -> None:
        self._sort_order = "DATE_DESC"
        self._update_chip_styles()
        self.refresh()

    def _clear_search(self) -> None:
        self._search_term = ""
        self._search_input.value = ""
        try:
            self._search_input.update()
        except Exception:
            pass
        self._update_chip_styles()
        self.refresh()
