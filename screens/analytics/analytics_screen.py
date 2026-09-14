"""
Spendora — Analytics Screen (Phase 4 placeholder).
"""

from __future__ import annotations

from kivy.metrics import dp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.screen import MDScreen


class AnalyticsScreen(MDScreen):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.name = "analytics"
        self._build_ui()

    def _build_ui(self) -> None:
        root = MDBoxLayout(
            orientation="vertical",
            md_bg_color=self.theme_cls.backgroundColor,
            padding=[dp(24), dp(48), dp(24), dp(24)],
            spacing=dp(16),
        )
        root.add_widget(MDLabel(
            text="Analytics",
            font_style="Display",
            role="small",
            adaptive_height=True,
        ))
        root.add_widget(MDLabel(
            text="Charts and financial analytics are coming in Phase 4.\n\n"
                 "You'll see:\n"
                 "• Income vs Expense charts\n"
                 "• Category breakdown\n"
                 "• Spending trends\n"
                 "• Custom date ranges",
            font_style="Body",
            role="large",
            adaptive_height=True,
            theme_text_color="Secondary",
        ))
        self.add_widget(root)

