"""
Spendora — Transactions Screen.

Displays user transactions with:
- Live search by description / notes
- Filtering by type (All, Expenses, Income)
- Reusable TransactionCard widgets
- Tap to edit transaction (opens AddEditTransactionScreen)
- Quick Add button
- Empty state when no transactions exist
"""

from __future__ import annotations

import logging
from typing import List, Optional

from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.scrollview import ScrollView
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDButton, MDButtonText
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.screen import MDScreen
from kivymd.uix.textfield import MDTextField, MDTextFieldHintText

from components.transaction_card import TransactionCard
from config.settings import (
    APP_BG_DARK,
    APP_BG_CARD,
    APP_BG_PANEL,
    APP_TEXT,
    APP_MUTED_TEXT,
    APP_ACCENT,
    APP_SUCCESS,
    APP_DANGER,
    DEFAULT_CURRENCY,
)
from database.models import Transaction, TransactionType, User
from services.profile_service import ProfileService
from services.transaction_service import TransactionService

logger = logging.getLogger(__name__)


class TransactionsScreen(MDScreen):
    """Transactions list screen with search, type filters, and CRUD navigation."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.name = "transactions"
        self._transaction_service = TransactionService()
        self._profile_service = ProfileService()
        self._user: Optional[User] = None
        self._current_filter: Optional[str] = None  # None = All, "EXPENSE", "INCOME"
        self._search_term: str = ""
        self._search_event = None
        self._build_ui()

    def _build_ui(self) -> None:
        root = MDBoxLayout(
            orientation="vertical",
            md_bg_color=APP_BG_DARK,
            padding=[dp(16), dp(16), dp(16), dp(8)],
            spacing=dp(12),
        )

        # --- Top Header ---
        header = MDBoxLayout(
            orientation="horizontal",
            adaptive_height=True,
            spacing=dp(8),
        )

        header_text_box = MDBoxLayout(orientation="vertical", adaptive_height=True, spacing=dp(2))
        header_text_box.add_widget(
            MDLabel(
                text="Transactions",
                font_style="Headline",
                role="small",
                adaptive_height=True,
                theme_text_color="Custom",
                text_color=APP_TEXT,
            )
        )
        self._count_label = MDLabel(
            text="0 transactions",
            font_style="Body",
            role="small",
            adaptive_height=True,
            theme_text_color="Custom",
            text_color=APP_MUTED_TEXT,
        )
        header_text_box.add_widget(self._count_label)
        header.add_widget(header_text_box)

        header.add_widget(MDBoxLayout())  # Spacer

        # Add button
        add_btn = MDButton(
            style="filled",
            on_release=self._open_add_transaction,
            pos_hint={"center_y": 0.5},
        )
        add_btn.add_widget(MDButtonText(text="+ Add"))
        header.add_widget(add_btn)

        root.add_widget(header)

        # --- Search Bar ---
        self._search_field = MDTextField(
            MDTextFieldHintText(text="Search by description or notes..."),
            mode="outlined",
        )
        self._search_field.bind(text=self._on_search_text_changed)
        root.add_widget(self._search_field)

        # --- Filter Chips Row ---
        filters_row = MDBoxLayout(
            orientation="horizontal",
            adaptive_height=True,
            spacing=dp(8),
        )

        self._filter_all_btn = MDButton(
            style="filled",
            size_hint_x=0.33,
            on_release=lambda *_: self._set_filter(None),
        )
        self._filter_all_btn.add_widget(MDButtonText(text="All"))

        self._filter_expense_btn = MDButton(
            style="tonal",
            size_hint_x=0.33,
            on_release=lambda *_: self._set_filter("EXPENSE"),
        )
        self._filter_expense_btn.add_widget(MDButtonText(text="Expenses"))

        self._filter_income_btn = MDButton(
            style="tonal",
            size_hint_x=0.33,
            on_release=lambda *_: self._set_filter("INCOME"),
        )
        self._filter_income_btn.add_widget(MDButtonText(text="Income"))

        filters_row.add_widget(self._filter_all_btn)
        filters_row.add_widget(self._filter_expense_btn)
        filters_row.add_widget(self._filter_income_btn)
        root.add_widget(filters_row)

        # --- Scrollable Transaction List ---
        scroll = ScrollView(do_scroll_x=False)
        self._list_layout = MDBoxLayout(
            orientation="vertical",
            adaptive_height=True,
            spacing=dp(8),
            padding=[0, dp(4), 0, dp(16)],
        )
        scroll.add_widget(self._list_layout)
        root.add_widget(scroll)

        self.add_widget(root)

    # ------------------------------------------------------------------
    # Filtering & Search
    # ------------------------------------------------------------------

    def _set_filter(self, filter_type: Optional[str]) -> None:
        """Switch active filter (None, 'EXPENSE', 'INCOME')."""
        self._current_filter = filter_type
        self._filter_all_btn.style = "filled" if filter_type is None else "tonal"
        self._filter_expense_btn.style = "filled" if filter_type == "EXPENSE" else "tonal"
        self._filter_income_btn.style = "filled" if filter_type == "INCOME" else "tonal"
        self.load_transactions()

    def _on_search_text_changed(self, instance, text: str) -> None:
        """Debounce search updates."""
        self._search_term = text.strip()
        if self._search_event:
            self._search_event.cancel()
        self._search_event = Clock.schedule_once(lambda dt: self.load_transactions(), 0.3)

    # ------------------------------------------------------------------
    # Data Loading
    # ------------------------------------------------------------------

    def refresh(self) -> None:
        """Refresh current user and transaction list."""
        self._user = self._profile_service.get_current_user()
        self.load_transactions()

    def on_enter(self, *args) -> None:
        """Called whenever the screen becomes visible."""
        Clock.schedule_once(lambda dt: self.refresh(), 0.1)

    def load_transactions(self) -> None:
        """Fetch transactions from TransactionService and update UI list."""
        if not self._user:
            self._user = self._profile_service.get_current_user()
            if not self._user:
                return

        self._list_layout.clear_widgets()

        try:
            transactions = self._transaction_service.list_transactions(
                user_id=self._user.id,
                transaction_type=self._current_filter,
                search_term=self._search_term if self._search_term else None,
            )

            total_count = len(transactions)
            currency = self._user.currency or DEFAULT_CURRENCY

            if total_count == 1:
                self._count_label.text = "1 transaction"
            else:
                self._count_label.text = f"{total_count} transactions"

            if not transactions:
                self._show_empty_state()
                return

            for txn in transactions:
                card = TransactionCard(
                    transaction=txn,
                    currency=currency,
                    on_tap=self._open_edit_transaction,
                )
                self._list_layout.add_widget(card)

        except Exception as exc:
            logger.error("Error loading transactions: %s", exc)
            self._list_layout.add_widget(
                MDLabel(
                    text=f"Error loading transactions: {exc}",
                    theme_text_color="Custom",
                    text_color=APP_DANGER,
                    adaptive_height=True,
                )
            )

    def _show_empty_state(self) -> None:
        """Render a placeholder when there are no transactions."""
        empty_box = MDBoxLayout(
            orientation="vertical",
            adaptive_height=True,
            padding=[dp(20), dp(40), dp(20), dp(20)],
            spacing=dp(12),
        )

        icon_card = MDCard(
            style="filled",
            md_bg_color=APP_BG_CARD,
            size_hint=(None, None),
            size=(dp(60), dp(60)),
            radius=[dp(30)],
            pos_hint={"center_x": 0.5},
        )
        icon_card.add_widget(
            MDLabel(
                text="💳",
                halign="center",
                valign="middle",
                font_style="Headline",
                role="medium",
            )
        )
        empty_box.add_widget(icon_card)

        if self._search_term:
            msg = f"No transactions matching '{self._search_term}'"
            sub_msg = "Try a different search keyword or clear filters."
        elif self._current_filter:
            filter_name = "expenses" if self._current_filter == "EXPENSE" else "income"
            msg = f"No {filter_name} recorded"
            sub_msg = "Tap '+ Add' to record one."
        else:
            msg = "No transactions yet"
            sub_msg = "Track your daily spending and income to see insights."

        empty_box.add_widget(
            MDLabel(
                text=msg,
                font_style="Title",
                role="medium",
                halign="center",
                adaptive_height=True,
                theme_text_color="Custom",
                text_color=APP_TEXT,
            )
        )
        empty_box.add_widget(
            MDLabel(
                text=sub_msg,
                font_style="Body",
                role="medium",
                halign="center",
                adaptive_height=True,
                theme_text_color="Custom",
                text_color=APP_MUTED_TEXT,
            )
        )

        self._list_layout.add_widget(empty_box)

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _open_add_transaction(self, *args) -> None:
        """Navigate to AddEditTransactionScreen in add mode."""
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
        """Navigate to AddEditTransactionScreen in edit mode."""
        if not self._user:
            self._user = self._profile_service.get_current_user()
            if not self._user:
                return

        app = MDApp.get_running_app()
        if app and app.root and app.root.has_screen("add_edit_transaction"):
            screen = app.root.get_screen("add_edit_transaction")
            screen.setup(user_id=self._user.id, transaction_id=txn.id)
            app.root.current = "add_edit_transaction"
