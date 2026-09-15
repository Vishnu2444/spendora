"""
Spendora — Category Setup Screen (Onboarding Screen 2 of 2).

Displays AI/system-suggested categories based on the user's profession.
User can accept, reject, rename, or add custom categories.

Nothing is written to the database until the user taps "Save & Continue".
"""

from __future__ import annotations

import logging
from typing import List, Optional

from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.scrollview import ScrollView
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDButton, MDButtonText, MDIconButton
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.screen import MDScreen
from kivymd.uix.snackbar import MDSnackbar, MDSnackbarText

from database.models import CategorySource, User
from services.category_service import CategoryService
from services.profile_service import ProfileService
from services.ai_service import AIService

logger = logging.getLogger(__name__)


class _CategoryChip(MDCard):
    """
    A selectable card representing a single suggested category.

    Visual state:
        - Selected (green tint)  → will be accepted
        - Deselected (grey tint) → will be rejected
    """

    def __init__(self, suggestion: dict, **kwargs) -> None:
        super().__init__(
            style="elevated",
            padding=[dp(12), dp(10), dp(12), dp(10)],
            **kwargs,
        )
        self.suggestion = suggestion
        self.selected: bool = True  # Default: accept the suggestion.
        self._build()
        self._update_visual()

    def _build(self) -> None:
        layout = MDBoxLayout(orientation="horizontal", spacing=dp(8), adaptive_height=True)

        self._name_label = MDLabel(
            text=self.suggestion.get("name", ""),
            font_style="Body",
            role="large",
            adaptive_height=True,
        )

        subs = self.suggestion.get("subcategories", [])
        if subs:
            sub_text = ", ".join(subs[:3])
            if len(subs) > 3:
                sub_text += f" +{len(subs) - 3} more"
            self._sub_label = MDLabel(
                text=sub_text,
                font_style="Body",
                role="small",
                adaptive_height=True,
                theme_text_color="Secondary",
            )
        else:
            self._sub_label = MDLabel(text="", adaptive_height=True)

        col = MDBoxLayout(orientation="vertical", adaptive_height=True, spacing=dp(2))
        col.add_widget(self._name_label)
        col.add_widget(self._sub_label)
        layout.add_widget(col)

        self._toggle_btn = MDIconButton(
            icon="check-circle" if self.selected else "circle-outline",
            on_release=self.toggle,
        )
        layout.add_widget(self._toggle_btn)
        self.add_widget(layout)

    def toggle(self, *args) -> None:
        self.selected = not self.selected
        self._update_visual()

    def _update_visual(self) -> None:
        if self.selected:
            self._toggle_btn.icon = "check-circle"
            self.md_bg_color = (0.15, 0.8, 0.4, 0.15)
        else:
            self._toggle_btn.icon = "circle-outline"
            self.md_bg_color = (0.5, 0.5, 0.5, 0.1)


class CategorySetupScreen(MDScreen):
    """
    Onboarding Screen 2: Show suggested categories, allow accept/reject.

    Usage: the WelcomeScreen calls set_user(user) before navigating here.
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.name = "category_setup"
        self._category_service = CategoryService()
        self._profile_service = ProfileService()
        self._user: Optional[User] = None
        self._chips: List[_CategoryChip] = []
        self._build_ui()

    def set_user(self, user: User) -> None:
        """Called by WelcomeScreen to pass the newly created user."""
        self._user = user
        # Load suggestions for the user's profession.
        Clock.schedule_once(lambda dt: self._load_suggestions(), 0)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = MDBoxLayout(
            orientation="vertical",
            md_bg_color=self.theme_cls.backgroundColor,
        )

        scroll = ScrollView()
        self._content = MDBoxLayout(
            orientation="vertical",
            adaptive_height=True,
            padding=[dp(24), dp(48), dp(24), dp(32)],
            spacing=dp(16),
        )

        # Header
        self._content.add_widget(MDLabel(
            text="Your Expense Categories",
            font_style="Display",
            role="small",
            halign="left",
            adaptive_height=True,
        ))
        self._subtitle = MDLabel(
            text="Based on your profile, these categories may be useful.\nSelect the ones you want to keep.",
            font_style="Body",
            role="large",
            halign="left",
            adaptive_height=True,
            theme_text_color="Secondary",
        )
        self._content.add_widget(self._subtitle)

        # Chips container
        self._chips_container = MDBoxLayout(
            orientation="vertical",
            adaptive_height=True,
            spacing=dp(10),
            padding=[0, dp(8), 0, dp(8)],
        )
        self._content.add_widget(self._chips_container)

        # Select all / deselect all
        action_row = MDBoxLayout(
            orientation="horizontal",
            adaptive_height=True,
            spacing=dp(12),
        )
        select_all_btn = MDButton(
            style="text",
            on_release=self._select_all,
        )
        select_all_btn.add_widget(MDButtonText(text="Select All"))
        deselect_all_btn = MDButton(
            style="text",
            on_release=self._deselect_all,
        )
        deselect_all_btn.add_widget(MDButtonText(text="Deselect All"))
        action_row.add_widget(select_all_btn)
        action_row.add_widget(deselect_all_btn)
        self._content.add_widget(action_row)

        # Save button
        save_btn = MDButton(
            style="filled",
            on_release=self._on_save,
        )
        save_btn.add_widget(MDButtonText(text="Save & Start Using Spendora"))
        self._content.add_widget(save_btn)

        # Skip button
        skip_btn = MDButton(
            style="text",
            on_release=self._on_skip,
        )
        skip_btn.add_widget(MDButtonText(text="Skip — I'll set up categories later"))
        self._content.add_widget(skip_btn)

        scroll.add_widget(self._content)
        root.add_widget(scroll)
        self.add_widget(root)

    # ------------------------------------------------------------------
    # Suggestion loading
    # ------------------------------------------------------------------

    def _load_suggestions(self) -> None:
        """Load and render suggestion chips for the user's profession."""
        if self._user is None:
            return

        self._chips_container.clear_widgets()
        self._chips = []

        ai_service = AIService()
        suggestions = ai_service.predict_categories(
            profession=self._user.profession,
            custom_profession=self._user.profession_custom,
        )

        if not suggestions:
            self._chips_container.add_widget(MDLabel(
                text="No suggestions available. You can create categories from the Personalization screen.",
                font_style="Body",
                role="medium",
                adaptive_height=True,
                theme_text_color="Secondary",
            ))
            return

        for suggestion in suggestions:
            chip = _CategoryChip(suggestion=suggestion, size_hint_y=None, height=dp(64))
            self._chips.append(chip)
            self._chips_container.add_widget(chip)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _select_all(self, *args) -> None:
        for chip in self._chips:
            if not chip.selected:
                chip.toggle()

    def _deselect_all(self, *args) -> None:
        for chip in self._chips:
            if chip.selected:
                chip.toggle()

    def _on_save(self, *args) -> None:
        """Accept selected categories and navigate to the main app."""
        if self._user is None:
            self._show_error("User not found. Please restart the app.")
            return

        accepted = [chip.suggestion for chip in self._chips if chip.selected]

        try:
            if accepted:
                source = CategorySource.AI if AIService().is_configured() else CategorySource.SYSTEM
                self._category_service.accept_suggestions(
                    user_id=self._user.id,
                    accepted_suggestions=accepted,
                    source=source,
                )
            self._profile_service.mark_onboarding_complete(self._user.id)
        except Exception as exc:
            logger.error("Error saving categories: %s", exc)
            self._show_error("Could not save categories. Please try again.")
            return

        self._navigate_to_main()

    def _on_skip(self, *args) -> None:
        """Skip category setup — user can configure later."""
        if self._user is not None:
            try:
                self._profile_service.mark_onboarding_complete(self._user.id)
            except Exception as exc:
                logger.warning("Could not mark onboarding complete: %s", exc)
        self._navigate_to_main()

    def _navigate_to_main(self) -> None:
        """Switch to the main app navigation."""
        if self.manager:
            self.manager.current = "main"

    def _show_error(self, message: str) -> None:
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
        """Reload suggestions when re-entering (e.g. back navigation)."""
        if self._user is not None:
            self._load_suggestions()

