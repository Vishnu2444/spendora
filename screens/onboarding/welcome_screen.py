"""
Spendora — Welcome Screen (Onboarding Step 1 of 2).

Profile creation and profession selection with dark theme styling.
"""

from __future__ import annotations

import logging
from typing import Optional

from kivy.metrics import dp
from kivy.uix.scrollview import ScrollView
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDButton, MDButtonText
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.screen import MDScreen
from kivymd.uix.textfield import (
    MDTextField,
    MDTextFieldHintText,
    MDTextFieldHelperText,
)

from config.settings import (
    APP_ACCENT,
    APP_BG_CARD,
    APP_BG_DARK,
    APP_BG_PANEL,
    APP_DANGER,
    APP_MUTED_TEXT,
    APP_TEXT,
    CURRENCY_SYMBOLS,
    DEFAULT_CURRENCY,
    PROFESSIONS,
)
from services.profile_service import ProfileService

logger = logging.getLogger(__name__)


class WelcomeScreen(MDScreen):
    """Initial onboarding screen for user profile setup."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.name = "welcome"
        self._profile_service = ProfileService()
        self._selected_profession = "Software Engineer"
        self._selected_currency = DEFAULT_CURRENCY
        self._profession_menu: Optional[MDDropdownMenu] = None
        self._currency_menu: Optional[MDDropdownMenu] = None
        self._build_ui()

    def _build_ui(self) -> None:
        root = MDBoxLayout(orientation="vertical", md_bg_color=APP_BG_DARK)

        scroll = ScrollView(do_scroll_x=False)
        content = MDBoxLayout(
            orientation="vertical",
            adaptive_height=True,
            padding=[dp(24), dp(36), dp(24), dp(36)],
            spacing=dp(16),
        )

        # Header Badge
        badge = MDCard(
            style="filled",
            md_bg_color=(0.28, 0.24, 0.45, 1),
            size_hint=(None, None),
            size=(dp(48), dp(48)),
            radius=[dp(24)],
        )
        badge.add_widget(
            MDLabel(
                text="✦",
                halign="center",
                valign="middle",
                font_style="Headline",
                role="small",
                theme_text_color="Custom",
                text_color=(0.75, 0.65, 1, 1),
            )
        )
        content.add_widget(badge)

        # Title & Subtitle
        content.add_widget(
            MDLabel(
                text="Welcome to Spendora",
                font_style="Headline",
                role="medium",
                adaptive_height=True,
                theme_text_color="Custom",
                text_color=APP_TEXT,
            )
        )
        content.add_widget(
            MDLabel(
                text="Set up your profile to receive personalized expense categories and grounded financial insights.",
                font_style="Body",
                role="medium",
                adaptive_height=True,
                theme_text_color="Custom",
                text_color=APP_MUTED_TEXT,
            )
        )

        # Full Name Field
        self._name_field = MDTextField(
            MDTextFieldHintText(text="Full Name *"),
            mode="outlined",
        )
        content.add_widget(self._name_field)

        # Profession Selector Label
        content.add_widget(
            MDLabel(
                text="Your Profession *",
                font_style="Label",
                role="medium",
                adaptive_height=True,
                theme_text_color="Custom",
                text_color=APP_MUTED_TEXT,
            )
        )

        self._profession_btn = MDButton(
            style="outlined",
            size_hint_x=1,
            on_release=self._open_profession_menu,
        )
        self._profession_btn_text = MDButtonText(text="Software Engineer")
        self._profession_btn.add_widget(self._profession_btn_text)
        content.add_widget(self._profession_btn)

        # Custom Profession Field (hidden unless 'Other' is selected)
        self._custom_profession_field = MDTextField(
            MDTextFieldHintText(text="Specify Profession *"),
            mode="outlined",
            opacity=0,
            disabled=True,
        )
        content.add_widget(self._custom_profession_field)

        # Monthly Income Baseline
        self._income_field = MDTextField(
            MDTextFieldHintText(text="Monthly Income (optional)"),
            MDTextFieldHelperText(text="e.g. 75000", mode="on_focus"),
            mode="outlined",
        )
        self._income_field.input_filter = "float"
        content.add_widget(self._income_field)

        # Fixed Expenses Baseline
        self._expenses_field = MDTextField(
            MDTextFieldHintText(text="Fixed Expenses (optional)"),
            MDTextFieldHelperText(text="Rent, recurring bills, EMIs", mode="on_focus"),
            mode="outlined",
        )
        self._expenses_field.input_filter = "float"
        content.add_widget(self._expenses_field)

        # Currency Selector
        content.add_widget(
            MDLabel(
                text="Currency *",
                font_style="Label",
                role="medium",
                adaptive_height=True,
                theme_text_color="Custom",
                text_color=APP_MUTED_TEXT,
            )
        )
        self._currency_btn = MDButton(
            style="outlined",
            size_hint_x=1,
            on_release=self._open_currency_menu,
        )
        self._currency_btn_text = MDButtonText(text=f"INR ({CURRENCY_SYMBOLS.get('INR', '₹')})")
        self._currency_btn.add_widget(self._currency_btn_text)
        content.add_widget(self._currency_btn)

        # Error / Status Label
        self._status_label = MDLabel(
            text="",
            font_style="Body",
            role="small",
            adaptive_height=True,
            theme_text_color="Custom",
            text_color=APP_DANGER,
        )
        content.add_widget(self._status_label)

        # Continue Button
        continue_btn = MDButton(
            style="filled",
            size_hint_x=1,
            on_release=self._on_continue,
        )
        continue_btn.add_widget(MDButtonText(text="Continue to Categories →"))
        content.add_widget(continue_btn)

        scroll.add_widget(content)
        root.add_widget(scroll)
        self.add_widget(root)

    # ------------------------------------------------------------------
    # Menus
    # ------------------------------------------------------------------

    def _open_profession_menu(self, *args) -> None:
        items = [
            {
                "text": p,
                "on_release": lambda x=p: self._select_profession(x),
            }
            for p in PROFESSIONS
        ]
        if self._profession_menu is None:
            self._profession_menu = MDDropdownMenu(
                caller=self._profession_btn,
                items=items,
            )
        self._profession_menu.open()

    def _select_profession(self, profession: str) -> None:
        self._selected_profession = profession
        self._profession_btn_text.text = profession
        if self._profession_menu:
            self._profession_menu.dismiss()

        if profession == "Other":
            self._custom_profession_field.opacity = 1
            self._custom_profession_field.disabled = False
        else:
            self._custom_profession_field.opacity = 0
            self._custom_profession_field.disabled = True
            self._custom_profession_field.text = ""

    def _open_currency_menu(self, *args) -> None:
        items = [
            {
                "text": f"{code} ({sym})",
                "on_release": lambda x=code: self._select_currency(x),
            }
            for code, sym in CURRENCY_SYMBOLS.items()
        ]
        if self._currency_menu is None:
            self._currency_menu = MDDropdownMenu(
                caller=self._currency_btn,
                items=items,
            )
        self._currency_menu.open()

    def _select_currency(self, code: str) -> None:
        self._selected_currency = code
        sym = CURRENCY_SYMBOLS.get(code, "")
        self._currency_btn_text.text = f"{code} ({sym})"
        if self._currency_menu:
            self._currency_menu.dismiss()

    # ------------------------------------------------------------------
    # Submission
    # ------------------------------------------------------------------

    def _on_continue(self, *args) -> None:
        self._status_label.text = ""
        name = self._name_field.text.strip()
        profession = self._selected_profession
        profession_custom = (
            self._custom_profession_field.text.strip()
            if profession == "Other"
            else None
        )
        income_str = self._income_field.text.strip() or None
        expenses_str = self._expenses_field.text.strip() or None

        if not name:
            self._status_label.text = "Please enter your name."
            return

        if profession == "Other" and not profession_custom:
            self._status_label.text = "Please specify your custom profession."
            return

        try:
            user = self._profile_service.create_user(
                name=name,
                profession=profession,
                profession_custom=profession_custom,
                monthly_income_str=income_str,
                fixed_expenses_str=expenses_str,
                currency=self._selected_currency,
            )

            if self.manager and self.manager.has_screen("category_setup"):
                setup_screen = self.manager.get_screen("category_setup")
                if hasattr(setup_screen, "set_user"):
                    setup_screen.set_user(user)
                self.manager.current = "category_setup"

        except ValueError as exc:
            self._status_label.text = str(exc)
        except Exception as exc:
            logger.error("Error creating user: %s", exc)
            self._status_label.text = f"Error: {exc}"
