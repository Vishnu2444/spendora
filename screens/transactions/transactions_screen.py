"""
Spendora — Transactions Screen (Phase 1 placeholder).
Full transaction CRUD will be implemented in Phase 2.
"""

from __future__ import annotations

from kivy.metrics import dp
from kivy.uix.scrollview import ScrollView
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.screen import MDScreen


class TransactionsScreen(MDScreen):
    """Transactions list screen — Phase 2 will implement full CRUD."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.name = "transactions"
        self._build_ui()

    def _build_ui(self) -> None:
        root = MDBoxLayout(
            orientation="vertical",
            md_bg_color=self.theme_cls.backgroundColor,
            padding=[dp(24), dp(48), dp(24), dp(24)],
            spacing=dp(16),
        )
        root.add_widget(MDLabel(
            text="Transactions",
            font_style="Display",
            role="small",
            adaptive_height=True,
        ))
        root.add_widget(MDLabel(
            text="Transaction management is coming in Phase 2.\n\n"
                 "You'll be able to:\n"
                 "• Add income and expenses\n"
                 "• Edit and delete transactions\n"
                 "• Filter by category and date\n"
                 "• Search transactions",
            font_style="Body",
            role="large",
            adaptive_height=True,
            theme_text_color="Secondary",
        ))
        self.add_widget(root)

