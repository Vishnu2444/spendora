"""
Spendora — Welcome / Onboarding Screen (Screen 1 of 2).

Collects:
  - User's name
  - Profession (dropdown with predefined options + "Other" with custom input)
  - Optional: monthly income, fixed expenses, preferred currency

Navigation:
  On success → category_setup screen
"""

from __future__ import annotations

import logging
from typing import Optional

from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.scrollview import ScrollView
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDButton, MDButtonText
from kivymd.uix.label import MDLabel
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.screen import MDScreen
from kivymd.uix.snackbar import MDSnackbar, MDSnackbarText
from kivymd.uix.textfield import (
    MDTextField,
    MDTextFieldHintText,
    MDTextFieldHelperText,
    MDTextFieldMaxLengthText,
)

from config.settings import PROFESSIONS, DEFAULT_CURRENCY, CURRENCY_SYMBOLS
from services.profile_service import ProfileService

logger = logging.getLogger(__name__)


class WelcomeScreen(MDScreen):
    """
    Onboarding Screen 1: collects user profile information.

    Architecture note: All validation is delegated to ProfileService /
    validators.py — this screen contains only UI logic.
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.name = "welcome"
        self._profile_service = ProfileService()
        self._selected_profession: str = ""
        self._selected_currency: str = DEFAULT_CURRENCY
        self._profession_menu: Optional[MDDropdownMenu] = None
        self._currency_menu: Optional[MDDropdownMenu] = None
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        """Build the screen layout programmatically."""

        root = MDBoxLayout(
            orientation="vertical",
            md_bg_color=self.theme_cls.backgroundColor,
        )

        scroll = ScrollView()
        content = MDBoxLayout(
            orientation="vertical",
            adaptive_height=True,
            padding=[dp(24), dp(48), dp(24), dp(32)],
            spacing=dp(20),
        )

        # ---- Header ----
        header = MDBoxLayout(
            orientation="vertical",
            adaptive_height=True,
            spacing=dp(8),
            padding=[0, 0, 0, dp(16)],
        )
        header.add_widget(MDLabel(
            text="Welcome to Spendora 👋",
            font_style="Display",
            role="small",
            halign="left",
            adaptive_height=True,
        ))
        header.add_widget(MDLabel(
            text="Let's set up your profile to personalise your experience.",
            font_style="Body",
            role="large",
            halign="left",
            adaptive_height=True,
            theme_text_color="Secondary",
        ))
        content.add_widget(header)

        # ---- Name field ----
        self._name_field = MDTextField(
            MDTextFieldHintText(text="Your name"),
            MDTextFieldHelperText(text="This is how Spendora will greet you", mode="on_focus"),
            MDTextFieldMaxLengthText(max_text_length=100),
            mode="outlined",
        )
        content.add_widget(self._name_field)

        # ---- Profession button (acts as a dropdown trigger) ----
        self._profession_btn = MDButton(
            style="outlined",
            on_release=self._open_profession_menu,
        )
        self._profession_btn.add_widget(MDButtonText(
            text="Select your profession",
            id="profession_btn_text",
        ))
        content.add_widget(self._profession_btn)

        # ---- Custom profession field (hidden until "Other" selected) ----
        self._custom_profession_field = MDTextField(
            MDTextFieldHintText(text="Your profession"),
            MDTextFieldHelperText(text="Please describe your profession", mode="on_focus"),
            MDTextFieldMaxLengthText(max_text_length=200),
            mode="outlined",
        )
        self._custom_profession_field.opacity = 0
        self._custom_profession_field.disabled = True
        content.add_widget(self._custom_profession_field)

        # ---- Optional section label ----
        content.add_widget(MDLabel(
            text="Optional information",
            font_style="Label",
            role="large",
            halign="left",
            adaptive_height=True,
            theme_text_color="Secondary",
            padding=[0, dp(8), 0, 0],
        ))

        # ---- Monthly income ----
        self._income_field = MDTextField(
            MDTextFieldHintText(text="Monthly income (e.g. 50000)"),
            MDTextFieldHelperText(text="Helps with financial insights", mode="on_focus"),
            mode="outlined",
            input_filter="float",
        )
        content.add_widget(self._income_field)

        # ---- Fixed expenses ----
        self._expenses_field = MDTextField(
            MDTextFieldHintText(text="Typical monthly expenses (e.g. 20000)"),
            MDTextFieldHelperText(text="Rent, EMIs, recurring bills", mode="on_focus"),
            mode="outlined",
            input_filter="float",
        )
        content.add_widget(self._expenses_field)

        # ---- Currency button ----
        self._currency_btn = MDButton(
            style="outlined",
            on_release=self._open_currency_menu,
        )
        self._currency_btn_text = MDButtonText(
            text=f"Currency: ₹ INR",
        )
        self._currency_btn.add_widget(self._currency_btn_text)
        content.add_widget(self._currency_btn)

        # ---- Continue button ----
        self._continue_btn = MDButton(
            style="filled",
            on_release=self._on_continue,
        )
        self._continue_btn.add_widget(MDButtonText(text="Continue →"))
        content.add_widget(self._continue_btn)

        scroll.add_widget(content)
        root.add_widget(scroll)
        self.add_widget(root)

    # ------------------------------------------------------------------
    # Profession menu
    # ------------------------------------------------------------------

    def _open_profession_menu(self, *args) -> None:
        """Open the profession selection dropdown."""
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
                width_mult=4,
            )
        self._profession_menu.open()

    def _select_profession(self, profession: str) -> None:
        """Handle profession selection."""
        self._selected_profession = profession
        # Update button text.
        for child in self._profession_btn.children:
            if isinstance(child, MDButtonText):
                child.text = profession
                break

        # Show / hide custom field.
        if profession == "Other":
            self._custom_profession_field.opacity = 1
            self._custom_profession_field.disabled = False
        else:
            self._custom_profession_field.opacity = 0
            self._custom_profession_field.disabled = True
            self._custom_profession_field.text = ""

        if self._profession_menu:
            self._profession_menu.dismiss()

    # ------------------------------------------------------------------
    # Currency menu
    # ------------------------------------------------------------------

    def _open_currency_menu(self, *args) -> None:
        """Open the currency selection dropdown."""
        items = [
            {
                "text": f"{sym} {code}",
                "on_release": lambda x=code: self._select_currency(x),
            }
            for code, sym in CURRENCY_SYMBOLS.items()
        ]
        if self._currency_menu is None:
            self._currency_menu = MDDropdownMenu(
                caller=self._currency_btn,
                items=items,
                width_mult=3,
            )
        self._currency_menu.open()

    def _select_currency(self, currency_code: str) -> None:
        """Handle currency selection."""
        self._selected_currency = currency_code
        sym = CURRENCY_SYMBOLS.get(currency_code, currency_code)
        self._currency_btn_text.text = f"Currency: {sym} {currency_code}"
        if self._currency_menu:
            self._currency_menu.dismiss()

    # ------------------------------------------------------------------
    # Form submission
    # ------------------------------------------------------------------

    def _on_continue(self, *args) -> None:
        """Validate inputs and create user profile."""
        name = self._name_field.text.strip()
        profession = self._selected_profession
        profession_custom = self._custom_profession_field.text.strip() if profession == "Other" else None
        income_str = self._income_field.text.strip() or None
        expenses_str = self._expenses_field.text.strip() or None

        # Basic UI-level checks before hitting the service.
        if not name:
            self._show_error("Please enter your name.")
            return
        if not profession:
            self._show_error("Please select your profession.")
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
        except ValueError as exc:
            self._show_error(str(exc))
            return
        except Exception as exc:
            logger.error("Unexpected error creating user: %s", exc)
            self._show_error("Something went wrong. Please try again.")
            return

        # Store user_id for the next screen.
        app = self.manager.get_screen("category_setup") if self.manager else None
        if app and hasattr(app, "set_user"):
            app.set_user(user)

        self.manager.current = "category_setup"

    def _show_error(self, message: str) -> None:
        """Display a non-blocking error snackbar."""
        snackbar = MDSnackbar(
            MDSnackbarText(text=message),
            y=dp(24),
            pos_hint={"center_x": 0.5},
            size_hint_x=0.9,
            duration=3,
        )
        snackbar.open()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_enter(self, *args) -> None:
        """Called when this screen becomes active."""
        # Clear fields if re-entering (e.g. back navigation in future).
        pass

