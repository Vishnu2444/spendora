"""
Spendora — ChatBubble component.

Renders user and assistant conversational message bubbles.
"""

from __future__ import annotations

from kivy.metrics import dp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel

from config.settings import (
    APP_BG_CARD,
    APP_MUTED_TEXT,
    APP_TEXT,
)


class ChatBubble(MDBoxLayout):
    """Chat message bubble for user or AI assistant."""

    def __init__(
        self,
        text: str,
        is_user: bool = False,
        timestamp: str = "",
        **kwargs,
    ) -> None:
        super().__init__(
            orientation="horizontal",
            adaptive_height=True,
            spacing=dp(8),
            padding=[dp(4), dp(4), dp(4), dp(4)],
            **kwargs,
        )
        self.is_user = is_user
        self._build(text, is_user, timestamp)

    def _build(self, text: str, is_user: bool, timestamp: str) -> None:
        if is_user:
            self.add_widget(MDBoxLayout())  # Left spacer to push user bubble right

            bubble = MDCard(
                style="filled",
                md_bg_color=(0.35, 0.28, 0.58, 0.95),
                radius=[dp(16), dp(16), dp(4), dp(16)],
                padding=[dp(14), dp(10), dp(14), dp(10)],
                size_hint_x=0.82,
                adaptive_height=True,
            )
            inner = MDBoxLayout(orientation="vertical", adaptive_height=True, spacing=dp(4))
            lbl = MDLabel(
                text=text,
                font_style="Body",
                role="medium",
                adaptive_height=True,
                theme_text_color="Custom",
                text_color=APP_TEXT,
            )
            inner.add_widget(lbl)

            if timestamp:
                time_lbl = MDLabel(
                    text=timestamp,
                    font_style="Label",
                    role="small",
                    adaptive_height=True,
                    halign="right",
                    theme_text_color="Custom",
                    text_color=(0.85, 0.82, 0.95, 0.8),
                )
                inner.add_widget(time_lbl)

            bubble.add_widget(inner)
            self.add_widget(bubble)

        else:
            # Assistant bubble (aligned left with avatar)
            avatar = MDCard(
                style="filled",
                md_bg_color=(0.25, 0.25, 0.38, 1),
                size_hint=(None, None),
                size=(dp(32), dp(32)),
                radius=[dp(16)],
                pos_hint={"top": 1},
            )
            avatar.add_widget(
                MDLabel(
                    text="✦",
                    halign="center",
                    valign="middle",
                    font_style="Title",
                    role="small",
                    theme_text_color="Custom",
                    text_color=(0.65, 0.55, 0.95, 1),
                )
            )
            self.add_widget(avatar)

            bubble = MDCard(
                style="filled",
                md_bg_color=APP_BG_CARD,
                radius=[dp(16), dp(16), dp(16), dp(4)],
                padding=[dp(14), dp(12), dp(14), dp(12)],
                size_hint_x=0.84,
                adaptive_height=True,
            )
            inner = MDBoxLayout(orientation="vertical", adaptive_height=True, spacing=dp(4))

            sender_lbl = MDLabel(
                text="Spendora Assistant",
                font_style="Label",
                role="medium",
                adaptive_height=True,
                theme_text_color="Custom",
                text_color=(0.65, 0.55, 0.95, 1),
            )
            inner.add_widget(sender_lbl)

            msg_lbl = MDLabel(
                text=text,
                font_style="Body",
                role="medium",
                adaptive_height=True,
                theme_text_color="Custom",
                text_color=APP_TEXT,
            )
            inner.add_widget(msg_lbl)

            if timestamp:
                time_lbl = MDLabel(
                    text=timestamp,
                    font_style="Label",
                    role="small",
                    adaptive_height=True,
                    theme_text_color="Custom",
                    text_color=APP_MUTED_TEXT,
                )
                inner.add_widget(time_lbl)

            bubble.add_widget(inner)
            self.add_widget(bubble)

            self.add_widget(MDBoxLayout())  # Right spacer

