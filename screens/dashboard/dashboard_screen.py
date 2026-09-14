"""
Spendora — Dashboard Screen (Phase 1 placeholder).

Shows greeting, current balance, income/expense summary, and recent
transactions. In Phase 1 this is a polished placeholder with real data
coming from the database.

Phase 2 will wire up the full CalculationService.
"""

from __future__ import annotations

import logging
from datetime import date

from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.scrollview import ScrollView
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDButton, MDButtonText, MDIconButton
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.screen import MDScreen

from database.database import get_session
from database.repositories.user_repository import UserRepository
from utils.formatting import format_currency, format_date
from utils.date_utils import today

logger = logging.getLogger(__name__)


class DashboardScreen(MDScreen):
    """Main dashboard — summary cards and recent transactions."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.name = "dashboard"
        self._build_ui()

    def _build_ui(self) -> None:
        root = MDBoxLayout(
            orientation="vertical",
            md_bg_color=self.theme_cls.backgroundColor,
        )

        scroll = ScrollView()
        self._content = MDBoxLayout(
            orientation="vertical",
            adaptive_height=True,
            padding=[dp(20), dp(24), dp(20), dp(24)],
            spacing=dp(16),
        )

        # ---- Greeting row ----
        greeting_row = MDBoxLayout(
            orientation="horizontal",
            adaptive_height=True,
            spacing=dp(8),
        )
        self._greeting_label = MDLabel(
            text="Hello! 👋",
            font_style="Headline",
            role="medium",
            adaptive_height=True,
        )
        greeting_row.add_widget(self._greeting_label)
        self._content.add_widget(greeting_row)

        # Date subtitle
        self._date_label = MDLabel(
            text=format_date(today(), "long"),
            font_style="Body",
            role="large",
            adaptive_height=True,
            theme_text_color="Secondary",
        )
        self._content.add_widget(self._date_label)

        # ---- Balance card ----
        balance_card = MDCard(
            style="filled",
            padding=[dp(20), dp(20), dp(20), dp(20)],
            md_bg_color=(0.25, 0.31, 0.71, 1),  # Indigo
            size_hint_y=None,
            height=dp(110),
            radius=[dp(16)],
        )
        balance_content = MDBoxLayout(
            orientation="vertical",
            adaptive_height=True,
            spacing=dp(6),
        )
        balance_content.add_widget(MDLabel(
            text="Current Balance",
            font_style="Body",
            role="medium",
            adaptive_height=True,
            theme_text_color="Custom",
            text_color=(1, 1, 1, 0.8),
        ))
        self._balance_label = MDLabel(
            text="₹0.00",
            font_style="Display",
            role="small",
            adaptive_height=True,
            theme_text_color="Custom",
            text_color=(1, 1, 1, 1),
        )
        balance_content.add_widget(self._balance_label)
        balance_card.add_widget(balance_content)
        self._content.add_widget(balance_card)

        # ---- Income / Expense row ----
        ie_row = MDBoxLayout(
            orientation="horizontal",
            adaptive_height=True,
            spacing=dp(12),
        )
        ie_row.add_widget(self._make_stat_card(
            label="Income",
            value_attr="_income_label",
            value="₹0.00",
            icon="arrow-down-circle",
            color=(0.18, 0.72, 0.44, 1),
        ))
        ie_row.add_widget(self._make_stat_card(
            label="Expenses",
            value_attr="_expense_label",
            value="₹0.00",
            icon="arrow-up-circle",
            color=(0.94, 0.33, 0.31, 1),
        ))
        self._content.add_widget(ie_row)

        # ---- Quick actions ----
        self._content.add_widget(MDLabel(
            text="Quick Actions",
            font_style="Title",
            role="medium",
            adaptive_height=True,
        ))
        qa_row = MDBoxLayout(
            orientation="horizontal",
            adaptive_height=True,
            spacing=dp(12),
        )
        add_expense_btn = MDButton(
            style="filled",
            on_release=self._on_add_expense,
        )
        add_expense_btn.add_widget(MDButtonText(text="+ Add Expense"))
        add_income_btn = MDButton(
            style="tonal",
            on_release=self._on_add_income,
        )
        add_income_btn.add_widget(MDButtonText(text="+ Add Income"))
        qa_row.add_widget(add_expense_btn)
        qa_row.add_widget(add_income_btn)
        self._content.add_widget(qa_row)

        # ---- Recent transactions header ----
        self._content.add_widget(MDLabel(
            text="Recent Transactions",
            font_style="Title",
            role="medium",
            adaptive_height=True,
        ))

        # ---- Empty state ----
        self._empty_label = MDLabel(
            text="No transactions yet.\nTap '+ Add Expense' to get started.",
            font_style="Body",
            role="large",
            adaptive_height=True,
            halign="center",
            theme_text_color="Secondary",
        )
        self._content.add_widget(self._empty_label)

        scroll.add_widget(self._content)
        root.add_widget(scroll)
        self.add_widget(root)

    def _make_stat_card(
        self,
        label: str,
        value_attr: str,
        value: str,
        icon: str,
        color: tuple,
    ) -> MDCard:
        """Helper to build a small statistic card."""
        card = MDCard(
            style="outlined",
            padding=[dp(16), dp(14), dp(16), dp(14)],
            size_hint_x=0.5,
            size_hint_y=None,
            height=dp(80),
            radius=[dp(12)],
        )
        inner = MDBoxLayout(orientation="vertical", adaptive_height=True, spacing=dp(4))
        inner.add_widget(MDLabel(
            text=label,
            font_style="Body",
            role="small",
            adaptive_height=True,
            theme_text_color="Secondary",
        ))
        val_label = MDLabel(
            text=value,
            font_style="Title",
            role="medium",
            adaptive_height=True,
            theme_text_color="Custom",
            text_color=color,
        )
        setattr(self, value_attr, val_label)
        inner.add_widget(val_label)
        card.add_widget(inner)
        return card

    # ------------------------------------------------------------------
    # Data refresh
    # ------------------------------------------------------------------

    def refresh(self) -> None:
        """Reload user data and update UI labels."""
        try:
            with get_session() as session:
                repo = UserRepository(session)
                user = repo.get_first_user()
                if user:
                    greeting = f"Hello, {user.name}! 👋"
                    self._greeting_label.text = greeting
        except Exception as exc:
            logger.error("Dashboard refresh error: %s", exc)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_add_expense(self, *args) -> None:
        if self.manager:
            self.manager.current = "transactions"

    def _on_add_income(self, *args) -> None:
        if self.manager:
            self.manager.current = "transactions"

    def on_enter(self, *args) -> None:
        Clock.schedule_once(lambda dt: self.refresh(), 0.1)

