"""
Spendora — ColorPickerRow component.

A horizontal palette of selectable Material color swatches for custom categories.
"""

from __future__ import annotations

from typing import Callable, List, Optional

from kivy.metrics import dp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel

PALETTE: List[str] = [
    "#FF6B6B",  # Coral Red
    "#4ECDC4",  # Mint Teal
    "#45B7D1",  # Sky Blue
    "#F7DC6F",  # Sunflower Yellow
    "#BB8FCE",  # Lavender Purple
    "#82E0AA",  # Emerald Green
    "#F0B27A",  # Soft Orange
    "#5DADE2",  # Ocean Blue
    "#E91E63",  # Deep Pink
    "#9C27B0",  # Royal Purple
]


class ColorPickerRow(MDBoxLayout):
    """Horizontal row of circular color swatches with active selection indicator."""

    def __init__(
        self,
        selected_color: str = "#4ECDC4",
        on_color_selected: Optional[Callable[[str], None]] = None,
        **kwargs,
    ) -> None:
        super().__init__(
            orientation="horizontal",
            adaptive_height=True,
            spacing=dp(8),
            padding=[0, dp(4), 0, dp(4)],
            **kwargs,
        )
        self.selected_color = selected_color.upper()
        self._on_color_selected = on_color_selected
        self._swatches = {}
        self._build_swatches()

    def _build_swatches(self) -> None:
        self.clear_widgets()
        self._swatches.clear()

        for hex_color in PALETTE:
            is_selected = hex_color.upper() == self.selected_color

            swatch = MDCard(
                style="filled",
                md_bg_color=self._hex_to_rgba(hex_color),
                size_hint=(None, None),
                size=(dp(28), dp(28)),
                radius=[dp(14)],
                ripple_behavior=True,
            )
            swatch.bind(on_release=lambda *_, c=hex_color: self.select_color(c))

            if is_selected:
                swatch.add_widget(
                    MDLabel(
                        text="✓",
                        halign="center",
                        valign="middle",
                        theme_text_color="Custom",
                        text_color=(1, 1, 1, 1),
                        font_style="Title",
                        role="small",
                    )
                )

            self._swatches[hex_color.upper()] = swatch
            self.add_widget(swatch)

    def select_color(self, hex_color: str) -> None:
        """Update active selection and invoke callback."""
        self.selected_color = hex_color.upper()
        self._build_swatches()
        if self._on_color_selected:
            self._on_color_selected(self.selected_color)

    @staticmethod
    def _hex_to_rgba(hex_str: str) -> tuple:
        hex_str = hex_str.lstrip("#")
        if len(hex_str) != 6:
            return (0.5, 0.5, 0.5, 1.0)
        r = int(hex_str[0:2], 16) / 255.0
        g = int(hex_str[2:4], 16) / 255.0
        b = int(hex_str[4:6], 16) / 255.0
        return (r, g, b, 1.0)

