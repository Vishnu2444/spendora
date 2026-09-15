"""
Spendora — Personalization Screen.

Customization and settings center:
- Category & subcategory management (create, rename, customize color/icon, delete)
- Profile management (name, monthly income target, fixed expenses baseline)
- Currency configuration (INR, USD, EUR, GBP)
"""

from __future__ import annotations

import logging
from typing import Optional

from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.scrollview import ScrollView
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDButton, MDButtonText
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.screen import MDScreen
from kivymd.uix.textfield import MDTextField, MDTextFieldHintText, MDTextFieldHelperText

from components.category_management_card import CategoryManagementCard
from components.color_picker_row import ColorPickerRow
from config.settings import (
    APP_ACCENT,
    APP_BG_CARD,
    APP_BG_DARK,
    APP_DANGER,
    APP_MUTED_TEXT,
    APP_SUCCESS,
    APP_TEXT,
    CURRENCY_SYMBOLS,
    DEFAULT_CURRENCY,
)
from database.models import Category, User
from services.category_service import CategoryService
from services.profile_service import ProfileService
from utils.formatting import format_paise_as_decimal

logger = logging.getLogger(__name__)


class PersonalizationScreen(MDScreen):
    """Personalization and application settings screen."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.name = "personalization"
        self._category_service = CategoryService()
        self._profile_service = ProfileService()
        self._user: Optional[User] = None
        self._active_tab = "categories"  # "categories" or "profile"

        # Creator / Editor state
        self._new_cat_color = "#4ECDC4"
        self._new_cat_icon = "tag"
        self._editing_cat_id: Optional[int] = None

        self._build_ui()

    def _build_ui(self) -> None:
        root = MDBoxLayout(orientation="vertical", md_bg_color=APP_BG_DARK)

        # --- Top Header ---
        top_bar = MDBoxLayout(
            orientation="horizontal",
            adaptive_height=True,
            padding=[dp(18), dp(16), dp(18), dp(8)],
            spacing=dp(8),
        )
        top_bar.add_widget(
            MDLabel(
                text="Personalization",
                font_style="Headline",
                role="small",
                adaptive_height=True,
                theme_text_color="Custom",
                text_color=APP_TEXT,
            )
        )
        root.add_widget(top_bar)

        # --- Segmented Section Switcher ---
        tab_row = MDBoxLayout(
            orientation="horizontal",
            adaptive_height=True,
            spacing=dp(12),
            padding=[dp(16), dp(4), dp(16), dp(8)],
        )

        self._tab_cat_btn = MDButton(
            style="filled",
            size_hint_x=0.5,
            on_release=lambda *_: self._switch_section("categories"),
        )
        self._tab_cat_btn.add_widget(MDButtonText(text="Categories"))

        self._tab_prof_btn = MDButton(
            style="tonal",
            size_hint_x=0.5,
            on_release=lambda *_: self._switch_section("profile"),
        )
        self._tab_prof_btn.add_widget(MDButtonText(text="Profile & Settings"))

        tab_row.add_widget(self._tab_cat_btn)
        tab_row.add_widget(self._tab_prof_btn)
        root.add_widget(tab_row)

        # --- Scrollable Body ---
        scroll = ScrollView(do_scroll_x=False)
        self._body = MDBoxLayout(
            orientation="vertical",
            adaptive_height=True,
            padding=[dp(16), dp(8), dp(16), dp(24)],
            spacing=dp(12),
        )
        scroll.add_widget(self._body)
        root.add_widget(scroll)

        self.add_widget(root)

    # ------------------------------------------------------------------
    # Section Switching
    # ------------------------------------------------------------------

    def _switch_section(self, section: str) -> None:
        self._active_tab = section
        self._tab_cat_btn.style = "filled" if section == "categories" else "tonal"
        self._tab_prof_btn.style = "filled" if section == "profile" else "tonal"
        self.refresh()

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    def refresh(self) -> None:
        """Reload data for the active section."""
        self._user = self._profile_service.get_current_user()
        if not self._user:
            return

        self._body.clear_widgets()

        if self._active_tab == "categories":
            self._render_categories_tab()
        else:
            self._render_profile_tab()

    def on_enter(self, *args) -> None:
        Clock.schedule_once(lambda dt: self.refresh(), 0.1)

    # ------------------------------------------------------------------
    # Categories Tab
    # ------------------------------------------------------------------

    def _render_categories_tab(self) -> None:
        # Header action: "+ Add Category"
        action_row = MDBoxLayout(orientation="horizontal", adaptive_height=True)
        action_row.add_widget(
            MDLabel(
                text="Your Expense Categories",
                font_style="Title",
                role="medium",
                adaptive_height=True,
                theme_text_color="Custom",
                text_color=APP_TEXT,
                pos_hint={"center_y": 0.5},
            )
        )
        action_row.add_widget(MDBoxLayout())  # Spacer

        add_cat_btn = MDButton(style="filled", on_release=self._toggle_creator)
        add_cat_btn.add_widget(MDButtonText(text="+ New Category"))
        action_row.add_widget(add_cat_btn)
        self._body.add_widget(action_row)

        # Inline Creator / Editor Card (hidden by default)
        self._creator_card = self._build_category_creator_card()
        self._body.add_widget(self._creator_card)

        # Inline Add Subcategory Card (hidden by default)
        self._sub_creator_card = self._build_subcategory_creator_card()
        self._body.add_widget(self._sub_creator_card)

        # Status feedback label
        self._cat_status_lbl = MDLabel(
            text="",
            font_style="Body",
            role="small",
            adaptive_height=True,
            theme_text_color="Custom",
            text_color=APP_SUCCESS,
        )
        self._body.add_widget(self._cat_status_lbl)

        # List of Categories
        categories = self._category_service.list_categories(self._user.id)
        if not categories:
            empty_card = MDCard(
                style="filled",
                md_bg_color=APP_BG_CARD,
                radius=[dp(14)],
                padding=[dp(16), dp(24), dp(16), dp(24)],
                size_hint_y=None,
                height=dp(80),
            )
            empty_card.add_widget(
                MDLabel(
                    text="No active categories. Tap '+ New Category' to create one.",
                    halign="center",
                    theme_text_color="Custom",
                    text_color=APP_MUTED_TEXT,
                    font_style="Body",
                    role="medium",
                )
            )
            self._body.add_widget(empty_card)
            return

        for cat in categories:
            card = CategoryManagementCard(
                category=cat,
                on_edit=self._open_edit_category,
                on_delete=self._confirm_delete_category,
                on_add_subcategory=self._open_add_subcategory,
                on_delete_subcategory=self._delete_subcategory,
            )
            self._body.add_widget(card)

    def _build_category_creator_card(self) -> MDCard:
        card = MDCard(
            style="filled",
            md_bg_color=APP_BG_CARD,
            radius=[dp(14)],
            padding=[dp(16), dp(14), dp(16), dp(14)],
            size_hint_y=None,
            height=dp(0),
            opacity=0,
        )
        layout = MDBoxLayout(orientation="vertical", spacing=dp(10), adaptive_height=True)

        self._creator_title = MDLabel(
            text="Add New Category",
            font_style="Title",
            role="medium",
            adaptive_height=True,
            theme_text_color="Custom",
            text_color=APP_TEXT,
        )
        layout.add_widget(self._creator_title)

        self._cat_name_field = MDTextField(
            MDTextFieldHintText(text="Category Name (e.g. Subscriptions)"),
            mode="outlined",
        )
        layout.add_widget(self._cat_name_field)

        # Color picker
        layout.add_widget(
            MDLabel(
                text="Select Color:",
                font_style="Label",
                role="small",
                adaptive_height=True,
                theme_text_color="Custom",
                text_color=APP_MUTED_TEXT,
            )
        )
        color_picker = ColorPickerRow(
            selected_color=self._new_cat_color,
            on_color_selected=self._on_color_selected,
        )
        layout.add_widget(color_picker)

        # Action buttons
        btn_row = MDBoxLayout(orientation="horizontal", adaptive_height=True, spacing=dp(10))
        save_btn = MDButton(style="filled", on_release=self._save_category, size_hint_x=0.5)
        save_btn.add_widget(MDButtonText(text="Save"))

        cancel_btn = MDButton(style="tonal", on_release=self._close_creator, size_hint_x=0.5)
        cancel_btn.add_widget(MDButtonText(text="Cancel"))

        btn_row.add_widget(save_btn)
        btn_row.add_widget(cancel_btn)
        layout.add_widget(btn_row)

        card.add_widget(layout)
        return card

    def _build_subcategory_creator_card(self) -> MDCard:
        card = MDCard(
            style="filled",
            md_bg_color=APP_BG_CARD,
            radius=[dp(14)],
            padding=[dp(16), dp(14), dp(16), dp(14)],
            size_hint_y=None,
            height=dp(0),
            opacity=0,
        )
        layout = MDBoxLayout(orientation="vertical", spacing=dp(10), adaptive_height=True)

        self._sub_creator_title = MDLabel(
            text="Add Subcategory",
            font_style="Title",
            role="medium",
            adaptive_height=True,
            theme_text_color="Custom",
            text_color=APP_TEXT,
        )
        layout.add_widget(self._sub_creator_title)

        self._sub_name_field = MDTextField(
            MDTextFieldHintText(text="Subcategory Name (e.g. Coffee)"),
            mode="outlined",
        )
        layout.add_widget(self._sub_name_field)

        btn_row = MDBoxLayout(orientation="horizontal", adaptive_height=True, spacing=dp(10))
        save_btn = MDButton(style="filled", on_release=self._save_subcategory, size_hint_x=0.5)
        save_btn.add_widget(MDButtonText(text="Add Subcategory"))

        cancel_btn = MDButton(style="tonal", on_release=self._close_sub_creator, size_hint_x=0.5)
        cancel_btn.add_widget(MDButtonText(text="Cancel"))

        btn_row.add_widget(save_btn)
        btn_row.add_widget(cancel_btn)
        layout.add_widget(btn_row)

        card.add_widget(layout)
        return card

    def _toggle_creator(self, *args) -> None:
        self._editing_cat_id = None
        self._creator_title.text = "Add New Category"
        self._cat_name_field.text = ""
        self._creator_card.opacity = 1
        self._creator_card.height = dp(200)

    def _close_creator(self, *args) -> None:
        self._creator_card.opacity = 0
        self._creator_card.height = dp(0)

    def _on_color_selected(self, color_hex: str) -> None:
        self._new_cat_color = color_hex

    def _save_category(self, *args) -> None:
        name = self._cat_name_field.text.strip()
        if not name:
            self._cat_status_lbl.text = "Please enter a category name."
            self._cat_status_lbl.text_color = APP_DANGER
            return

        try:
            if self._editing_cat_id is not None:
                self._category_service.update_category(
                    category_id=self._editing_cat_id,
                    name=name,
                    color=self._new_cat_color,
                )
                self._cat_status_lbl.text = f"Category '{name}' updated."
                self._cat_status_lbl.text_color = APP_SUCCESS
            else:
                self._category_service.create_category(
                    user_id=self._user.id,
                    name=name,
                    color=self._new_cat_color,
                    icon=self._new_cat_icon,
                )
                self._cat_status_lbl.text = f"Category '{name}' created."
                self._cat_status_lbl.text_color = APP_SUCCESS

            self._close_creator()
            Clock.schedule_once(lambda dt: self.refresh(), 0.3)

        except ValueError as exc:
            self._cat_status_lbl.text = str(exc)
            self._cat_status_lbl.text_color = APP_DANGER

    def _open_edit_category(self, category: Category) -> None:
        self._editing_cat_id = category.id
        self._creator_title.text = f"Edit '{category.name}'"
        self._cat_name_field.text = category.name
        self._new_cat_color = category.color or "#4ECDC4"
        self._creator_card.opacity = 1
        self._creator_card.height = dp(200)

    def _confirm_delete_category(self, category: Category) -> None:
        try:
            self._category_service.delete_category(category.id, soft=True)
            self._cat_status_lbl.text = f"Category '{category.name}' deleted."
            self._cat_status_lbl.text_color = APP_SUCCESS
            Clock.schedule_once(lambda dt: self.refresh(), 0.2)
        except Exception as exc:
            self._cat_status_lbl.text = f"Error: {exc}"
            self._cat_status_lbl.text_color = APP_DANGER

    def _open_add_subcategory(self, category: Category) -> None:
        self._target_category_for_sub = category.id
        self._sub_creator_title.text = f"Add Subcategory to '{category.name}'"
        self._sub_name_field.text = ""
        self._sub_creator_card.opacity = 1
        self._sub_creator_card.height = dp(140)

    def _close_sub_creator(self, *args) -> None:
        self._sub_creator_card.opacity = 0
        self._sub_creator_card.height = dp(0)

    def _save_subcategory(self, *args) -> None:
        sub_name = self._sub_name_field.text.strip()
        if not sub_name:
            self._cat_status_lbl.text = "Please enter a subcategory name."
            self._cat_status_lbl.text_color = APP_DANGER
            return

        try:
            self._category_service.create_subcategory(
                category_id=self._target_category_for_sub,
                name=sub_name,
            )
            self._cat_status_lbl.text = f"Subcategory '{sub_name}' added."
            self._cat_status_lbl.text_color = APP_SUCCESS
            self._close_sub_creator()
            Clock.schedule_once(lambda dt: self.refresh(), 0.3)
        except ValueError as exc:
            self._cat_status_lbl.text = str(exc)
            self._cat_status_lbl.text_color = APP_DANGER

    def _delete_subcategory(self, sub_id: int) -> None:
        try:
            self._category_service.delete_subcategory(sub_id, soft=True)
            self._cat_status_lbl.text = "Subcategory removed."
            self._cat_status_lbl.text_color = APP_SUCCESS
            Clock.schedule_once(lambda dt: self.refresh(), 0.2)
        except Exception as exc:
            self._cat_status_lbl.text = f"Error: {exc}"
            self._cat_status_lbl.text_color = APP_DANGER

    # ------------------------------------------------------------------
    # Profile & Settings Tab
    # ------------------------------------------------------------------

    def _render_profile_tab(self) -> None:
        self._body.add_widget(
            MDLabel(
                text="User Profile & Financial Baselines",
                font_style="Title",
                role="medium",
                adaptive_height=True,
                theme_text_color="Custom",
                text_color=APP_TEXT,
            )
        )

        card = MDCard(
            style="filled",
            md_bg_color=APP_BG_CARD,
            radius=[dp(16)],
            padding=[dp(18), dp(16), dp(18), dp(20)],
            size_hint_y=None,
            height=dp(380),
        )
        layout = MDBoxLayout(orientation="vertical", spacing=dp(12), adaptive_height=True)

        # Name field
        self._prof_name_field = MDTextField(
            MDTextFieldHintText(text="Your Name"),
            mode="outlined",
        )
        self._prof_name_field.text = self._user.name
        layout.add_widget(self._prof_name_field)

        # Profession display
        prof_text = self._user.profession
        if self._user.profession == "Other" and self._user.profession_custom:
            prof_text = f"{self._user.profession} ({self._user.profession_custom})"

        layout.add_widget(
            MDLabel(
                text=f"Profession: {prof_text}",
                font_style="Body",
                role="medium",
                adaptive_height=True,
                theme_text_color="Custom",
                text_color=APP_MUTED_TEXT,
            )
        )

        # Monthly Income target
        cur = self._user.currency or DEFAULT_CURRENCY
        cur_sym = CURRENCY_SYMBOLS.get(cur, "₹")

        inc_val = (
            format_paise_as_decimal(self._user.monthly_income_paise, cur)
            if self._user.monthly_income_paise is not None
            else ""
        )
        self._prof_income_field = MDTextField(
            MDTextFieldHintText(text=f"Monthly Income ({cur_sym})"),
            MDTextFieldHelperText(text="Target monthly earnings baseline", mode="on_focus"),
            mode="outlined",
        )
        self._prof_income_field.text = inc_val
        self._prof_income_field.input_filter = "float"
        layout.add_widget(self._prof_income_field)

        # Fixed Expenses baseline
        exp_val = (
            format_paise_as_decimal(self._user.fixed_expenses_paise, cur)
            if self._user.fixed_expenses_paise is not None
            else ""
        )
        self._prof_expense_field = MDTextField(
            MDTextFieldHintText(text=f"Fixed Expenses ({cur_sym})"),
            MDTextFieldHelperText(text="Rent, recurring bills, EMIs", mode="on_focus"),
            mode="outlined",
        )
        self._prof_expense_field.text = exp_val
        self._prof_expense_field.input_filter = "float"
        layout.add_widget(self._prof_expense_field)

        # Currency selection buttons
        layout.add_widget(
            MDLabel(
                text="Currency:",
                font_style="Label",
                role="small",
                adaptive_height=True,
                theme_text_color="Custom",
                text_color=APP_MUTED_TEXT,
            )
        )

        cur_row = MDBoxLayout(orientation="horizontal", adaptive_height=True, spacing=dp(8))
        self._selected_currency = cur
        self._cur_buttons = {}

        for c_code, c_sym in CURRENCY_SYMBOLS.items():
            btn = MDButton(
                style="filled" if c_code == cur else "tonal",
                size_hint_x=0.25,
                on_release=lambda *_, code=c_code: self._select_currency(code),
            )
            btn.add_widget(MDButtonText(text=f"{c_code} ({c_sym})", font_style="Label", role="small"))
            self._cur_buttons[c_code] = btn
            cur_row.add_widget(btn)

        layout.add_widget(cur_row)

        card.add_widget(layout)
        self._body.add_widget(card)

        # Save profile button
        save_btn = MDButton(
            style="filled",
            size_hint_x=1,
            on_release=self._save_profile_changes,
        )
        save_btn.add_widget(MDButtonText(text="Save Profile Changes"))
        self._body.add_widget(save_btn)

        # Profile status feedback
        self._prof_status_lbl = MDLabel(
            text="",
            font_style="Body",
            role="small",
            adaptive_height=True,
            theme_text_color="Custom",
            text_color=APP_SUCCESS,
        )
        self._body.add_widget(self._prof_status_lbl)

    def _select_currency(self, currency_code: str) -> None:
        self._selected_currency = currency_code
        for code, btn in self._cur_buttons.items():
            btn.style = "filled" if code == currency_code else "tonal"

    def _save_profile_changes(self, *args) -> None:
        self._prof_status_lbl.text = ""
        name = self._prof_name_field.text.strip()
        income_str = self._prof_income_field.text.strip() or None
        expense_str = self._prof_expense_field.text.strip() or None

        try:
            self._profile_service.update_profile(
                user_id=self._user.id,
                name=name,
                currency=self._selected_currency,
                monthly_income_str=income_str,
                fixed_expenses_str=expense_str,
            )
            self._prof_status_lbl.text = "Profile and settings saved successfully!"
            self._prof_status_lbl.text_color = APP_SUCCESS
        except ValueError as exc:
            self._prof_status_lbl.text = str(exc)
            self._prof_status_lbl.text_color = APP_DANGER
        except Exception as exc:
            self._prof_status_lbl.text = f"Error: {exc}"
            self._prof_status_lbl.text_color = APP_DANGER
