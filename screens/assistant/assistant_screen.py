"""
Spendora — AI Assistant Screen (Phase 6 placeholder).
"""

from __future__ import annotations

from kivy.metrics import dp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.screen import MDScreen


class AssistantScreen(MDScreen):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.name = "assistant"
        self._build_ui()

    def _build_ui(self) -> None:
        root = MDBoxLayout(
            orientation="vertical",
            md_bg_color=self.theme_cls.backgroundColor,
            padding=[dp(24), dp(48), dp(24), dp(24)],
            spacing=dp(16),
        )
        root.add_widget(MDLabel(
            text="AI Assistant",
            font_style="Display",
            role="small",
            adaptive_height=True,
        ))
        root.add_widget(MDLabel(
            text="Your AI financial assistant is coming in Phase 6.\n\n"
                 "You'll be able to ask:\n"
                 "• 'How much did I spend on food this month?'\n"
                 "• 'What was my biggest expense last month?'\n"
                 "• 'Compare August and September'\n"
                 "• 'Where am I spending the most?'",
            font_style="Body",
            role="large",
            adaptive_height=True,
            theme_text_color="Secondary",
        ))
        self.add_widget(root)

