"""
Spendora — Analytics Screen.

Visual financial performance and analytics across arbitrary date ranges:
- Preset range toggles (This Month, Last Month, Last 30 Days, This Year, Custom)
- Custom date range navigation
- Comprehensive performance summary (opening/closing balance, net, daily burn)
- Period-over-period comparison indicators
- Category spending distribution with visual progress gauges
- Key spending insights (peak day, largest purchase, average transaction size)
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Optional

from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.scrollview import ScrollView
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDButton, MDButtonText
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.screen import MDScreen

from components.category_breakdown_item import CategoryBreakdownItem
from config.settings import (
    APP_ACCENT,
    APP_BG_CARD,
    APP_BG_DARK,
    APP_DANGER,
    APP_MUTED_TEXT,
    APP_SUCCESS,
    APP_TEXT,
    DEFAULT_CURRENCY,
)
from database.models import User
from services.analytics_service import AnalyticsService
from services.profile_service import ProfileService
from utils.date_utils import (
    date_range_last_month,
    date_range_this_month,
    date_range_this_year,
    today,
)
from utils.formatting import format_currency, format_date_range

logger = logging.getLogger(__name__)


class AnalyticsScreen(MDScreen):
    """Analytics and financial performance screen."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.name = "analytics"
        self._analytics_service = AnalyticsService()
        self._profile_service = ProfileService()
        self._user: Optional[User] = None

        # Active date range (defaults to this month)
        self._active_preset = "this_month"
        self._start_date, self._end_date = date_range_this_month()
        self._build_ui()

    def _build_ui(self) -> None:
        root = MDBoxLayout(orientation="vertical", md_bg_color=APP_BG_DARK)

        # --- Top Bar ---
        top_bar = MDBoxLayout(
            orientation="horizontal",
            adaptive_height=True,
            padding=[dp(18), dp(16), dp(18), dp(8)],
            spacing=dp(8),
        )
        top_bar.add_widget(
            MDLabel(
                text="Financial Analytics",
                font_style="Headline",
                role="small",
                adaptive_height=True,
                theme_text_color="Custom",
                text_color=APP_TEXT,
            )
        )
        root.add_widget(top_bar)

        # --- Scrollable Content ---
        scroll = ScrollView(do_scroll_x=False)
        self._content = MDBoxLayout(
            orientation="vertical",
            adaptive_height=True,
            padding=[dp(16), dp(8), dp(16), dp(24)],
            spacing=dp(16),
        )

        # --- Preset Selector Buttons ---
        preset_row = MDBoxLayout(
            orientation="horizontal",
            adaptive_height=True,
            spacing=dp(6),
        )

        self._btn_this_month = self._create_preset_btn("This Month", "this_month")
        self._btn_last_month = self._create_preset_btn("Last Month", "last_month")
        self._btn_30_days = self._create_preset_btn("30 Days", "30_days")
        self._btn_this_year = self._create_preset_btn("This Year", "this_year")
        self._btn_custom = self._create_preset_btn("Custom", "custom")

        preset_row.add_widget(self._btn_this_month)
        preset_row.add_widget(self._btn_last_month)
        preset_row.add_widget(self._btn_30_days)
        preset_row.add_widget(self._btn_this_year)
        preset_row.add_widget(self._btn_custom)
        self._content.add_widget(preset_row)

        # --- Custom Date Range Controls (visible in custom mode) ---
        self._custom_controls = MDBoxLayout(
            orientation="vertical",
            adaptive_height=True,
            spacing=dp(8),
            opacity=0,
            size_hint_y=None,
            height=dp(0),
        )
        custom_row = MDBoxLayout(orientation="horizontal", adaptive_height=True, spacing=dp(8))
        custom_row.add_widget(
            MDLabel(
                text="Start:",
                font_style="Body",
                role="small",
                adaptive_height=True,
                theme_text_color="Custom",
                text_color=APP_MUTED_TEXT,
                pos_hint={"center_y": 0.5},
            )
        )
        self._custom_start_label = MDLabel(
            text=str(self._start_date),
            font_style="Body",
            role="medium",
            adaptive_height=True,
            theme_text_color="Custom",
            text_color=APP_TEXT,
            pos_hint={"center_y": 0.5},
        )
        custom_row.add_widget(self._custom_start_label)
        start_prev = MDButton(style="text", on_release=lambda *_: self._adjust_date("start", -1))
        start_prev.add_widget(MDButtonText(text="◀"))
        custom_row.add_widget(start_prev)
        start_next = MDButton(style="text", on_release=lambda *_: self._adjust_date("start", 1))
        start_next.add_widget(MDButtonText(text="▶"))
        custom_row.add_widget(start_next)

        custom_row.add_widget(
            MDLabel(
                text="End:",
                font_style="Body",
                role="small",
                adaptive_height=True,
                theme_text_color="Custom",
                text_color=APP_MUTED_TEXT,
                pos_hint={"center_y": 0.5},
            )
        )
        self._custom_end_label = MDLabel(
            text=str(self._end_date),
            font_style="Body",
            role="medium",
            adaptive_height=True,
            theme_text_color="Custom",
            text_color=APP_TEXT,
            pos_hint={"center_y": 0.5},
        )
        custom_row.add_widget(self._custom_end_label)
        end_prev = MDButton(style="text", on_release=lambda *_: self._adjust_date("end", -1))
        end_prev.add_widget(MDButtonText(text="◀"))
        custom_row.add_widget(end_prev)
        end_next = MDButton(style="text", on_release=lambda *_: self._adjust_date("end", 1))
        end_next.add_widget(MDButtonText(text="▶"))
        custom_row.add_widget(end_next)

        self._custom_controls.add_widget(custom_row)
        self._content.add_widget(self._custom_controls)

        # --- Active Period Date Range Display ---
        self._date_range_label = MDLabel(
            text=format_date_range(self._start_date, self._end_date),
            font_style="Body",
            role="medium",
            adaptive_height=True,
            theme_text_color="Custom",
            text_color=APP_MUTED_TEXT,
        )
        self._content.add_widget(self._date_range_label)

        # --- Performance Summary Card ---
        self._perf_card = self._build_performance_card()
        self._content.add_widget(self._perf_card)

        # --- Key Financial Insights Card ---
        self._insights_card = self._build_insights_card()
        self._content.add_widget(self._insights_card)

        # --- Category Breakdown Section ---
        dist_header = MDBoxLayout(orientation="horizontal", adaptive_height=True)
        dist_header.add_widget(
            MDLabel(
                text="Spending Distribution",
                font_style="Title",
                role="medium",
                adaptive_height=True,
                theme_text_color="Custom",
                text_color=APP_TEXT,
            )
        )
        self._content.add_widget(dist_header)

        self._distribution_container = MDBoxLayout(
            orientation="vertical",
            adaptive_height=True,
            spacing=dp(8),
        )
        self._content.add_widget(self._distribution_container)

        scroll.add_widget(self._content)
        root.add_widget(scroll)
        self.add_widget(root)

    # ------------------------------------------------------------------
    # Card Builders
    # ------------------------------------------------------------------

    def _create_preset_btn(self, text: str, preset_key: str) -> MDButton:
        btn = MDButton(
            style="filled" if preset_key == self._active_preset else "tonal",
            size_hint_x=0.2,
            on_release=lambda *_: self._set_preset(preset_key),
        )
        btn.add_widget(MDButtonText(text=text, font_style="Label", role="small"))
        return btn

    def _build_performance_card(self) -> MDCard:
        card = MDCard(
            style="filled",
            md_bg_color=APP_BG_CARD,
            radius=[dp(16)],
            padding=[dp(16), dp(16), dp(16), dp(16)],
            size_hint_y=None,
            height=dp(170),
        )
        layout = MDBoxLayout(orientation="vertical", spacing=dp(8))

        top_row = MDBoxLayout(orientation="horizontal", adaptive_height=True)
        top_row.add_widget(
            MDLabel(
                text="NET PERFORMANCE",
                font_style="Label",
                role="medium",
                adaptive_height=True,
                theme_text_color="Custom",
                text_color=APP_MUTED_TEXT,
            )
        )
        top_row.add_widget(MDBoxLayout())
        self._status_badge = MDLabel(
            text="GAIN",
            font_style="Label",
            role="small",
            adaptive_height=True,
            theme_text_color="Custom",
            text_color=APP_SUCCESS,
        )
        top_row.add_widget(self._status_badge)
        layout.add_widget(top_row)

        self._net_label = MDLabel(
            text="₹0.00",
            font_style="Headline",
            role="large",
            adaptive_height=True,
            theme_text_color="Custom",
            text_color=APP_TEXT,
        )
        layout.add_widget(self._net_label)

        self._comparison_label = MDLabel(
            text="Comparing against previous period...",
            font_style="Body",
            role="small",
            adaptive_height=True,
            theme_text_color="Custom",
            text_color=APP_MUTED_TEXT,
        )
        layout.add_widget(self._comparison_label)

        # 3-stat sub-row: Income | Expenses | Daily Avg
        stats_row = MDBoxLayout(orientation="horizontal", adaptive_height=True, spacing=dp(8))

        self._inc_val_lbl = MDLabel(
            text="Inc: ₹0",
            font_style="Body",
            role="small",
            adaptive_height=True,
            theme_text_color="Custom",
            text_color=APP_SUCCESS,
        )
        self._exp_val_lbl = MDLabel(
            text="Exp: ₹0",
            font_style="Body",
            role="small",
            adaptive_height=True,
            theme_text_color="Custom",
            text_color=APP_DANGER,
        )
        self._burn_val_lbl = MDLabel(
            text="Burn: ₹0/d",
            font_style="Body",
            role="small",
            adaptive_height=True,
            theme_text_color="Custom",
            text_color=APP_MUTED_TEXT,
        )

        stats_row.add_widget(self._inc_val_lbl)
        stats_row.add_widget(self._exp_val_lbl)
        stats_row.add_widget(self._burn_val_lbl)
        layout.add_widget(stats_row)

        card.add_widget(layout)
        return card

    def _build_insights_card(self) -> MDCard:
        card = MDCard(
            style="filled",
            md_bg_color=APP_BG_CARD,
            radius=[dp(16)],
            padding=[dp(16), dp(14), dp(16), dp(14)],
            size_hint_y=None,
            height=dp(130),
        )
        layout = MDBoxLayout(orientation="vertical", spacing=dp(6))

        layout.add_widget(
            MDLabel(
                text="KEY INSIGHTS",
                font_style="Label",
                role="medium",
                adaptive_height=True,
                theme_text_color="Custom",
                text_color=APP_MUTED_TEXT,
            )
        )

        self._top_cat_lbl = MDLabel(
            text="• Top Category: None",
            font_style="Body",
            role="medium",
            adaptive_height=True,
            theme_text_color="Custom",
            text_color=APP_TEXT,
        )
        self._peak_day_lbl = MDLabel(
            text="• Peak Spending: None",
            font_style="Body",
            role="medium",
            adaptive_height=True,
            theme_text_color="Custom",
            text_color=APP_TEXT,
        )
        self._largest_exp_lbl = MDLabel(
            text="• Largest Purchase: None",
            font_style="Body",
            role="medium",
            adaptive_height=True,
            theme_text_color="Custom",
            text_color=APP_TEXT,
        )

        layout.add_widget(self._top_cat_lbl)
        layout.add_widget(self._peak_day_lbl)
        layout.add_widget(self._largest_exp_lbl)

        card.add_widget(layout)
        return card

    # ------------------------------------------------------------------
    # Presets and Date Controls
    # ------------------------------------------------------------------

    def _set_preset(self, preset_key: str) -> None:
        self._active_preset = preset_key

        # Update button styles
        for key, btn in [
            ("this_month", self._btn_this_month),
            ("last_month", self._btn_last_month),
            ("30_days", self._btn_30_days),
            ("this_year", self._btn_this_year),
            ("custom", self._btn_custom),
        ]:
            btn.style = "filled" if key == preset_key else "tonal"

        if preset_key == "this_month":
            self._start_date, self._end_date = date_range_this_month()
            self._hide_custom_controls()
        elif preset_key == "last_month":
            self._start_date, self._end_date = date_range_last_month()
            self._hide_custom_controls()
        elif preset_key == "30_days":
            end = today()
            start = end - timedelta(days=29)
            self._start_date, self._end_date = start, end
            self._hide_custom_controls()
        elif preset_key == "this_year":
            self._start_date, self._end_date = date_range_this_year()
            self._hide_custom_controls()
        elif preset_key == "custom":
            self._show_custom_controls()

        self._custom_start_label.text = str(self._start_date)
        self._custom_end_label.text = str(self._end_date)
        self.refresh()

    def _show_custom_controls(self) -> None:
        self._custom_controls.opacity = 1
        self._custom_controls.height = dp(40)

    def _hide_custom_controls(self) -> None:
        self._custom_controls.opacity = 0
        self._custom_controls.height = dp(0)

    def _adjust_date(self, target: str, delta_days: int) -> None:
        """Adjust custom start or end date."""
        if target == "start":
            new_date = self._start_date + timedelta(days=delta_days)
            if new_date <= self._end_date:
                self._start_date = new_date
        elif target == "end":
            new_date = self._end_date + timedelta(days=delta_days)
            if new_date >= self._start_date:
                self._end_date = new_date

        self._custom_start_label.text = str(self._start_date)
        self._custom_end_label.text = str(self._end_date)
        self.refresh()

    # ------------------------------------------------------------------
    # Data Refresh & Rendering
    # ------------------------------------------------------------------

    def refresh(self) -> None:
        """Fetch analytical data and update the entire screen."""
        self._user = self._profile_service.get_current_user()
        if not self._user:
            return

        currency = self._user.currency or DEFAULT_CURRENCY
        self._date_range_label.text = (
            f"{format_date_range(self._start_date, self._end_date)} "
            f"({(self._end_date - self._start_date).days + 1} days)"
        )

        try:
            # 1. Performance Overview & Comparison
            perf = self._analytics_service.calculate_date_range_performance(
                user_id=self._user.id,
                start_date=self._start_date,
                end_date=self._end_date,
            )
            self._update_performance_card(perf, currency)

            # 2. Spending Insights
            insights = self._analytics_service.get_spending_insights(
                user_id=self._user.id,
                start_date=self._start_date,
                end_date=self._end_date,
            )
            self._update_insights_card(insights, currency)

            # 3. Category Spending Distribution
            dist = self._analytics_service.get_category_spending_distribution(
                user_id=self._user.id,
                start_date=self._start_date,
                end_date=self._end_date,
            )
            self._update_distribution_list(dist, currency)

        except Exception as exc:
            logger.error("Analytics refresh error: %s", exc)

    def _update_performance_card(self, perf: dict, currency: str) -> None:
        cur = perf["current"]
        deltas = perf["deltas"]

        net_paise = cur["net_paise"]
        net_str = format_currency(net_paise, currency)

        if net_paise >= 0:
            self._net_label.text = f"+{net_str}"
            self._net_label.text_color = APP_SUCCESS
            self._status_badge.text = cur["status"]
            self._status_badge.text_color = APP_SUCCESS
        else:
            self._net_label.text = net_str
            self._net_label.text_color = APP_DANGER
            self._status_badge.text = cur["status"]
            self._status_badge.text_color = APP_DANGER

        # Period comparison message
        exp_pct = deltas["expense_pct_change"]
        if exp_pct is not None:
            if exp_pct > 0:
                self._comparison_label.text = f"Expenses ↑ {exp_pct}% vs preceding period"
                self._comparison_label.text_color = APP_DANGER
            elif exp_pct < 0:
                self._comparison_label.text = f"Expenses ↓ {abs(exp_pct)}% vs preceding period"
                self._comparison_label.text_color = APP_SUCCESS
            else:
                self._comparison_label.text = "Expenses on par with preceding period"
                self._comparison_label.text_color = APP_MUTED_TEXT
        else:
            self._comparison_label.text = "No prior spending recorded to compare"
            self._comparison_label.text_color = APP_MUTED_TEXT

        # Income / Expense / Daily Avg row
        inc_str = format_currency(cur["total_income_paise"], currency)
        exp_str = format_currency(cur["total_expenses_paise"], currency)
        burn_str = format_currency(cur["avg_daily_expense_paise"], currency)

        self._inc_val_lbl.text = f"Inc: {inc_str}"
        self._exp_val_lbl.text = f"Exp: {exp_str}"
        self._burn_val_lbl.text = f"Burn: {burn_str}/d"

    def _update_insights_card(self, insights: dict, currency: str) -> None:
        # Top category
        if insights["top_category_name"]:
            amt = format_currency(insights["top_category_paise"], currency)
            self._top_cat_lbl.text = f"• Top Category: {insights['top_category_name']} ({amt})"
        else:
            self._top_cat_lbl.text = "• Top Category: None in this period"

        # Peak day
        if insights["peak_day"]:
            peak_amt = format_currency(insights["peak_day_amount_paise"], currency)
            self._peak_day_lbl.text = f"• Peak Spending: {insights['peak_day'].strftime('%d %b')} ({peak_amt})"
        else:
            self._peak_day_lbl.text = "• Peak Spending: None"

        # Largest expense
        largest = insights["largest_expense"]
        if largest:
            l_amt = format_currency(largest["amount_paise"], currency)
            self._largest_exp_lbl.text = f"• Largest Purchase: {largest['description']} ({l_amt})"
        else:
            self._largest_exp_lbl.text = "• Largest Purchase: None"

    def _update_distribution_list(self, dist: list, currency: str) -> None:
        self._distribution_container.clear_widgets()

        if not dist:
            empty_box = MDCard(
                style="filled",
                md_bg_color=APP_BG_CARD,
                radius=[dp(12)],
                padding=[dp(16), dp(20), dp(16), dp(20)],
                size_hint_y=None,
                height=dp(80),
            )
            empty_box.add_widget(
                MDLabel(
                    text="No expenses recorded in this period.",
                    halign="center",
                    theme_text_color="Custom",
                    text_color=APP_MUTED_TEXT,
                    font_style="Body",
                    role="medium",
                )
            )
            self._distribution_container.add_widget(empty_box)
            return

        for item in dist:
            widget = CategoryBreakdownItem(
                category_name=item["name"],
                amount_paise=item["amount_paise"],
                percentage=item["percentage"],
                transaction_count=item["transaction_count"],
                color_hex=item["color"],
                icon_name=item["icon"],
                currency=currency,
            )
            self._distribution_container.add_widget(widget)

    def on_enter(self, *args) -> None:
        Clock.schedule_once(lambda dt: self.refresh(), 0.1)
