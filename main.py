"""
Spendora — Application entry point.

Bootstraps:
    1. Database (creates tables if needed)
    2. KivyMD app with Material Design 3 theming
    3. Screen manager with all screens
    4. Routing: onboarding → main app (based on user existence)

Run with:
    python main.py
"""

from __future__ import annotations

import logging
import os
import sys

# ---------------------------------------------------------------------------
# Kivy environment must be configured BEFORE kivy is imported.
# ---------------------------------------------------------------------------
os.environ.setdefault("KIVY_NO_ENV_CONFIG", "1")

# Suppress Kivy's verbose startup log unless DEBUG mode is on.
# This must come before any kivy import.
import kivy

kivy.require("2.3.0")

from kivy.config import Config

# Mobile-friendly window size for desktop testing.
# On Android these are ignored and the full screen is used.
Config.set("graphics", "width", "400")
Config.set("graphics", "height", "780")
Config.set("graphics", "resizable", "1")

from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.properties import StringProperty
from kivy.uix.screenmanager import ScreenManager, SlideTransition
from kivymd.app import MDApp
from kivymd.uix.navigationbar import (
    MDNavigationBar,
    MDNavigationItem,
    MDNavigationItemIcon,
    MDNavigationItemLabel,
)
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.screen import MDScreen
from kivymd.uix.label import MDLabel
from kivymd.uix.boxlayout import MDBoxLayout

# ---------------------------------------------------------------------------
# Internal imports (database, screens, etc.)
# ---------------------------------------------------------------------------
from database.database import init_db
from screens.onboarding.welcome_screen import WelcomeScreen
from screens.onboarding.category_setup_screen import CategorySetupScreen
from screens.dashboard.dashboard_screen import DashboardScreen
from screens.transactions.transactions_screen import TransactionsScreen
from screens.transactions.add_edit_transaction_screen import AddEditTransactionScreen
from screens.analytics.analytics_screen import AnalyticsScreen
from screens.personalization.personalization_screen import PersonalizationScreen
from screens.assistant.assistant_screen import AssistantScreen
from services.profile_service import ProfileService
from config.settings import (
    APP_NAME,
    APP_VERSION,
    THEME_PRIMARY_COLOR,
    THEME_ACCENT_COLOR,
    THEME_STYLE,
    LOG_LEVEL,
    DEBUG,
)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.WARNING),
    format="%(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Main navigation screen (bottom nav + screens)
# ---------------------------------------------------------------------------

class NavItem(MDNavigationItem):
    """A navigation item with icon and label for MDNavigationBar."""
    icon = StringProperty()
    text = StringProperty()

    def __init__(self, icon: str, text: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.icon = icon
        self.text = text
        self.add_widget(MDNavigationItemIcon(icon=icon))
        self.add_widget(MDNavigationItemLabel(text=text))


class MainScreen(MDScreen):
    """
    The primary screen shown after onboarding.

    Contains a bottom navigation bar with five tabs:
        Dashboard | Transactions | Analytics | Personalization | AI Assistant
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.name = "main"
        self._build_ui()

    def _build_ui(self) -> None:
        """Build the bottom navigation layout."""
        layout = MDBoxLayout(
            orientation="vertical",
            md_bg_color=self.theme_cls.backgroundColor,
        )

        self._screen_manager = MDScreenManager()
        self._dashboard = DashboardScreen()
        self._screen_manager.add_widget(self._dashboard)
        self._screen_manager.add_widget(TransactionsScreen())
        self._screen_manager.add_widget(AnalyticsScreen())
        self._screen_manager.add_widget(PersonalizationScreen())
        self._screen_manager.add_widget(AssistantScreen())

        self._nav_bar = MDNavigationBar(
            on_switch_tabs=self._on_switch_tabs,
        )
        self._nav_bar.add_widget(NavItem(icon="view-dashboard", text="Dashboard", active=True))
        self._nav_bar.add_widget(NavItem(icon="swap-horizontal", text="Transactions"))
        self._nav_bar.add_widget(NavItem(icon="chart-bar", text="Analytics"))
        self._nav_bar.add_widget(NavItem(icon="tag-multiple", text="Personalization"))
        self._nav_bar.add_widget(NavItem(icon="robot", text="Assistant"))

        layout.add_widget(self._screen_manager)
        layout.add_widget(self._nav_bar)
        self.add_widget(layout)

    def _on_switch_tabs(
        self,
        bar: MDNavigationBar,
        item: MDNavigationItem,
        item_icon: str,
        item_text: str,
    ) -> None:
        target_name = item_text.lower()
        if self._screen_manager.has_screen(target_name):
            self._screen_manager.current = target_name

    def switch_tab(self, tab_name: str) -> None:
        """Programmatically switch tabs inside MainScreen."""
        target = tab_name.lower()
        if self._screen_manager.has_screen(target):
            self._screen_manager.current = target

    def on_enter(self, *args) -> None:
        """Trigger refresh on the active child screen when returning to MainScreen."""
        current_screen = self._screen_manager.current_screen
        if current_screen and hasattr(current_screen, "refresh"):
            current_screen.refresh()


# ---------------------------------------------------------------------------
# Spendora Application
# ---------------------------------------------------------------------------

class SpendoraApp(MDApp):
    """
    Root KivyMD application class.

    Theming, screen manager setup, and initial routing are handled here.
    Business logic lives in services, not in this class.
    """

    def build(self) -> ScreenManager:
        # ---- Theme ----
        self.theme_cls.theme_style = THEME_STYLE
        self.theme_cls.primary_palette = THEME_PRIMARY_COLOR
        self.theme_cls.accent_palette = THEME_ACCENT_COLOR
        self.theme_cls.material_style = "M3"
        self.title = APP_NAME
        Window.clearcolor = (8 / 255, 15 / 255, 25 / 255, 1)

        # ---- Database ----
        try:
            init_db()
            logger.info("Database ready.")
        except Exception as exc:
            logger.critical("Failed to initialise database: %s", exc)
            # Show a minimal error screen and exit gracefully.
            from kivymd.uix.label import MDLabel
            root = MDBoxLayout(
                orientation="vertical",
                padding=[dp(24), dp(48)],
                spacing=dp(16),
                md_bg_color=(1, 1, 1, 1),
            )
            root.add_widget(MDLabel(
                text="⚠️ Spendora could not start.\n\nDatabase initialisation failed.\nPlease check storage permissions.",
                halign="center",
                adaptive_height=True,
            ))
            return root  # type: ignore[return-value]

        # ---- Screen Manager ----
        sm = ScreenManager(transition=SlideTransition())

        # Onboarding and main screens
        welcome = WelcomeScreen()
        category_setup = CategorySetupScreen()
        main = MainScreen()
        add_edit_transaction = AddEditTransactionScreen()

        sm.add_widget(welcome)
        sm.add_widget(category_setup)
        sm.add_widget(main)
        sm.add_widget(add_edit_transaction)

        # ---- Routing ----
        # If a user already exists and has completed onboarding → go to main.
        # Otherwise → start from welcome screen.
        profile_service = ProfileService()
        user = profile_service.get_current_user()

        if user is not None and user.is_onboarding_complete:
            sm.current = "main"
            logger.info("Returning user %d detected — skipping onboarding.", user.id)
        else:
            sm.current = "welcome"
            logger.info("No returning user found — starting onboarding.")

        return sm

    def switch_tab(self, tab_name: str) -> None:
        """Switch tab inside MainScreen."""
        if self.root and self.root.has_screen("main"):
            main_screen = self.root.get_screen("main")
            if hasattr(main_screen, "switch_tab"):
                main_screen.switch_tab(tab_name)

    def on_start(self) -> None:
        logger.info("%s %s started.", APP_NAME, APP_VERSION)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    SpendoraApp().run()

