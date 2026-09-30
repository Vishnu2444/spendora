"""
Spendora — Central Theme & Dark Mode Manager.

Handles dynamic Light / Dark / System theme switching, state persistence,
palette token resolution, and reactive listener callbacks across all views.
"""

from __future__ import annotations

import logging
from typing import Callable, List, Optional

import flet as ft

from config.settings import (
    COLOR_BACKGROUND,
    COLOR_CORAL_ACCENT,
    COLOR_EMERALD_ACCENT,
    COLOR_ERROR,
    COLOR_ON_PRIMARY,
    COLOR_ON_SECONDARY,
    COLOR_ON_SURFACE,
    COLOR_ON_SURFACE_VARIANT,
    COLOR_OUTLINE,
    COLOR_OUTLINE_VARIANT,
    COLOR_PRIMARY,
    COLOR_PRIMARY_CONTAINER,
    COLOR_PRIMARY_FIXED,
    COLOR_SECONDARY,
    COLOR_SECONDARY_CONTAINER,
    COLOR_SECONDARY_FIXED,
    COLOR_SURFACE_CARD,
    COLOR_SURFACE_CONTAINER,
    COLOR_SURFACE_LOW,
    COLOR_TERTIARY_CONTAINER,
)

logger = logging.getLogger(__name__)

# Dark Mode Palette Tokens (Matching Stitch intelligent_fintech specifications)
COLOR_BACKGROUND_DARK = "#0F131D"
COLOR_SURFACE_CARD_DARK = "#1C1F2A"
COLOR_SURFACE_LOW_DARK = "#171B26"
COLOR_SURFACE_CONTAINER_DARK = "#262A35"
COLOR_SURFACE_HIGH_DARK = "#313540"
COLOR_ON_SURFACE_DARK = "#DFE2F1"
COLOR_ON_SURFACE_VARIANT_DARK = "#C7C4D7"
COLOR_OUTLINE_DARK = "#908FA0"
COLOR_OUTLINE_VARIANT_DARK = "#464554"
COLOR_PRIMARY_DARK = "#C0C1FF"
COLOR_PRIMARY_CONTAINER_DARK = "#8083FF"
COLOR_SECONDARY_DARK = "#4EDEA3"
COLOR_SECONDARY_CONTAINER_DARK = "#00A572"
COLOR_TERTIARY_DARK = "#FFB2B7"
COLOR_TERTIARY_CONTAINER_DARK = "#FF516A"


class ThemeMode:
    LIGHT = "LIGHT"
    DARK = "DARK"
    SYSTEM = "SYSTEM"


class ThemeManager:
    """Singleton-style Theme Manager for reactive dark mode toggling."""

    def __init__(self) -> None:
        self._mode: str = ThemeMode.DARK  # Default to Stitch Dark mode
        self._listeners: List[Callable] = []
        self._page: Optional[ft.Page] = None

    def set_page(self, page: ft.Page) -> None:
        self._page = page

    def register_listener(self, listener: Callable) -> None:
        """Register callback to be invoked when theme changes."""
        if listener not in self._listeners:
            self._listeners.append(listener)

    add_listener = register_listener

    def unregister_listener(self, listener: Callable) -> None:
        if listener in self._listeners:
            self._listeners.remove(listener)

    remove_listener = unregister_listener

    @property
    def mode(self) -> str:
        return self._mode

    def is_dark(self) -> bool:
        if self._mode == "DARK":
            return True
        elif self._mode == "SYSTEM" and self._page:
            return self._page.platform_brightness == ft.Brightness.DARK
        return False

    def toggle(self, page: Optional[ft.Page] = None) -> None:
        """Toggle between LIGHT and DARK mode."""
        p = page or self._page
        new_mode = "LIGHT" if self.is_dark() else "DARK"
        self.set_theme(new_mode, p)

    def load_saved_preference(self, page: Optional[ft.Page] = None) -> None:
        """Load stored theme preference from database."""
        p = page or self._page
        try:
            from database.database import get_session
            from database.repositories.user_repository import UserRepository
            with get_session() as session:
                user = UserRepository(session).get_first_user()
                if user:
                    from database.models import UserPreference
                    pref = session.query(UserPreference).filter(
                        UserPreference.user_id == user.id,
                        UserPreference.key == "theme_mode",
                    ).first()
                    if pref and pref.value:
                        self.set_theme(pref.value, p)
                        return
        except Exception as ex:
            logger.debug("Could not load theme preference: %s", ex)
        if p:
            self.set_theme(self._mode, p)

    def set_theme(self, mode: str, page: Optional[ft.Page] = None) -> None:
        """Set theme mode: LIGHT, DARK, or SYSTEM."""
        self._mode = mode.upper()
        p = page or self._page

        is_dark_now = self.is_dark()

        if p:
            if self._mode == "DARK":
                p.theme_mode = ft.ThemeMode.DARK
                p.bgcolor = COLOR_BACKGROUND_DARK
            elif self._mode == "LIGHT":
                p.theme_mode = ft.ThemeMode.LIGHT
                p.bgcolor = COLOR_BACKGROUND
            else:
                p.theme_mode = ft.ThemeMode.SYSTEM
                p.bgcolor = COLOR_BACKGROUND_DARK if is_dark_now else COLOR_BACKGROUND

        # Persist theme preference in UserPreferences if available
        try:
            from database.database import get_session
            from database.repositories.user_repository import UserRepository
            with get_session() as session:
                user = UserRepository(session).get_first_user()
                if user:
                    from database.models import UserPreference
                    pref = session.query(UserPreference).filter(
                        UserPreference.user_id == user.id,
                        UserPreference.key == "theme_mode",
                    ).first()
                    if pref:
                        pref.value = self._mode
                    else:
                        pref = UserPreference(user_id=user.id, key="theme_mode", value=self._mode)
                        session.add(pref)
                    session.commit()
        except Exception as ex:
            logger.debug("Could not persist theme preference: %s", ex)

        # Notify all active views
        for listener in list(self._listeners):
            try:
                try:
                    listener(is_dark_now)
                except TypeError:
                    listener()
            except Exception as ex:
                logger.debug("Listener theme update error: %s", ex)

        try:
            p.update()
        except Exception:
            pass

    def get_colors(self) -> dict:
        """Return active theme palette dictionary."""
        dark = self.is_dark()
        return {
            "is_dark": dark,
            "background": COLOR_BACKGROUND_DARK if dark else COLOR_BACKGROUND,
            "surface_card": COLOR_SURFACE_CARD_DARK if dark else COLOR_SURFACE_CARD,
            "surface_low": COLOR_SURFACE_LOW_DARK if dark else COLOR_SURFACE_LOW,
            "surface_container": COLOR_SURFACE_CONTAINER_DARK if dark else COLOR_SURFACE_CONTAINER,
            "on_surface": COLOR_ON_SURFACE_DARK if dark else COLOR_ON_SURFACE,
            "on_surface_variant": COLOR_ON_SURFACE_VARIANT_DARK if dark else COLOR_ON_SURFACE_VARIANT,
            "outline": COLOR_OUTLINE_DARK if dark else COLOR_OUTLINE,
            "outline_variant": COLOR_OUTLINE_VARIANT_DARK if dark else COLOR_OUTLINE_VARIANT,
            "primary": COLOR_PRIMARY_DARK if dark else COLOR_PRIMARY,
            "primary_container": COLOR_PRIMARY_CONTAINER_DARK if dark else COLOR_PRIMARY_CONTAINER,
            "secondary": COLOR_SECONDARY_DARK if dark else COLOR_SECONDARY,
            "tertiary": COLOR_TERTIARY_DARK if dark else COLOR_TERTIARY_CONTAINER,
            "tertiary_container": COLOR_TERTIARY_CONTAINER_DARK if dark else COLOR_TERTIARY_CONTAINER,
        }


# Global singleton instance
theme_manager = ThemeManager()
