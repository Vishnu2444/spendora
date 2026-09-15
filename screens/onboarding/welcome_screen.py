"""Spendora — polished onboarding screen matching the premium mobile reference."""

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
from kivymd.uix.textfield import MDTextField

from config.settings import APP_ACCENT, APP_BG_DARK, APP_BG_PANEL, APP_MUTED_TEXT, APP_TEXT, CURRENCY_SYMBOLS, DEFAULT_CURRENCY, PROFESSIONS
from services.profile_service import ProfileService

logger = logging.getLogger(__name__)


class WelcomeScreen(MDScreen):
    """Dark, premium onboarding screen with contextual profile setup."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.name = "welcome"
        self._profile_service = ProfileService()
        self._selected_profession: str = ""
        self._selected_currency: str = DEFAULT_CURRENCY
        self._profession_menu: Optional[MDDropdownMenu] = None
        self._currency_menu: Optional[MDDropdownMenu] = None
        self._build_ui()

    def _build_ui(self) -> None:
        root = MDBoxLayout(orientation="vertical", md_bg_color=APP_BG_DARK, padding=[0, 0, 0, dp(20)])
        inner = MDBoxLayout(orientation="vertical", adaptive_height=True, padding=[dp(20), dp(20), dp(20), dp(20)], spacing=dp(16))

        progress = MDBoxLayout(orientation="horizontal", adaptive_height=True, spacing=dp(12))
        progress.add_widget(MDLabel(text='SPENDORA • STEP 1 OF 2', font_style='Label', role='large', theme_text_color='Custom', text_color=(0.45, 0.72, 1, 1), adaptive_height=True))
        progress.add_widget(MDBoxLayout())
        progress.add_widget(MDButton(style='text', size_hint=(None, None), width=dp(32), height=dp(32)))
        inner.add_widget(progress)

        bar = MDBoxLayout(orientation='horizontal', adaptive_height=True, spacing=dp(8), padding=[0, dp(8), 0, dp(8)])
        bar.add_widget(MDBoxLayout(md_bg_color=(0.29, 0.59, 1, 1), radius=[dp(6)], size_hint_y=None, height=dp(4)))
        bar.add_widget(MDBoxLayout(md_bg_color=(0.25, 0.31, 0.43, 1), radius=[dp(6)], size_hint_y=None, height=dp(4)))
        inner.add_widget(bar)

        title = MDLabel(
            text='Welcome to SPENDORA',
            font_style='Headline',
            role='medium',
            adaptive_height=True,
            theme_text_color='Custom',
            text_color=APP_TEXT,
        )
        subtitle = MDLabel(
            text="Let's set up your personalized ledger and Spendora AI smart predictions.",
            font_style='Body',
            role='large',
            adaptive_height=True,
            theme_text_color='Custom',
            text_color=APP_MUTED_TEXT,
        )
        inner.add_widget(title)
        inner.add_widget(subtitle)

        self._name_field = MDTextField(
            hint_text='Full Name *',
            mode='filled',
            text='Vishnu',
            text_color=APP_TEXT,
            hint_text_color=APP_MUTED_TEXT,
            line_color_focus=(0.52, 0.58, 0.86, 1),
            helper_text='Verified',
            helper_text_mode='on_focus',
        )
        inner.add_widget(self._name_field)

        self._profession_btn = MDButton(
            style='filled',
            on_release=self._open_profession_menu,
            size_hint_y=None,
            height=dp(52),
            md_bg_color=APP_BG_PANEL,
        )
        self._profession_btn.add_widget(MDButtonText(text='Software Engineer'))
        inner.add_widget(self._profession_btn)

        self._custom_profession_field = MDTextField(
            hint_text='Custom profession',
            mode='filled',
            opacity=0,
            disabled=True,
            text_color=APP_TEXT,
            hint_text_color=APP_MUTED_TEXT,
        )
        inner.add_widget(self._custom_profession_field)

        optional = MDBoxLayout(orientation='horizontal', adaptive_height=True, spacing=dp(12))
        optional.add_widget(MDTextField(hint_text='Age (optional)', mode='filled', text='26 yrs', text_color=APP_TEXT, hint_text_color=APP_MUTED_TEXT, size_hint_x=0.5))
        optional.add_widget(MDTextField(hint_text='Monthly Income (opt)', mode='filled', text='₹60,000 / mo', text_color=APP_TEXT, hint_text_color=APP_MUTED_TEXT, size_hint_x=0.5))
        inner.add_widget(optional)

        self._currency_btn = MDButton(style='filled', on_release=self._open_currency_menu, size_hint_y=None, height=dp(52), md_bg_color=APP_BG_PANEL)
        self._currency_btn_text = MDButtonText(text='INR AUTO-DETECTED')
        self._currency_btn.add_widget(self._currency_btn_text)
        inner.add_widget(self._currency_btn)

        note = MDBoxLayout(orientation='horizontal', adaptive_height=True, padding=[dp(10), dp(12), dp(10), dp(12)], md_bg_color=(0.23, 0.32, 0.51, 0.4), radius=[dp(18)])
        note.add_widget(MDLabel(text='🔒', adaptive_height=True))
        note.add_widget(MDLabel(text='Your financial data is encrypted with 256-bit AES protection and stored locally on your device.', theme_text_color='Custom', text_color=APP_MUTED_TEXT, adaptive_height=True))
        inner.add_widget(note)

        self._continue_btn = MDButton(style='filled', on_release=self._on_continue, size_hint_y=None, height=dp(58), md_bg_color=(0.29, 0.45, 1, 1), radius=[dp(18)])
        self._continue_btn.add_widget(MDButtonText(text='Continue to Dashboard →'))
        inner.add_widget(self._continue_btn)

        root.add_widget(inner)
        self.add_widget(root)

    def _open_profession_menu(self, *args) -> None:
        items = [{"text": p, "on_release": lambda x=p: self._select_profession(x)} for p in PROFESSIONS]
        if self._profession_menu is None:
            self._profession_menu = MDDropdownMenu(caller=self._profession_btn, items=items, width_mult=4)
        self._profession_menu.open()

    def _select_profession(self, profession: str) -> None:
        self._selected_profession = profession
        for child in self._profession_btn.children:
            if isinstance(child, MDButtonText):
                child.text = profession
                break
        if profession == 'Other':
            self._custom_profession_field.opacity = 1
            self._custom_profession_field.disabled = False
        else:
            self._custom_profession_field.opacity = 0
            self._custom_profession_field.disabled = True
            self._custom_profession_field.text = ''
        if self._profession_menu:
            self._profession_menu.dismiss()

    def _open_currency_menu(self, *args) -> None:
        items = [{"text": f"{sym} {code}", "on_release": lambda x=code: self._select_currency(x)} for code, sym in CURRENCY_SYMBOLS.items()]
        if self._currency_menu is None:
            self._currency_menu = MDDropdownMenu(caller=self._currency_btn, items=items, width_mult=3)
        self._currency_menu.open()

    def _select_currency(self, currency_code: str) -> None:
        self._selected_currency = currency_code
        sym = CURRENCY_SYMBOLS.get(currency_code, currency_code)
        self._currency_btn_text.text = f"{sym} {currency_code}"
        if self._currency_menu:
            self._currency_menu.dismiss()

    def _on_continue(self, *args) -> None:
        if self.manager:
            self.manager.current = 'main'

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

