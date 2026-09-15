"""
Spendora — Add/Edit Transaction Screen.

Full-screen form for creating or editing a financial transaction.
Registered in the ROOT ScreenManager (not the inner tab ScreenManager)
so it gets a full-screen slide transition.

Features:
- Income/Expense type toggle
- Amount input with currency symbol
- Category and subcategory selection (dropdown)
- Date picker
- Description and notes fields
- Delete button (edit mode only)
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Optional

from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.scrollview import ScrollView
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDButton, MDButtonText, MDButtonIcon
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.screen import MDScreen
from kivymd.uix.textfield import (
    MDTextField,
    MDTextFieldHintText,
    MDTextFieldHelperText,
)
from kivymd.uix.menu import MDDropdownMenu

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
    CURRENCY_SYMBOLS,
)
from database.database import get_session
from database.repositories.category_repository import CategoryRepository
from services.transaction_service import TransactionService
from utils.formatting import format_paise_as_decimal, format_date

logger = logging.getLogger(__name__)


class AddEditTransactionScreen(MDScreen):
    """Full-screen form for adding or editing a transaction."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.name = "add_edit_transaction"
        self._transaction_service = TransactionService()
        self._user_id: Optional[int] = None
        self._transaction_id: Optional[int] = None
        self._selected_type = "EXPENSE"
        self._selected_category_id: Optional[int] = None
        self._selected_subcategory_id: Optional[int] = None
        self._selected_date: date = date.today()
        self._categories = []
        self._subcategories = []
        self._category_menu: Optional[MDDropdownMenu] = None
        self._subcategory_menu: Optional[MDDropdownMenu] = None
        self._is_edit_mode = False
        self._build_ui()

    def setup(
        self,
        user_id: int,
        transaction_id: Optional[int] = None,
    ) -> None:
        """Configure the screen for add or edit mode."""
        self._user_id = user_id
        self._transaction_id = transaction_id
        self._is_edit_mode = transaction_id is not None

        # Load categories.
        self._load_categories()

        if self._is_edit_mode:
            self._title_label.text = "Edit Transaction"
            self._delete_btn.opacity = 1
            self._delete_btn.disabled = False
            self._load_existing_transaction()
        else:
            self._title_label.text = "Add Transaction"
            self._delete_btn.opacity = 0
            self._delete_btn.disabled = True
            self._reset_form()

    def _build_ui(self) -> None:
        root = MDBoxLayout(orientation="vertical", md_bg_color=APP_BG_DARK)

        # --- Top bar ---
        top_bar = MDBoxLayout(
            orientation="horizontal",
            adaptive_height=True,
            padding=[dp(8), dp(12), dp(8), dp(4)],
            spacing=dp(8),
        )

        back_btn = MDButton(style="text", on_release=self._go_back)
        back_btn.add_widget(MDButtonText(text="← Back"))
        top_bar.add_widget(back_btn)

        self._title_label = MDLabel(
            text="Add Transaction",
            font_style="Headline",
            role="small",
            adaptive_height=True,
            theme_text_color="Custom",
            text_color=APP_TEXT,
        )
        top_bar.add_widget(self._title_label)

        top_bar.add_widget(MDBoxLayout())  # spacer

        self._delete_btn = MDButton(
            style="text",
            on_release=self._confirm_delete,
            opacity=0,
            disabled=True,
        )
        self._delete_btn.add_widget(MDButtonText(text="Delete", theme_text_color="Custom", text_color=APP_DANGER))
        top_bar.add_widget(self._delete_btn)

        root.add_widget(top_bar)

        # --- Scrollable form ---
        scroll = ScrollView(do_scroll_x=False)
        self._form = MDBoxLayout(
            orientation="vertical",
            adaptive_height=True,
            padding=[dp(20), dp(10), dp(20), dp(24)],
            spacing=dp(16),
        )

        # --- Type toggle ---
        type_label = MDLabel(
            text="Transaction Type",
            font_style="Label",
            role="large",
            adaptive_height=True,
            theme_text_color="Custom",
            text_color=APP_MUTED_TEXT,
        )
        self._form.add_widget(type_label)

        type_row = MDBoxLayout(
            orientation="horizontal",
            adaptive_height=True,
            spacing=dp(12),
        )
        self._expense_btn = MDButton(
            style="filled",
            on_release=lambda *_: self._set_type("EXPENSE"),
            size_hint_x=0.5,
        )
        self._expense_btn.add_widget(MDButtonText(text="Expense"))
        self._expense_btn_text = self._expense_btn.children[0]

        self._income_btn = MDButton(
            style="tonal",
            on_release=lambda *_: self._set_type("INCOME"),
            size_hint_x=0.5,
        )
        self._income_btn.add_widget(MDButtonText(text="Income"))
        self._income_btn_text = self._income_btn.children[0]

        type_row.add_widget(self._expense_btn)
        type_row.add_widget(self._income_btn)
        self._form.add_widget(type_row)

        # --- Amount field ---
        currency_sym = CURRENCY_SYMBOLS.get(DEFAULT_CURRENCY, "₹")
        self._amount_field = MDTextField(
            MDTextFieldHintText(text=f"Amount ({currency_sym})"),
            MDTextFieldHelperText(text="Enter amount (e.g., 250.50)", mode="on_focus"),
            mode="outlined",
        )
        self._amount_field.input_filter = "float"
        self._form.add_widget(self._amount_field)

        # --- Category dropdown ---
        cat_label = MDLabel(
            text="Category",
            font_style="Label",
            role="large",
            adaptive_height=True,
            theme_text_color="Custom",
            text_color=APP_MUTED_TEXT,
        )
        self._form.add_widget(cat_label)

        self._category_btn = MDButton(
            style="outlined",
            on_release=self._show_category_menu,
            size_hint_x=1,
        )
        self._category_btn_text = MDButtonText(text="Select Category")
        self._category_btn.add_widget(self._category_btn_text)
        self._form.add_widget(self._category_btn)

        # --- Subcategory dropdown ---
        self._subcategory_label = MDLabel(
            text="Subcategory",
            font_style="Label",
            role="large",
            adaptive_height=True,
            theme_text_color="Custom",
            text_color=APP_MUTED_TEXT,
        )
        self._form.add_widget(self._subcategory_label)

        self._subcategory_btn = MDButton(
            style="outlined",
            on_release=self._show_subcategory_menu,
            size_hint_x=1,
        )
        self._subcategory_btn_text = MDButtonText(text="Select Subcategory")
        self._subcategory_btn.add_widget(self._subcategory_btn_text)
        self._form.add_widget(self._subcategory_btn)

        # --- Date field ---
        date_label = MDLabel(
            text="Date",
            font_style="Label",
            role="large",
            adaptive_height=True,
            theme_text_color="Custom",
            text_color=APP_MUTED_TEXT,
        )
        self._form.add_widget(date_label)

        date_row = MDBoxLayout(
            orientation="horizontal",
            adaptive_height=True,
            spacing=dp(8),
        )
        self._date_display = MDLabel(
            text=format_date(date.today(), style="display"),
            font_style="Body",
            role="large",
            adaptive_height=True,
            theme_text_color="Custom",
            text_color=APP_TEXT,
        )
        date_row.add_widget(self._date_display)

        today_btn = MDButton(
            style="text",
            on_release=lambda *_: self._set_date(date.today()),
        )
        today_btn.add_widget(MDButtonText(text="Today"))
        date_row.add_widget(today_btn)

        prev_btn = MDButton(
            style="text",
            on_release=self._date_prev,
        )
        prev_btn.add_widget(MDButtonText(text="◀"))
        date_row.add_widget(prev_btn)

        next_btn = MDButton(
            style="text",
            on_release=self._date_next,
        )
        next_btn.add_widget(MDButtonText(text="▶"))
        date_row.add_widget(next_btn)

        self._form.add_widget(date_row)

        # --- Description ---
        self._desc_field = MDTextField(
            MDTextFieldHintText(text="Description"),
            MDTextFieldHelperText(text="Short description (optional)", mode="on_focus"),
            mode="outlined",
        )
        self._form.add_widget(self._desc_field)

        # --- Notes ---
        self._notes_field = MDTextField(
            MDTextFieldHintText(text="Notes"),
            MDTextFieldHelperText(text="Additional notes (optional)", mode="on_focus"),
            mode="outlined",
            multiline=True,
        )
        self._form.add_widget(self._notes_field)

        # --- Save button ---
        save_row = MDBoxLayout(
            orientation="horizontal",
            adaptive_height=True,
            padding=[0, dp(12), 0, 0],
        )
        self._save_btn = MDButton(
            style="filled",
            on_release=self._save_transaction,
            size_hint_x=1,
        )
        self._save_btn.add_widget(MDButtonText(text="Save Transaction"))
        save_row.add_widget(self._save_btn)
        self._form.add_widget(save_row)

        # --- Status message ---
        self._status_label = MDLabel(
            text="",
            font_style="Body",
            role="medium",
            adaptive_height=True,
            halign="center",
            theme_text_color="Custom",
            text_color=APP_DANGER,
        )
        self._form.add_widget(self._status_label)

        scroll.add_widget(self._form)
        root.add_widget(scroll)
        self.add_widget(root)

    # ------------------------------------------------------------------
    # Type toggle
    # ------------------------------------------------------------------

    def _set_type(self, txn_type: str) -> None:
        self._selected_type = txn_type
        if txn_type == "EXPENSE":
            self._expense_btn.style = "filled"
            self._income_btn.style = "tonal"
        else:
            self._income_btn.style = "filled"
            self._expense_btn.style = "tonal"

    # ------------------------------------------------------------------
    # Date navigation
    # ------------------------------------------------------------------

    def _set_date(self, d: date) -> None:
        self._selected_date = d
        self._date_display.text = format_date(d, style="display")

    def _date_prev(self, *args) -> None:
        from datetime import timedelta
        self._set_date(self._selected_date - timedelta(days=1))

    def _date_next(self, *args) -> None:
        from datetime import timedelta
        self._set_date(self._selected_date + timedelta(days=1))

    # ------------------------------------------------------------------
    # Category / subcategory
    # ------------------------------------------------------------------

    def _load_categories(self) -> None:
        """Fetch user's categories from DB."""
        if self._user_id is None:
            return
        try:
            with get_session() as session:
                repo = CategoryRepository(session)
                self._categories = repo.list_for_user(self._user_id)
                for cat in self._categories:
                    session.expunge(cat)
        except Exception as exc:
            logger.error("Failed to load categories: %s", exc)
            self._categories = []

    def _show_category_menu(self, *args) -> None:
        items = [
            {
                "text": cat.name,
                "on_release": lambda c=cat: self._on_category_selected(c),
            }
            for cat in self._categories
        ]
        # Add "None" option.
        items.insert(0, {
            "text": "No Category",
            "on_release": lambda: self._on_category_selected(None),
        })

        if self._category_menu:
            self._category_menu.dismiss()

        self._category_menu = MDDropdownMenu(
            caller=self._category_btn,
            items=items,
        )
        self._category_menu.open()

    def _on_category_selected(self, category) -> None:
        if self._category_menu:
            self._category_menu.dismiss()
        if category is None:
            self._selected_category_id = None
            self._category_btn_text.text = "No Category"
            self._subcategories = []
            self._selected_subcategory_id = None
            self._subcategory_btn_text.text = "Select Subcategory"
        else:
            self._selected_category_id = category.id
            self._category_btn_text.text = category.name
            # Load subcategories for this category.
            self._load_subcategories(category.id)
            self._selected_subcategory_id = None
            self._subcategory_btn_text.text = "Select Subcategory"

    def _load_subcategories(self, category_id: int) -> None:
        """Load subcategories for a given category."""
        try:
            with get_session() as session:
                repo = CategoryRepository(session)
                self._subcategories = repo.list_subcategories(category_id)
                for sub in self._subcategories:
                    session.expunge(sub)
        except Exception as exc:
            logger.error("Failed to load subcategories: %s", exc)
            self._subcategories = []

    def _show_subcategory_menu(self, *args) -> None:
        if not self._subcategories:
            return
        items = [
            {
                "text": sub.name,
                "on_release": lambda s=sub: self._on_subcategory_selected(s),
            }
            for sub in self._subcategories
        ]
        items.insert(0, {
            "text": "No Subcategory",
            "on_release": lambda: self._on_subcategory_selected(None),
        })

        if self._subcategory_menu:
            self._subcategory_menu.dismiss()

        self._subcategory_menu = MDDropdownMenu(
            caller=self._subcategory_btn,
            items=items,
        )
        self._subcategory_menu.open()

    def _on_subcategory_selected(self, subcategory) -> None:
        if self._subcategory_menu:
            self._subcategory_menu.dismiss()
        if subcategory is None:
            self._selected_subcategory_id = None
            self._subcategory_btn_text.text = "No Subcategory"
        else:
            self._selected_subcategory_id = subcategory.id
            self._subcategory_btn_text.text = subcategory.name

    # ------------------------------------------------------------------
    # Load existing transaction (edit mode)
    # ------------------------------------------------------------------

    def _load_existing_transaction(self) -> None:
        """Populate form fields from an existing transaction."""
        if self._transaction_id is None:
            return
        try:
            txn = self._transaction_service.get_transaction(self._transaction_id)
            if txn is None:
                self._status_label.text = "Transaction not found."
                return

            self._set_type(txn.transaction_type.value)

            # Amount.
            self._amount_field.text = format_paise_as_decimal(txn.amount_paise)

            # Category.
            if txn.category_id:
                self._selected_category_id = txn.category_id
                # Find category name.
                for cat in self._categories:
                    if cat.id == txn.category_id:
                        self._category_btn_text.text = cat.name
                        self._load_subcategories(cat.id)
                        break
            else:
                self._selected_category_id = None
                self._category_btn_text.text = "No Category"

            # Subcategory.
            if txn.subcategory_id:
                self._selected_subcategory_id = txn.subcategory_id
                for sub in self._subcategories:
                    if sub.id == txn.subcategory_id:
                        self._subcategory_btn_text.text = sub.name
                        break
            else:
                self._selected_subcategory_id = None
                self._subcategory_btn_text.text = "Select Subcategory"

            # Date.
            self._set_date(txn.transaction_date)

            # Description and notes.
            self._desc_field.text = txn.description or ""
            self._notes_field.text = txn.notes or ""

        except Exception as exc:
            logger.error("Failed to load transaction: %s", exc)
            self._status_label.text = f"Error: {exc}"

    # ------------------------------------------------------------------
    # Reset form
    # ------------------------------------------------------------------

    def _reset_form(self) -> None:
        """Clear all form fields for add mode."""
        self._set_type("EXPENSE")
        self._amount_field.text = ""
        self._selected_category_id = None
        self._category_btn_text.text = "Select Category"
        self._selected_subcategory_id = None
        self._subcategory_btn_text.text = "Select Subcategory"
        self._subcategories = []
        self._set_date(date.today())
        self._desc_field.text = ""
        self._notes_field.text = ""
        self._status_label.text = ""

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def _save_transaction(self, *args) -> None:
        """Validate and save the transaction."""
        self._status_label.text = ""
        amount_text = self._amount_field.text.strip()
        if not amount_text:
            self._status_label.text = "Please enter an amount."
            return

        try:
            if self._is_edit_mode and self._transaction_id is not None:
                self._transaction_service.update_transaction(
                    transaction_id=self._transaction_id,
                    user_id=self._user_id,
                    transaction_type=self._selected_type,
                    amount_str=amount_text,
                    transaction_date=self._selected_date,
                    category_id=self._selected_category_id,
                    subcategory_id=self._selected_subcategory_id,
                    description=self._desc_field.text or None,
                    notes=self._notes_field.text or None,
                    clear_category=self._selected_category_id is None,
                    clear_subcategory=self._selected_subcategory_id is None,
                )
                self._status_label.text_color = APP_SUCCESS
                self._status_label.text = "Transaction updated!"
            else:
                self._transaction_service.create_transaction(
                    user_id=self._user_id,
                    transaction_type=self._selected_type,
                    amount_str=amount_text,
                    transaction_date=self._selected_date,
                    category_id=self._selected_category_id,
                    subcategory_id=self._selected_subcategory_id,
                    description=self._desc_field.text or None,
                    notes=self._notes_field.text or None,
                )
                self._status_label.text_color = APP_SUCCESS
                self._status_label.text = "Transaction saved!"

            # Go back after a brief delay.
            Clock.schedule_once(lambda dt: self._go_back(), 0.6)

        except ValueError as exc:
            self._status_label.text_color = APP_DANGER
            self._status_label.text = str(exc)
        except Exception as exc:
            logger.error("Failed to save transaction: %s", exc)
            self._status_label.text_color = APP_DANGER
            self._status_label.text = f"Error: {exc}"

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    def _confirm_delete(self, *args) -> None:
        """Show delete confirmation. In this phase, delete directly."""
        if not self._is_edit_mode or self._transaction_id is None:
            return
        try:
            self._transaction_service.delete_transaction(
                self._transaction_id, self._user_id
            )
            self._status_label.text_color = APP_SUCCESS
            self._status_label.text = "Transaction deleted."
            Clock.schedule_once(lambda dt: self._go_back(), 0.6)
        except ValueError as exc:
            self._status_label.text_color = APP_DANGER
            self._status_label.text = str(exc)
        except Exception as exc:
            logger.error("Failed to delete transaction: %s", exc)
            self._status_label.text_color = APP_DANGER
            self._status_label.text = f"Error: {exc}"

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _go_back(self, *args) -> None:
        """Navigate back to the main screen."""
        app = self._get_app()
        if app and app.root:
            app.root.current = "main"

    @staticmethod
    def _get_app():
        from kivymd.app import MDApp
        return MDApp.get_running_app()
