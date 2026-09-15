"""
Spendora — AI Financial Assistant Screen.

Natural language conversational interface powered by Google Gemini (gemini-3.8-flash)
and grounded strictly in verified financial records computed by the calculation engine.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.scrollview import ScrollView
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDButton, MDButtonText
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.screen import MDScreen
from kivymd.uix.textfield import MDTextField, MDTextFieldHintText

from components.chat_bubble import ChatBubble
from config.settings import (
    APP_ACCENT,
    APP_BG_CARD,
    APP_BG_DARK,
    APP_MUTED_TEXT,
    APP_SUCCESS,
    APP_TEXT,
)
from database.models import User
from services.ai_service import AIService
from services.profile_service import ProfileService

logger = logging.getLogger(__name__)


class AssistantScreen(MDScreen):
    """Conversational financial assistant screen."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.name = "assistant"
        self._ai_service = AIService()
        self._profile_service = ProfileService()
        self._user: Optional[User] = None
        self._is_busy = False
        self._has_initialized_chat = False
        self._build_ui()

    def _build_ui(self) -> None:
        root = MDBoxLayout(orientation="vertical", md_bg_color=APP_BG_DARK)

        # --- Top Header ---
        top_bar = MDBoxLayout(
            orientation="horizontal",
            adaptive_height=True,
            padding=[dp(18), dp(16), dp(18), dp(8)],
            spacing=dp(10),
        )

        sparkle = MDCard(
            style="filled",
            md_bg_color=(0.28, 0.24, 0.45, 1),
            size_hint=(None, None),
            size=(dp(36), dp(36)),
            radius=[dp(18)],
            pos_hint={"center_y": 0.5},
        )
        sparkle.add_widget(
            MDLabel(
                text="✦",
                halign="center",
                valign="middle",
                theme_text_color="Custom",
                text_color=(0.75, 0.65, 1, 1),
                font_style="Title",
                role="medium",
            )
        )
        top_bar.add_widget(sparkle)

        title_box = MDBoxLayout(orientation="vertical", adaptive_height=True, spacing=dp(2), pos_hint={"center_y": 0.5})
        title_box.add_widget(
            MDLabel(
                text="AI Assistant",
                font_style="Headline",
                role="small",
                adaptive_height=True,
                theme_text_color="Custom",
                text_color=APP_TEXT,
            )
        )
        self._status_sub = MDLabel(
            text="Powered by Gemini",
            font_style="Body",
            role="small",
            adaptive_height=True,
            theme_text_color="Custom",
            text_color=APP_MUTED_TEXT,
        )
        title_box.add_widget(self._status_sub)
        top_bar.add_widget(title_box)

        top_bar.add_widget(MDBoxLayout())  # Spacer

        self._mode_badge = MDCard(
            style="filled",
            md_bg_color=(0.18, 0.25, 0.35, 0.8),
            radius=[dp(8)],
            size_hint=(None, None),
            size=(dp(90), dp(28)),
            pos_hint={"center_y": 0.5},
        )
        self._mode_lbl = MDLabel(
            text="AI Online" if self._ai_service.is_configured() else "Local Mode",
            halign="center",
            valign="middle",
            font_style="Label",
            role="small",
            theme_text_color="Custom",
            text_color=APP_SUCCESS if self._ai_service.is_configured() else APP_MUTED_TEXT,
        )
        self._mode_badge.add_widget(self._mode_lbl)
        top_bar.add_widget(self._mode_badge)

        root.add_widget(top_bar)

        # --- Chat Messages ScrollView ---
        self._scroll = ScrollView(do_scroll_x=False)
        self._chat_layout = MDBoxLayout(
            orientation="vertical",
            adaptive_height=True,
            padding=[dp(16), dp(10), dp(16), dp(16)],
            spacing=dp(12),
        )
        self._scroll.add_widget(self._chat_layout)
        root.add_widget(self._scroll)

        # --- Thinking / Loading Indicator ---
        self._loading_card = MDCard(
            style="filled",
            md_bg_color=APP_BG_CARD,
            radius=[dp(10)],
            padding=[dp(14), dp(8), dp(14), dp(8)],
            size_hint_y=None,
            height=dp(0),
            opacity=0,
        )
        self._loading_lbl = MDLabel(
            text="✦ Spendora is analyzing your financial records...",
            font_style="Body",
            role="small",
            theme_text_color="Custom",
            text_color=(0.7, 0.6, 0.95, 1),
            adaptive_height=True,
        )
        self._loading_card.add_widget(self._loading_lbl)
        root.add_widget(self._loading_card)

        # --- Quick Prompts Row ---
        quick_scroll = ScrollView(do_scroll_y=False, size_hint_y=None, height=dp(42))
        quick_box = MDBoxLayout(
            orientation="horizontal",
            adaptive_width=True,
            spacing=dp(8),
            padding=[dp(16), dp(4), dp(16), dp(4)],
        )

        prompts = [
            "How much did I spend this month?",
            "Am I spending more than I earn?",
            "Where am I spending the most?",
            "How can I optimize my savings?",
        ]
        for p in prompts:
            btn = MDButton(
                style="tonal",
                on_release=lambda *_, query=p: self._send_query(query),
            )
            btn.add_widget(MDButtonText(text=p, font_style="Label", role="small"))
            quick_box.add_widget(btn)

        quick_scroll.add_widget(quick_box)
        root.add_widget(quick_scroll)

        # --- Input Bar ---
        input_bar = MDBoxLayout(
            orientation="horizontal",
            adaptive_height=True,
            padding=[dp(16), dp(8), dp(16), dp(14)],
            spacing=dp(8),
        )

        self._input_field = MDTextField(
            MDTextFieldHintText(text="Ask about your finances..."),
            mode="outlined",
        )
        input_bar.add_widget(self._input_field)

        send_btn = MDButton(
            style="filled",
            on_release=lambda *_: self._handle_input_submit(),
            pos_hint={"center_y": 0.5},
        )
        send_btn.add_widget(MDButtonText(text="Send"))
        input_bar.add_widget(send_btn)

        root.add_widget(input_bar)
        self.add_widget(root)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_enter(self, *args) -> None:
        self._user = self._profile_service.get_current_user()
        is_conf = self._ai_service.is_configured()
        self._mode_lbl.text = "AI Online" if is_conf else "Local Mode"
        self._mode_lbl.text_color = APP_SUCCESS if is_conf else APP_MUTED_TEXT

        if not self._has_initialized_chat and self._user:
            self._has_initialized_chat = True
            welcome_msg = (
                f"Hello {self._user.name}! I'm your Spendora Financial Assistant.\n\n"
                "I analyze your actual income, expenses, and category distributions to give you "
                "personalized, data-grounded insights.\n\n"
                "Tap any suggestion below or ask me a question!"
            )
            self._add_assistant_message(welcome_msg)

    # ------------------------------------------------------------------
    # Messaging
    # ------------------------------------------------------------------

    def _handle_input_submit(self) -> None:
        text = self._input_field.text.strip()
        if not text:
            return
        self._input_field.text = ""
        self._send_query(text)

    def _send_query(self, query: str) -> None:
        if self._is_busy or not self._user:
            return

        # Add user message bubble
        now_time = datetime.now().strftime("%I:%M %p")
        self._chat_layout.add_widget(
            ChatBubble(text=query, is_user=True, timestamp=now_time)
        )
        self._scroll_to_bottom()

        # Show thinking indicator
        self._is_busy = True
        self._loading_card.opacity = 1
        self._loading_card.height = dp(36)

        # Process in background clock callback
        Clock.schedule_once(lambda dt: self._process_query(query), 0.1)

    def _process_query(self, query: str) -> None:
        try:
            answer = self._ai_service.query_financial_assistant(
                user_id=self._user.id,
                question=query,
            )
        except Exception as exc:
            logger.error("Assistant query processing error: %s", exc)
            answer = f"Sorry, I encountered an issue analyzing your records: {exc}"

        # Hide loading indicator
        self._loading_card.opacity = 0
        self._loading_card.height = dp(0)
        self._is_busy = False

        # Add assistant response bubble
        now_time = datetime.now().strftime("%I:%M %p")
        self._add_assistant_message(answer, timestamp=now_time)

    def _add_assistant_message(self, text: str, timestamp: str = "") -> None:
        if not timestamp:
            timestamp = datetime.now().strftime("%I:%M %p")
        bubble = ChatBubble(text=text, is_user=False, timestamp=timestamp)
        self._chat_layout.add_widget(bubble)
        self._scroll_to_bottom()

    def _scroll_to_bottom(self) -> None:
        Clock.schedule_once(lambda dt: setattr(self._scroll, "scroll_y", 0), 0.05)
