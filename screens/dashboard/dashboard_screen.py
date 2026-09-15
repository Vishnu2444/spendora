"""Spendora — Dashboard screen with real financial statistics and transactions."""

from __future__ import annotations

import logging
from typing import Optional

from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.scrollview import ScrollView
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDButton, MDButtonText
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.screen import MDScreen

from components.transaction_card import TransactionCard
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
from database.models import Transaction, User
from services.calculation_service import CalculationService
from services.profile_service import ProfileService
from services.transaction_service import TransactionService
from utils.date_utils import date_range_this_month
from utils.formatting import format_currency

logger = logging.getLogger(__name__)


class DashboardScreen(MDScreen):
    """Dashboard displaying live financial balance, burn rate, and recent transactions."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.name = "dashboard"
        self._profile_service = ProfileService()
        self._calculation_service = CalculationService()
        self._transaction_service = TransactionService()
        self._user: Optional[User] = None
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
                text="SPENDORA",
                font_style="Headline",
                role="small",
                adaptive_height=True,
                theme_text_color="Custom",
                text_color=APP_TEXT,
            )
        )
        top_bar.add_widget(MDBoxLayout())  # Spacer

        # Quick Add button in top bar
        quick_add_btn = MDButton(
            style="filled",
            on_release=self._open_add_transaction,
            pos_hint={"center_y": 0.5},
        )
        quick_add_btn.add_widget(MDButtonText(text="+ Add"))
        top_bar.add_widget(quick_add_btn)

        root.add_widget(top_bar)

        # --- Scrollable Content ---
        scroll = ScrollView(do_scroll_x=False)
        content = MDBoxLayout(
            orientation="vertical",
            adaptive_height=True,
            padding=[dp(20), dp(10), dp(20), dp(24)],
            spacing=dp(16),
        )

        # --- Greeting Row ---
        hello_row = MDBoxLayout(orientation="horizontal", adaptive_height=True, spacing=dp(12))
        sparkle = MDCard(
            style="filled",
            md_bg_color=(0.25, 0.25, 0.36, 1),
            size_hint=(None, None),
            size=(dp(42), dp(42)),
            radius=[dp(21)],
        )
        sparkle.add_widget(
            MDLabel(
                text="✦",
                halign="center",
                valign="middle",
                theme_text_color="Custom",
                text_color=APP_TEXT,
                font_style="Title",
            )
        )
        hello_row.add_widget(sparkle)

        self._greeting_label = MDLabel(
            text="Welcome back!",
            font_style="Headline",
            role="medium",
            adaptive_height=True,
            theme_text_color="Custom",
            text_color=APP_TEXT,
        )
        hello_row.add_widget(self._greeting_label)
        content.add_widget(hello_row)

        # --- Financial Summary Row (Surplus & Burn Status) ---
        self._summary_row = MDBoxLayout(orientation="horizontal", adaptive_height=True, spacing=dp(12))
        self._surplus_card = self._create_stat_card("Net This Month", "₹0.00", APP_SUCCESS, "0 transactions")
        self._burn_card = self._create_stat_card("Burn Status", "₹0.00/day", APP_SUCCESS, "Avg daily expense")
        self._summary_row.add_widget(self._surplus_card["widget"])
        self._summary_row.add_widget(self._burn_card["widget"])
        content.add_widget(self._summary_row)

        # --- Income & Expense Row ---
        inc_exp_row = MDBoxLayout(orientation="horizontal", adaptive_height=True, spacing=dp(12))
        self._income_card = self._create_stat_card("Total Income", "₹0.00", APP_SUCCESS, "This month")
        self._expense_card = self._create_stat_card("Total Spent", "₹0.00", APP_DANGER, "This month")
        inc_exp_row.add_widget(self._income_card["widget"])
        inc_exp_row.add_widget(self._expense_card["widget"])
        content.add_widget(inc_exp_row)

        # --- Recent Transactions Section ---
        recent_header = MDBoxLayout(orientation="horizontal", adaptive_height=True)
        recent_header.add_widget(
            MDLabel(
                text="Recent Transactions",
                font_style="Title",
                role="medium",
                adaptive_height=True,
                theme_text_color="Custom",
                text_color=APP_TEXT,
            )
        )
        recent_header.add_widget(MDBoxLayout())

        view_all_btn = MDButton(
            style="text",
            on_release=self._switch_to_transactions,
        )
        view_all_btn.add_widget(
            MDButtonText(
                text="View All →",
                theme_text_color="Custom",
                text_color=APP_ACCENT,
            )
        )
        recent_header.add_widget(view_all_btn)
        content.add_widget(recent_header)

        # Container for dynamic transaction cards
        self._recent_list = MDBoxLayout(
            orientation="vertical",
            adaptive_height=True,
            spacing=dp(8),
        )
        content.add_widget(self._recent_list)

        scroll.add_widget(content)
        root.add_widget(scroll)
        self.add_widget(root)

    def _create_stat_card(self, title: str, value: str, color: tuple, meta: str) -> dict:
        """Create a summary card with references to dynamic label widgets."""
        card = MDCard(
            style="filled",
            md_bg_color=APP_BG_CARD,
            size_hint_x=0.5,
            size_hint_y=None,
            height=dp(100),
            radius=[dp(18)],
            padding=[dp(14), dp(12), dp(14), dp(12)],
        )
        layout = MDBoxLayout(orientation="vertical", spacing=dp(6))
        title_lbl = MDLabel(
            text=title.upper(),
            font_style="Label",
            role="large",
            adaptive_height=True,
            theme_text_color="Custom",
            text_color=APP_MUTED_TEXT,
        )
        layout.add_widget(title_lbl)

        val_lbl = MDLabel(
            text=value,
            font_style="Headline",
            role="medium",
            adaptive_height=True,
            theme_text_color="Custom",
            text_color=APP_TEXT,
        )
        layout.add_widget(val_lbl)

        meta_lbl = MDLabel(
            text=meta,
            theme_text_color="Custom",
            text_color=color,
            adaptive_height=True,
            font_style="Body",
            role="small",
        )
        layout.add_widget(meta_lbl)
        card.add_widget(layout)

        return {
            "widget": card,
            "val_label": val_lbl,
            "meta_label": meta_lbl,
        }

    # ------------------------------------------------------------------
    # Data Refresh
    # ------------------------------------------------------------------

    def refresh(self) -> None:
        """Fetch real data from services and refresh all dashboard cards."""
        try:
            self._user = self._profile_service.get_current_user()
            if not self._user:
                return

            self._greeting_label.text = f"Good day, {self._user.name}!"
            currency = self._user.currency or DEFAULT_CURRENCY

            # Calculate current month's summary
            start_date, end_date = date_range_this_month()
            summary = self._calculation_service.calculate_period_summary(
                user_id=self._user.id,
                start_date=start_date,
                end_date=end_date,
            )

            # Update Net / Surplus card
            net_paise = summary["net_paise"]
            net_str = format_currency(net_paise, currency)
            if net_paise >= 0:
                self._surplus_card["val_label"].text = f"+{net_str}"
                self._surplus_card["val_label"].text_color = APP_SUCCESS
                self._surplus_card["meta_label"].text = f"{summary['status']} · {summary['transaction_count']} txns"
                self._surplus_card["meta_label"].text_color = APP_SUCCESS
            else:
                self._surplus_card["val_label"].text = net_str
                self._surplus_card["val_label"].text_color = APP_DANGER
                self._surplus_card["meta_label"].text = f"{summary['status']} · {summary['transaction_count']} txns"
                self._surplus_card["meta_label"].text_color = APP_DANGER

            # Update Burn Rate / Daily average card
            daily_avg_paise = summary["avg_daily_expense_paise"]
            daily_avg_str = format_currency(daily_avg_paise, currency)
            self._burn_card["val_label"].text = f"{daily_avg_str}/day"
            self._burn_card["val_label"].text_color = APP_TEXT
            self._burn_card["meta_label"].text = "Avg daily expense"

            # Update Income & Expense cards
            income_str = format_currency(summary["total_income_paise"], currency)
            self._income_card["val_label"].text = income_str
            self._income_card["val_label"].text_color = APP_SUCCESS

            expense_str = format_currency(summary["total_expenses_paise"], currency)
            self._expense_card["val_label"].text = expense_str
            self._expense_card["val_label"].text_color = APP_DANGER

            # Load recent transactions
            self._load_recent_transactions(currency)

        except Exception as exc:
            logger.error("Dashboard refresh error: %s", exc)

    def _load_recent_transactions(self, currency: str) -> None:
        """Fetch and display up to 4 most recent transactions."""
        self._recent_list.clear_widgets()

        if not self._user:
            return

        recent_txns = self._transaction_service.get_recent_transactions(
            user_id=self._user.id,
            limit=4,
        )

        if not recent_txns:
            empty_card = MDCard(
                style="filled",
                md_bg_color=APP_BG_CARD,
                radius=[dp(14)],
                padding=[dp(16), dp(20), dp(16), dp(20)],
                size_hint_y=None,
                height=dp(80),
            )
            empty_card.add_widget(
                MDLabel(
                    text="No transactions recorded yet.\nTap '+ Add' to log your first income or expense!",
                    halign="center",
                    theme_text_color="Custom",
                    text_color=APP_MUTED_TEXT,
                    font_style="Body",
                    role="medium",
                )
            )
            self._recent_list.add_widget(empty_card)
            return

        for txn in recent_txns:
            card = TransactionCard(
                transaction=txn,
                currency=currency,
                on_tap=self._open_edit_transaction,
            )
            self._recent_list.add_widget(card)

    def on_enter(self, *args) -> None:
        Clock.schedule_once(lambda dt: self.refresh(), 0.1)

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _open_add_transaction(self, *args) -> None:
        """Open AddEditTransactionScreen in add mode."""
        if not self._user:
            self._user = self._profile_service.get_current_user()
            if not self._user:
                return

        app = MDApp.get_running_app()
        if app and app.root and app.root.has_screen("add_edit_transaction"):
            screen = app.root.get_screen("add_edit_transaction")
            screen.setup(user_id=self._user.id, transaction_id=None)
            app.root.current = "add_edit_transaction"

    def _open_edit_transaction(self, txn: Transaction) -> None:
        """Open AddEditTransactionScreen in edit mode."""
        if not self._user:
            self._user = self._profile_service.get_current_user()
            if not self._user:
                return

        app = MDApp.get_running_app()
        if app and app.root and app.root.has_screen("add_edit_transaction"):
            screen = app.root.get_screen("add_edit_transaction")
            screen.setup(user_id=self._user.id, transaction_id=txn.id)
            app.root.current = "add_edit_transaction"

    def _switch_to_transactions(self, *args) -> None:
        """Switch navigation tab to Transactions screen."""
        app = MDApp.get_running_app()
        if app and hasattr(app, "switch_tab"):
            app.switch_tab("transactions")
