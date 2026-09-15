"""
Spendora — CategoryManagementCard component.

An interactive card in the Personalization screen for managing a category:
- Icon, color badge, and name
- Source badge (USER / SYSTEM / AI)
- Subcategories display with deletion chips
- Quick actions: Add Subcategory, Edit, Delete
"""

from __future__ import annotations

from typing import Callable, Optional

from kivy.metrics import dp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDButton, MDButtonText
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel

from config.settings import (
    APP_BG_CARD,
    APP_DANGER,
    APP_MUTED_TEXT,
    APP_TEXT,
)
from database.models import Category


class CategoryManagementCard(MDCard):
    """Card for category display, subcategory listing, and management actions."""

    def __init__(
        self,
        category: Category,
        on_edit: Optional[Callable[[Category], None]] = None,
        on_delete: Optional[Callable[[Category], None]] = None,
        on_add_subcategory: Optional[Callable[[Category], None]] = None,
        on_delete_subcategory: Optional[Callable[[int], None]] = None,
        **kwargs,
    ) -> None:
        super().__init__(
            style="filled",
            md_bg_color=APP_BG_CARD,
            radius=[dp(14)],
            padding=[dp(14), dp(12), dp(14), dp(12)],
            size_hint_y=None,
            **kwargs,
        )
        self.category = category
        self._on_edit = on_edit
        self._on_delete = on_delete
        self._on_add_subcategory = on_add_subcategory
        self._on_delete_subcategory = on_delete_subcategory

        # Calculate height based on subcategories
        has_subs = bool(category.subcategories)
        self.height = dp(115) if has_subs else dp(74)

        self._build()

    def _build(self) -> None:
        layout = MDBoxLayout(orientation="vertical", spacing=dp(8))

        # Top row: Category badge, name, source, and action buttons
        top_row = MDBoxLayout(orientation="horizontal", adaptive_height=True, spacing=dp(8))

        color_hex = self.category.color or "#4ECDC4"
        icon_box = MDCard(
            style="filled",
            md_bg_color=self._hex_to_rgba(color_hex, alpha=0.2),
            size_hint=(None, None),
            size=(dp(34), dp(34)),
            radius=[dp(17)],
            pos_hint={"center_y": 0.5},
        )
        icon_box.add_widget(
            MDLabel(
                text=self._icon_char(self.category.icon or "tag"),
                halign="center",
                valign="middle",
                theme_text_color="Custom",
                text_color=self._hex_to_rgba(color_hex, alpha=1.0),
                font_style="Title",
                role="medium",
            )
        )
        top_row.add_widget(icon_box)

        # Name and source label
        name_box = MDBoxLayout(orientation="vertical", adaptive_height=True, spacing=dp(1), pos_hint={"center_y": 0.5})
        name_box.add_widget(
            MDLabel(
                text=self.category.name,
                font_style="Body",
                role="large",
                adaptive_height=True,
                theme_text_color="Custom",
                text_color=APP_TEXT,
            )
        )

        source_text = self.category.source.value if hasattr(self.category.source, "value") else str(self.category.source)
        name_box.add_widget(
            MDLabel(
                text=source_text,
                font_style="Label",
                role="small",
                adaptive_height=True,
                theme_text_color="Custom",
                text_color=APP_MUTED_TEXT,
            )
        )
        top_row.add_widget(name_box)

        top_row.add_widget(MDBoxLayout())  # Spacer

        # Add Subcategory button
        add_sub_btn = MDButton(
            style="text",
            on_release=lambda *_: self._on_add_subcategory(self.category) if self._on_add_subcategory else None,
            pos_hint={"center_y": 0.5},
        )
        add_sub_btn.add_widget(MDButtonText(text="+ Sub", font_style="Label", role="small"))
        top_row.add_widget(add_sub_btn)

        # Edit button
        edit_btn = MDButton(
            style="text",
            on_release=lambda *_: self._on_edit(self.category) if self._on_edit else None,
            pos_hint={"center_y": 0.5},
        )
        edit_btn.add_widget(MDButtonText(text="✎", font_style="Label", role="medium"))
        top_row.add_widget(edit_btn)

        # Delete button
        del_btn = MDButton(
            style="text",
            on_release=lambda *_: self._on_delete(self.category) if self._on_delete else None,
            pos_hint={"center_y": 0.5},
        )
        del_btn.add_widget(
            MDButtonText(
                text="✕",
                font_style="Label",
                role="medium",
                theme_text_color="Custom",
                text_color=APP_DANGER,
            )
        )
        top_row.add_widget(del_btn)

        layout.add_widget(top_row)

        # Subcategories row (if any)
        if self.category.subcategories:
            sub_row = MDBoxLayout(
                orientation="horizontal",
                adaptive_height=True,
                spacing=dp(6),
                padding=[dp(42), dp(2), dp(4), dp(2)],
            )
            for sub in self.category.subcategories:
                sub_chip = MDCard(
                    style="filled",
                    md_bg_color=(0.18, 0.22, 0.32, 0.8),
                    radius=[dp(8)],
                    size_hint=(None, None),
                    height=dp(26),
                    padding=[dp(8), dp(2), dp(6), dp(2)],
                )
                chip_box = MDBoxLayout(orientation="horizontal", spacing=dp(4), adaptive_width=True)
                chip_box.add_widget(
                    MDLabel(
                        text=sub.name,
                        font_style="Body",
                        role="small",
                        theme_text_color="Custom",
                        text_color=APP_TEXT,
                        adaptive_width=True,
                    )
                )

                del_sub = MDLabel(
                    text="×",
                    font_style="Label",
                    role="small",
                    theme_text_color="Custom",
                    text_color=APP_MUTED_TEXT,
                    adaptive_width=True,
                )
                chip_box.add_widget(del_sub)
                sub_chip.add_widget(chip_box)

                # Bind tap on subcategory chip to delete subcategory
                sub_chip.bind(on_release=lambda *_, s_id=sub.id: self._handle_delete_sub(s_id))
                sub_row.add_widget(sub_chip)

            layout.add_widget(sub_row)

        self.add_widget(layout)

    def _handle_delete_sub(self, sub_id: int) -> None:
        if self._on_delete_subcategory:
            self._on_delete_subcategory(sub_id)

    @staticmethod
    def _hex_to_rgba(hex_str: str, alpha: float = 1.0) -> tuple:
        hex_str = hex_str.lstrip("#")
        if len(hex_str) != 6:
            return (0.5, 0.5, 0.5, alpha)
        r = int(hex_str[0:2], 16) / 255.0
        g = int(hex_str[2:4], 16) / 255.0
        b = int(hex_str[4:6], 16) / 255.0
        return (r, g, b, alpha)

    @staticmethod
    def _icon_char(icon_name: str) -> str:
        _MAP = {
            "food": "🍽",
            "car": "🚗",
            "train": "🚆",
            "bus": "🚌",
            "home": "🏠",
            "laptop": "💻",
            "book-open-variant": "📚",
            "television-play": "🎬",
            "shopping": "🛍",
            "heart-pulse": "❤",
            "lightning-bolt": "⚡",
            "piggy-bank": "🐷",
            "wifi": "📶",
            "briefcase": "💼",
            "cash": "💰",
            "tag": "🏷",
        }
        return _MAP.get(icon_name, "🏷")
