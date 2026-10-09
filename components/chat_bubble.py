"""
Spendora (Trackz) — ChatBubble component (Flet).

Matches Google Stitch AI Advisor design:
- Assistant bubble in soft `#EAEDFF` container with smart_toy icon
- User bubble in deep `#064E3B` container with white text
"""

from __future__ import annotations

from typing import Callable, List, Optional
import flet as ft

from config.settings import (
    COLOR_EMERALD_ACCENT,
    COLOR_ON_PRIMARY,
    COLOR_ON_SURFACE,
    COLOR_OUTLINE_VARIANT,
    COLOR_PRIMARY,
    COLOR_PRIMARY_CONTAINER,
    COLOR_SECONDARY,
    COLOR_SURFACE_CARD,
    COLOR_SURFACE_CONTAINER,
)


def build_chat_bubble(
    text: str,
    is_user: bool = False,
    timestamp: str = "",
    action_badge: Optional[str] = None,
    suggested_chips: Optional[List[str]] = None,
    on_chip_click: Optional[Callable[[str], None]] = None,
) -> ft.Row:
    """Build a Stitch-styled chat bubble for the Spendora AI Financial Advisor."""
    if is_user:
        bubble = ft.Container(
            bgcolor=COLOR_PRIMARY_CONTAINER,
            border_radius=ft.BorderRadius.only(
                top_left=16, top_right=16, bottom_left=16, bottom_right=4,
            ),
            padding=ft.Padding.symmetric(horizontal=16, vertical=12),
            content=ft.Column(
                spacing=4,
                controls=[
                    ft.Text(
                        text,
                        color=COLOR_ON_PRIMARY,
                        size=14,
                        weight=ft.FontWeight.W_400,
                    ),
                    *(
                        [
                            ft.Text(
                                timestamp,
                                color=f"{COLOR_ON_PRIMARY}AA",
                                size=11,
                                text_align=ft.TextAlign.RIGHT,
                            )
                        ]
                        if timestamp
                        else []
                    ),
                ],
            ),
        )
        return ft.Row(
            alignment=ft.MainAxisAlignment.END,
            vertical_alignment=ft.CrossAxisAlignment.END,
            controls=[
                ft.Container(expand=True),
                bubble,
            ],
        )
    else:
        from config.theme_manager import theme_manager
        is_dark = theme_manager.is_dark()
        avatar = ft.Container(
            width=36,
            height=36,
            border_radius=18,
            bgcolor="#222B3D" if is_dark else COLOR_SURFACE_CONTAINER,
            border=ft.Border.all(1, "#334155" if is_dark else COLOR_OUTLINE_VARIANT),
            alignment=ft.Alignment.CENTER,
            content=ft.Icon(ft.Icons.AUTO_AWESOME, color="#C0C1FF" if is_dark else COLOR_PRIMARY, size=18),
        )

        header_controls = [
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Row(
                        spacing=6,
                        controls=[
                            ft.Text(
                                "Spendora AI",
                                color=COLOR_PRIMARY,
                                size=12,
                                weight=ft.FontWeight.W_700,
                            ),
                            ft.Container(
                                bgcolor=f"{COLOR_PRIMARY}18",
                                border_radius=6,
                                padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                                content=ft.Text("CONCIERGE", size=9, weight=ft.FontWeight.W_800, color=COLOR_PRIMARY),
                            ),
                        ],
                    ),
                    *(
                        [
                            ft.Text(
                                timestamp,
                                color=COLOR_SECONDARY,
                                size=11,
                            )
                        ]
                        if timestamp
                        else []
                    ),
                ],
            )
        ]

        # Optional action badge (e.g. "✅ Logged to Ledger")
        badge_controls = []
        if action_badge:
            badge_controls.append(
                ft.Container(
                    bgcolor=f"{COLOR_EMERALD_ACCENT}18",
                    border=ft.Border.all(1, f"{COLOR_EMERALD_ACCENT}40"),
                    border_radius=8,
                    padding=ft.Padding.symmetric(horizontal=8, vertical=3),
                    content=ft.Text(action_badge, size=11, weight=ft.FontWeight.W_700, color=COLOR_EMERALD_ACCENT),
                )
            )

        # Markdown body
        body_control = ft.Markdown(
            text,
            selectable=True,
            extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
        )

        # Optional suggested chips
        chips_controls = []
        if suggested_chips and on_chip_click:
            chips_list = []
            for chip_text in suggested_chips:
                def _make_click(ct=chip_text):
                    return lambda e: on_chip_click(ct)

                chips_list.append(
                    ft.Container(
                        bgcolor=COLOR_SURFACE_CARD,
                        border=ft.Border.all(1, COLOR_OUTLINE_VARIANT),
                        border_radius=16,
                        padding=ft.Padding.symmetric(horizontal=10, vertical=6),
                        ink=True,
                        on_click=_make_click(),
                        content=ft.Text(chip_text, size=11, weight=ft.FontWeight.W_600, color=COLOR_PRIMARY),
                    )
                )

            chips_controls.append(
                ft.Container(
                    padding=ft.Padding.only(top=6),
                    content=ft.Row(
                        scroll=ft.ScrollMode.HIDDEN,
                        spacing=6,
                        controls=chips_list,
                    ),
                )
            )

        bubble = ft.Container(
            bgcolor="#1C2333" if is_dark else COLOR_SURFACE_CONTAINER,
            border=ft.Border.all(1, "#262E40" if is_dark else COLOR_OUTLINE_VARIANT),
            border_radius=ft.BorderRadius.only(
                top_left=16, top_right=16, bottom_left=4, bottom_right=16,
            ),
            padding=ft.Padding.symmetric(horizontal=16, vertical=12),
            content=ft.Column(
                spacing=8,
                controls=[
                    *header_controls,
                    *badge_controls,
                    body_control,
                    *chips_controls,
                ],
            ),
        )

        return ft.Row(
            alignment=ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.START,
            spacing=10,
            controls=[
                avatar,
                ft.Container(content=bubble, expand=True),
            ],
        )
