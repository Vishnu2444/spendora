"""
Spendora (Trackz) — Add/Edit Transaction Screen (Flet).

faithfully reproduces the Google Stitch "Trackz - Add Transaction / Entry" screen:
- Top Header with Back button and Title
- Segmented Pill Toggle: Expense vs Income
- Large Display Amount: $0.00 / ₹0.00
- AI Suggested Category badge (auto_awesome)
- Category selector chips (Groceries, Dining, Transport, Utilities, etc.)
- Date Picker and Note / Merchant input fields
- Interactive Numeric Keypad (1-9, ., 0, backspace) for touch entry
- Primary Emerald "Save Transaction" button (check_circle)
"""

from __future__ import annotations

from datetime import date
import logging
from typing import Callable, Optional

import utils.flet_compat
import flet as ft

from config.settings import (
    COLOR_BACKGROUND,
    COLOR_ERROR,
    COLOR_ON_PRIMARY,
    COLOR_ON_SURFACE,
    COLOR_OUTLINE_VARIANT,
    COLOR_PRIMARY,
    COLOR_PRIMARY_CONTAINER,
    COLOR_PRIMARY_FIXED_DIM,
    COLOR_SECONDARY,
    COLOR_SURFACE_CARD,
    COLOR_SURFACE_CONTAINER,
    COLOR_SURFACE_LOW,
    CURRENCY_SYMBOLS,
    DEFAULT_CURRENCY,
)
from config.theme_manager import theme_manager
from database.database import get_session
from database.models import Category, Transaction, TransactionType
from services.category_service import CategoryService
from services.profile_service import ProfileService
from services.transaction_service import TransactionService

logger = logging.getLogger(__name__)


class AddEditTransactionView:
    """Entry form for logging and editing expenses matching Stitch Trackz design."""

    def __init__(self, go_back_fn: Optional[Callable[[], None]] = None) -> None:
        self._transaction_service = TransactionService()
        self._profile_service = ProfileService()
        self._category_service = CategoryService()
        self._go_back = go_back_fn

        self._transaction_id: Optional[int] = None
        self._user_id: Optional[int] = None
        self._page: Optional[ft.Page] = None
        self._selected_type: str = "EXPENSE"
        self._selected_category_id: Optional[int] = None
        self._selected_date: date = date.today()
        self._currency: str = DEFAULT_CURRENCY
        self._amount_str: str = "0.00"

        # UI Controls
        self._title = ft.Text(
            "New Entry",
            size=18,
            weight=ft.FontWeight.W_800,
            color=COLOR_ON_SURFACE,
        )

        # Segmented Type Toggle
        self._expense_pill = ft.Container(
            bgcolor=COLOR_SURFACE_CARD,
            border_radius=20,
            padding=ft.Padding.symmetric(horizontal=24, vertical=8),
            ink=True,
            content=ft.Text("Expense", color=COLOR_ON_SURFACE, size=13, weight=ft.FontWeight.W_700),
            on_click=lambda e: self._set_type("EXPENSE"),
        )
        self._income_pill = ft.Container(
            bgcolor=COLOR_SURFACE_LOW,
            border_radius=20,
            padding=ft.Padding.symmetric(horizontal=24, vertical=8),
            ink=True,
            content=ft.Text("Income", color=COLOR_SECONDARY, size=13, weight=ft.FontWeight.W_500),
            on_click=lambda e: self._set_type("INCOME"),
        )

        # Amount Display (supports both direct typing and keypad tapping)
        self._currency_symbol_text = ft.Text("₹", size=24, weight=ft.FontWeight.W_600, color=COLOR_SECONDARY)
        self._amount_display = ft.TextField(
            value="0.00",
            text_size=36,
            text_style=ft.TextStyle(weight=ft.FontWeight.W_800, color=COLOR_ON_SURFACE),
            text_align=ft.TextAlign.CENTER,
            keyboard_type=ft.KeyboardType.NUMBER,
            border=ft.NoInputBorder() if hasattr(ft, "NoInputBorder") else ft.InputBorder.NONE,
            content_padding=ft.Padding.all(4),
            width=220,
            cursor_color=COLOR_PRIMARY,
            on_change=self._on_amount_typed,
        )

        # AI Suggestion Chip
        self._ai_suggestion_row = ft.Container(
            bgcolor=COLOR_SURFACE_LOW,
            border=ft.Border.all(1, COLOR_PRIMARY_FIXED_DIM),
            border_radius=8,
            padding=ft.Padding.symmetric(horizontal=12, vertical=8),
            visible=False,
            content=ft.Row(
                spacing=8,
                controls=[
                    ft.Icon(ft.Icons.AUTO_AWESOME, color=COLOR_PRIMARY, size=16),
                    ft.Text("AI Suggested: ", color=COLOR_PRIMARY, size=12, weight=ft.FontWeight.W_600),
                    ft.Text("", color=COLOR_ON_SURFACE, size=12, weight=ft.FontWeight.W_700),
                ],
            ),
        )

        # Category Chips Row
        self._category_chips_row = ft.Row(wrap=True, spacing=8, run_spacing=8)

        # Inputs
        self._date_text = ft.Text(str(date.today()), size=14, color=COLOR_ON_SURFACE)
        self._note_field = ft.TextField(
            hint_text="e.g. Whole Foods, Client Lunch, Salary",
            hint_style=ft.TextStyle(color=COLOR_SECONDARY),
            text_style=ft.TextStyle(color=COLOR_ON_SURFACE),
            border_color=COLOR_OUTLINE_VARIANT,
            focused_border_color=COLOR_PRIMARY,
            border_radius=10,
            prefix_icon=ft.Icons.EDIT_NOTE,
            dense=True,
            on_change=self._on_note_change,
        )

        # Error / Message
        self._error_text = ft.Text("", color=COLOR_ERROR, size=12, visible=False)

        # Delete button for edit mode
        self._delete_btn = ft.Container(
            border=ft.Border.all(1, COLOR_ERROR),
            border_radius=12,
            padding=ft.Padding.symmetric(horizontal=12, vertical=6),
            visible=False,
            ink=True,
            on_click=self._on_delete_click,
            content=ft.Row(
                spacing=4,
                tight=True,
                controls=[
                    ft.Icon(ft.Icons.DELETE_OUTLINE, size=16, color=COLOR_ERROR),
                    ft.Text("Delete Entry", size=12, weight=ft.FontWeight.W_600, color=COLOR_ERROR),
                ],
            ),
        )

    def set_page(self, page: ft.Page) -> None:
        self._page = page

    def _set_type(self, txn_type: str) -> None:
        self._selected_type = txn_type
        if txn_type == "EXPENSE":
            self._expense_pill.bgcolor = COLOR_SURFACE_CARD
            self._expense_pill.content.color = COLOR_ON_SURFACE
            self._expense_pill.content.weight = ft.FontWeight.W_700
            self._income_pill.bgcolor = COLOR_SURFACE_LOW
            self._income_pill.content.color = COLOR_SECONDARY
            self._income_pill.content.weight = ft.FontWeight.W_500
        else:
            self._income_pill.bgcolor = COLOR_SURFACE_CARD
            self._income_pill.content.color = COLOR_ON_SURFACE
            self._income_pill.content.weight = ft.FontWeight.W_700
            self._expense_pill.bgcolor = COLOR_SURFACE_LOW
            self._expense_pill.content.color = COLOR_SECONDARY
            self._expense_pill.content.weight = ft.FontWeight.W_500
        try:
            self._expense_pill.update()
            self._income_pill.update()
        except Exception:
            pass

    def _keypad_press(self, val: str) -> None:
        """Handle numeric keypad button clicks."""
        current = self._amount_str
        if val == "C":
            self._amount_str = "0.00"
        elif val == "⌫":
            if len(current) <= 1 or current == "0.00":
                self._amount_str = "0.00"
            else:
                self._amount_str = current[:-1]
        elif val == ".":
            if "." not in current:
                self._amount_str = current + "."
        else:
            if current == "0.00" or current == "0":
                self._amount_str = val
            elif len(current) < 9:
                self._amount_str = current + val

        self._amount_display.value = self._amount_str
        try:
            self._amount_display.update()
        except Exception:
            pass

    def _on_amount_typed(self, e) -> None:
        """Handle direct text input typed with keyboard."""
        raw = self._amount_display.value or ""
        cleaned = "".join(ch for ch in raw if ch.isdigit() or ch == ".")
        self._amount_str = cleaned if cleaned else "0.00"

    def _on_note_change(self, e) -> None:
        """Simple heuristic to suggest category based on note."""
        note = (self._note_field.value or "").lower()
        if not note:
            self._ai_suggestion_row.visible = False
            try:
                self._ai_suggestion_row.update()
            except Exception:
                pass
            return

        suggested = None
        if any(w in note for w in ["food", "lunch", "dinner", "burger", "pizza", "coffee", "restaurant", "cafe", "sushi"]):
            suggested = "Food"
        elif any(w in note for w in ["grocery", "supermarket", "whole foods", "milk", "vegetables"]):
            suggested = "Groceries"
        elif any(w in note for w in ["uber", "ola", "cab", "petrol", "fuel", "flight", "train", "metro", "bus"]):
            suggested = "Transportation"
        elif any(w in note for w in ["aws", "github", "software", "chatgpt", "gemini", "domain"]):
            suggested = "Software"
        elif any(w in note for w in ["salary", "payout", "client", "invoice"]):
            suggested = "Salary"

        if suggested:
            self._ai_suggestion_row.content.controls[2].value = suggested
            self._ai_suggestion_row.visible = True
            # Auto-match category if possible
            for cat in self._categories:
                if suggested.lower() in cat.name.lower():
                    self._select_category(cat.id)
                    break
        else:
            self._ai_suggestion_row.visible = False
        try:
            self._ai_suggestion_row.update()
        except Exception:
            pass

    def _select_category(self, cat_id: int) -> None:
        self._selected_category_id = cat_id
        for chip in self._category_chips_row.controls:
            is_sel = chip.data == cat_id
            chip.bgcolor = COLOR_PRIMARY_CONTAINER if is_sel else COLOR_SURFACE_CARD
            chip.content.controls[1].color = COLOR_ON_PRIMARY if is_sel else COLOR_ON_SURFACE
            try:
                chip.update()
            except Exception:
                pass

    def build(self, transaction: Optional[Transaction] = None, initial_type: str = "EXPENSE") -> ft.Control:
        """Construct Flet layout for Entry / AddEditTransaction."""
        # Populate categories and form data
        self.load_transaction(transaction, initial_type=initial_type)
        is_dark = theme_manager.is_dark()
        card_bg = "#151D30" if is_dark else COLOR_SURFACE_CARD
        border_col = "#222E48" if is_dark else COLOR_OUTLINE_VARIANT
        input_bg = "#0F1726" if is_dark else COLOR_SURFACE_LOW
        text_col = "#FFFFFF" if is_dark else COLOR_ON_SURFACE
        sub_col = "#94A3B8" if is_dark else COLOR_SECONDARY
        primary_col = "#8B5CF6" if is_dark else COLOR_PRIMARY

        self._title.color = text_col
        self._currency_symbol_text.color = sub_col
        self._amount_display.text_style = ft.TextStyle(weight=ft.FontWeight.W_800, color=text_col)
        self._date_text.color = text_col
        self._note_field.bgcolor = input_bg
        self._note_field.text_style = ft.TextStyle(color=text_col)
        self._note_field.border_color = border_col

        # Top Bar
        top_bar = ft.Container(
            bgcolor=card_bg,
            border=ft.Border.only(bottom=ft.BorderSide(1, border_col)),
            padding=ft.Padding.symmetric(horizontal=16, vertical=12),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.IconButton(
                        icon=ft.Icons.ARROW_BACK,
                        icon_color=primary_col,
                        on_click=lambda e: self._go_back(),
                    ),
                    self._title,
                    self._delete_btn,
                ],
            ),
        )

        # Toggle Card + Amount Display (Stitch)
        amount_card = ft.Container(
            bgcolor=card_bg,
            border=ft.Border.all(1, border_col),
            border_radius=16,
            padding=ft.Padding.symmetric(horizontal=20, vertical=16),
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=14,
                controls=[
                    # Pill toggle
                    ft.Container(
                        bgcolor=input_bg,
                        border_radius=24,
                        padding=ft.Padding.all(4),
                        content=ft.Row(
                            alignment=ft.MainAxisAlignment.CENTER,
                            spacing=4,
                            controls=[self._expense_pill, self._income_pill],
                        ),
                    ),
                    # Large Amount Display
                    ft.Row(
                        alignment=ft.MainAxisAlignment.CENTER,
                        vertical_alignment=ft.CrossAxisAlignment.BASELINE,
                        spacing=4,
                        controls=[
                            self._currency_symbol_text,
                            self._amount_display,
                        ],
                    ),
                ],
            ),
        )

        # Keypad Grid (Stitch 3-column touch keypad)
        def _make_key(val: str) -> ft.Container:
            return ft.Container(
                bgcolor=input_bg,
                border_radius=12,
                height=48,
                expand=True,
                alignment=ft.Alignment.CENTER,
                ink=True,
                content=ft.Text(val, size=20, weight=ft.FontWeight.W_600, color=text_col),
                on_click=lambda e, v=val: self._keypad_press(v),
            )

        keypad = ft.Container(
            bgcolor=card_bg,
            border=ft.Border.all(1, border_col),
            border_radius=16,
            padding=ft.Padding.all(14),
            content=ft.Column(
                spacing=8,
                controls=[
                    ft.Row(spacing=8, controls=[_make_key("1"), _make_key("2"), _make_key("3")]),
                    ft.Row(spacing=8, controls=[_make_key("4"), _make_key("5"), _make_key("6")]),
                    ft.Row(spacing=8, controls=[_make_key("7"), _make_key("8"), _make_key("9")]),
                    ft.Row(spacing=8, controls=[_make_key("."), _make_key("0"), _make_key("⌫")]),
                ],
            ),
        )

        # Date Picker Row
        def _on_date_picked(e):
            if date_picker.value:
                val = date_picker.value
                self._selected_date = val.date() if hasattr(val, "date") else val
                self._date_text.value = str(self._selected_date)
                try:
                    self._date_text.update()
                except Exception:
                    pass

        date_picker = ft.DatePicker(
            value=self._selected_date,
            on_change=_on_date_picked,
        )

        def _open_date_picker(e):
            if self._page:
                self._page.overlay.append(date_picker)
                date_picker.open = True
                try:
                    self._page.update()
                except Exception:
                    pass

        date_row = ft.Container(
            padding=ft.Padding.symmetric(vertical=6),
            ink=True,
            on_click=_open_date_picker,
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Row(
                        spacing=8,
                        tight=True,
                        controls=[
                            ft.Icon(ft.Icons.CALENDAR_MONTH, color=primary_col, size=18),
                            ft.Text("DATE", size=11, weight=ft.FontWeight.W_700, color=sub_col),
                        ],
                    ),
                    ft.Row(
                        spacing=4,
                        tight=True,
                        controls=[
                            self._date_text,
                            ft.Icon(ft.Icons.ARROW_DROP_DOWN, color=sub_col, size=18),
                        ],
                    ),
                ],
            ),
        )

        # Details Card (Categories + Date + Note)
        details_card = ft.Container(
            bgcolor=card_bg,
            border=ft.Border.all(1, border_col),
            border_radius=16,
            padding=ft.Padding.all(16),
            content=ft.Column(
                spacing=14,
                controls=[
                    ft.Text("CATEGORY", color=sub_col, size=11, weight=ft.FontWeight.W_700),
                    self._ai_suggestion_row,
                    self._category_chips_row,
                    ft.Divider(color=border_col),
                    date_row,
                    ft.Divider(color=border_col),
                    ft.Text("NOTE / MERCHANT", color=sub_col, size=11, weight=ft.FontWeight.W_700),
                    self._note_field,
                    self._error_text,
                ],
            ),
        )

        # Save Button
        save_btn = ft.Container(
            height=52,
            border_radius=14,
            bgcolor=primary_col,
            alignment=ft.Alignment.CENTER,
            ink=True,
            on_click=self._on_save_click,
            content=ft.Row(
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=8,
                controls=[
                    ft.Text("Save Transaction", size=16, weight=ft.FontWeight.W_700, color="#FFFFFF"),
                    ft.Icon(ft.Icons.CHECK_CIRCLE, size=20, color="#FFFFFF"),
                ],
            ),
        )

        # Main scrollable body — same pattern as Dashboard (ft.ListView expand=True works)
        scroll_content = ft.ListView(
            expand=True,
            spacing=16,
            padding=ft.Padding.symmetric(horizontal=16, vertical=12),
            controls=[
                amount_card,
                keypad,
                details_card,
                save_btn,
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
        """Refresh form state and category options."""
        self.load_transaction(None)

    def load_transaction(self, transaction: Optional[Transaction] = None, initial_type: str = "EXPENSE") -> None:
        """Reset form or load an existing transaction for editing."""
        user = self._profile_service.get_current_user()
        user_id = user.id if user else 1
        self._currency = user.currency if user and user.currency else DEFAULT_CURRENCY
        self._currency_symbol_text.value = CURRENCY_SYMBOLS.get(self._currency, "$")

        # Load categories from CategoryService
        self._categories = self._category_service.list_categories(user_id=user_id)

        # Build category chips
        self._category_chips_row.controls.clear()
        for cat in self._categories:
            is_selected = False
            from components.transaction_card import _resolve_icon
            chip = ft.Container(
                bgcolor=COLOR_SURFACE_CARD,
                border=ft.Border.all(1, COLOR_OUTLINE_VARIANT),
                border_radius=20,
                padding=ft.Padding.symmetric(horizontal=12, vertical=6),
                ink=True,
                data=cat.id,
                content=ft.Row(
                    spacing=6,
                    tight=True,
                    controls=[
                        ft.Icon(_resolve_icon(cat.icon or "payments"), size=14, color=COLOR_PRIMARY),
                        ft.Text(cat.name, size=12, color=COLOR_ON_SURFACE, weight=ft.FontWeight.W_500),
                    ],
                ),
                on_click=lambda e, cid=cat.id: self._select_category(cid),
            )
            self._category_chips_row.controls.append(chip)

        if transaction:
            self._transaction_id = transaction.id
            self._title.value = "Edit Entry"
            self._delete_btn.visible = True
            self._set_type(transaction.transaction_type.value)
            self._amount_str = f"{transaction.amount_paise / 100:.2f}"
            self._amount_display.value = self._amount_str
            self._note_field.value = transaction.description or ""
            self._selected_date = transaction.transaction_date
            self._date_text.value = str(self._selected_date)
            if transaction.category_id:
                self._select_category(transaction.category_id)
        else:
            self._transaction_id = None
            is_income = (initial_type.upper() == "INCOME")
            self._title.value = "New Income" if is_income else "New Expense"
            self._delete_btn.visible = False
            self._set_type("INCOME" if is_income else "EXPENSE")
            self._amount_str = "0.00"
            self._amount_display.value = "0.00"
            self._note_field.value = ""
            self._selected_date = date.today()
            self._date_text.value = str(self._selected_date)
            if self._categories:
                self._select_category(self._categories[0].id)

    def _on_save_click(self, e) -> None:
        """Validate and commit transaction to database."""
        try:
            val = float(self._amount_str)
            if val <= 0:
                self._error_text.value = "Please enter an amount greater than 0"
                self._error_text.visible = True
                try:
                    self._error_text.update()
                except Exception:
                    pass
                return
        except ValueError:
            self._error_text.value = "Invalid amount format"
            self._error_text.visible = True
            try:
                self._error_text.update()
            except Exception:
                pass
            return

        amount_str = f"{val:.2f}"
        desc = (self._note_field.value or "").strip()
        user = self._profile_service.get_current_user()
        user_id = user.id if user else (self._user_id or 1)

        try:
            if self._transaction_id:
                self._transaction_service.update_transaction(
                    transaction_id=self._transaction_id,
                    user_id=user_id,
                    transaction_type=self._selected_type,
                    amount_str=amount_str,
                    category_id=self._selected_category_id,
                    description=desc,
                    transaction_date=self._selected_date,
                    currency=self._currency,
                )
            else:
                self._transaction_service.create_transaction(
                    user_id=user_id,
                    transaction_type=self._selected_type,
                    amount_str=amount_str,
                    category_id=self._selected_category_id,
                    description=desc,
                    transaction_date=self._selected_date,
                    currency=self._currency,
                )
            if self._page:
                self._page.snack_bar = ft.SnackBar(
                    ft.Text(f"{'Updated' if self._transaction_id else 'Saved'} transaction successfully!", color="#FFFFFF"),
                    bgcolor="#10B981",
                    duration=2000,
                )
                self._page.snack_bar.open = True
                try:
                    self._page.update()
                except Exception:
                    pass
            if self._go_back:
                self._go_back()
        except Exception as ex:
            logger.error("Failed to save transaction: %s", ex, exc_info=True)
            self._error_text.value = f"Error: {ex}"
            self._error_text.visible = True
            try:
                self._error_text.update()
            except Exception:
                pass

    def _on_delete_click(self, e) -> None:
        if not self._transaction_id:
            return

        def _confirm_delete(ev):
            try:
                user = self._profile_service.get_current_user()
                user_id = user.id if user else (self._user_id or 1)
                self._transaction_service.delete_transaction(self._transaction_id, user_id=user_id)
                if hasattr(dialog, "open"):
                    dialog.open = False
                if self._page:
                    try:
                        self._page.update()
                    except Exception:
                        pass
                if self._go_back:
                    self._go_back()
            except Exception as ex:
                logger.error("Failed to delete transaction: %s", ex, exc_info=True)
                self._error_text.value = f"Error: {ex}"
                self._error_text.visible = True
                try:
                    self._error_text.update()
                except Exception:
                    pass

        def _cancel_delete(ev):
            dialog.open = False
            if self._page:
                try:
                    self._page.update()
                except Exception:
                    pass

        dialog = ft.AlertDialog(
            title=ft.Text("Delete Transaction", weight=ft.FontWeight.W_700),
            content=ft.Text("Are you sure you want to delete this transaction? This action cannot be undone."),
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
