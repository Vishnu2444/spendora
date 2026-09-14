"""
Spendora — Personalization Screen (Phase 3 placeholder).
"""

from __future__ import annotations

from kivy.metrics import dp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.screen import MDScreen


class PersonalizationScreen(MDScreen):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.name = "personalization"
        self._build_ui()

    def _build_ui(self) -> None:
        root = MDBoxLayout(
            orientation="vertical",
            md_bg_color=self.theme_cls.backgroundColor,
            padding=[dp(24), dp(48), dp(24), dp(24)],
            spacing=dp(16),
        )
        root.add_widget(MDLabel(
            text="Personalization",
            font_style="Display",
            role="small",
            adaptive_height=True,
        ))
        root.add_widget(MDLabel(
            text="Category management is coming in Phase 3.\n\n"
                 "You'll be able to:\n"
                 "• View all your categories\n"
                 "• Add, rename, delete categories\n"
                 "• Manage subcategories\n"
                 "• Customise icons and colours",
            font_style="Body",
            role="large",
            adaptive_height=True,
            theme_text_color="Secondary",
        ))
        self.add_widget(root)

