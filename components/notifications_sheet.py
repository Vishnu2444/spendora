"""
Spendora — Notifications & Activity Screen (Flet).

Matches Google Stitch Screen 8 "Notifications & Activity":
- Header: Back button, "Notifications", "Clear" pill
- Filter pills: All (10), Alerts (4), Transactions (6)
- Actionable notification cards:
  - AI Budget Warning: Food & Dining
  - Automatic UPI Detection: ₹550
  - Spendora Peer Insight
  - Salary Credited: ₹50,000
  - Upcoming Bill: AWS & GitHub Subscriptions
"""

from __future__ import annotations

from typing import Callable, Optional
import flet as ft

from config.settings import (
    COLOR_CORAL_ACCENT,
    COLOR_EMERALD_ACCENT,
    COLOR_ERROR,
    COLOR_ON_PRIMARY,
    COLOR_PRIMARY,
    COLOR_PRIMARY_CONTAINER,
    COLOR_SECONDARY,
)
from config.theme_manager import theme_manager


def show_notifications_dialog(page: ft.Page, switch_to_tab: Optional[Callable[[int], None]] = None) -> None:
    """Display the Stitch-styled Notifications & Activity sheet modal."""
    is_dark = theme_manager.is_dark()
    bg_color = "#0B0F19" if is_dark else "#FAF8FF"
    card_bg = "#151D30" if is_dark else "#FFFFFF"
    border_color = "#222E48" if is_dark else "#E2E8F0"
    text_primary = "#FFFFFF" if is_dark else "#151B2B"
    text_secondary = "#94A3B8" if is_dark else "#747688"
    accent_purple = "#8B5CF6" if is_dark else COLOR_PRIMARY

    def _close(e=None):
        dialog.open = False
        try:
            page.update()
        except Exception:
            pass

    # Filter chips
    chip_all = ft.Container(
        bgcolor=accent_purple,
        border_radius=16,
        padding=ft.Padding.symmetric(horizontal=12, vertical=6),
        ink=True,
        content=ft.Text("All (10)", size=11, weight=ft.FontWeight.W_700, color="#FFFFFF"),
    )
    chip_alerts = ft.Container(
        bgcolor=card_bg,
        border=ft.Border.all(1, border_color),
        border_radius=16,
        padding=ft.Padding.symmetric(horizontal=12, vertical=6),
        ink=True,
        content=ft.Text("Alerts (4)", size=11, weight=ft.FontWeight.W_500, color=text_primary),
    )
    chip_txns = ft.Container(
        bgcolor=card_bg,
        border=ft.Border.all(1, border_color),
        border_radius=16,
        padding=ft.Padding.symmetric(horizontal=12, vertical=6),
        ink=True,
        content=ft.Text("Transactions (6)", size=11, weight=ft.FontWeight.W_500, color=text_primary),
    )

    def _notification_card(
        icon: str,
        icon_color: str,
        title: str,
        message: str,
        badge_text: Optional[str] = None,
        badge_color: str = accent_purple,
        primary_btn: Optional[str] = None,
        secondary_btn: Optional[str] = None,
        timestamp: Optional[str] = None,
    ) -> ft.Container:
        action_buttons = []
        if secondary_btn:
            action_buttons.append(
                ft.Container(
                    bgcolor=border_color,
                    border_radius=8,
                    padding=ft.Padding.symmetric(horizontal=10, vertical=5),
                    ink=True,
                    content=ft.Text(secondary_btn, size=10, weight=ft.FontWeight.W_600, color=text_primary),
                    on_click=lambda e: _close(),
                )
            )
        if primary_btn:
            action_buttons.append(
                ft.Container(
                    bgcolor=f"{icon_color}22",
                    border=ft.Border.all(1, f"{icon_color}55"),
                    border_radius=8,
                    padding=ft.Padding.symmetric(horizontal=10, vertical=5),
                    ink=True,
                    content=ft.Text(primary_btn, size=10, weight=ft.FontWeight.W_700, color=icon_color),
                    on_click=lambda e: _close(),
                )
            )

        return ft.Container(
            bgcolor=card_bg,
            border=ft.Border.all(1, border_color),
            border_radius=18,
            padding=ft.Padding.all(14),
            content=ft.Column(
                spacing=8,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Row(
                                spacing=10,
                                controls=[
                                    ft.Container(
                                        width=34,
                                        height=34,
                                        border_radius=10,
                                        bgcolor=f"{icon_color}22",
                                        alignment=ft.Alignment.CENTER,
                                        content=ft.Icon(icon, color=icon_color, size=18),
                                    ),
                                    ft.Column(
                                        spacing=1,
                                        controls=[
                                            ft.Text(title, size=13, weight=ft.FontWeight.W_700, color=text_primary),
                                            ft.Text(timestamp or "Just now", size=10, color=text_secondary),
                                        ],
                                    ),
                                ],
                            ),
                            ft.Container(
                                bgcolor=f"{badge_color}22" if badge_text else None,
                                border_radius=8,
                                padding=ft.Padding.symmetric(horizontal=6, vertical=2) if badge_text else ft.Padding.all(0),
                                content=ft.Text(badge_text or "", size=9, weight=ft.FontWeight.W_700, color=badge_color) if badge_text else ft.Container(),
                            ),
                        ],
                    ),
                    ft.Text(message, size=12, color=text_secondary),
                    ft.Row(spacing=8, controls=action_buttons) if action_buttons else ft.Container(),
                ],
            ),
        )

    # 5 Stitch Notification cards
    cards_list = [
        _notification_card(
            icon=ft.Icons.WARNING_AMBER_ROUNDED,
            icon_color=COLOR_CORAL_ACCENT,
            title="AI Budget Warning: Food & Dining",
            message="You have reached 86% of your monthly dining budget (₹8,450 spent). At this rate, budget exhausts in 4 days.",
            badge_text="CRITICAL",
            badge_color=COLOR_CORAL_ACCENT,
            primary_btn="Adjust Budget",
            secondary_btn="View Expenses",
            timestamp="TODAY • 11:30 AM",
        ),
        _notification_card(
            icon=ft.Icons.AUTO_AWESOME,
            icon_color="#38BDF8",
            title="Automatic UPI Detection: ₹550",
            message="Payment to Nature's Basket auto-categorized under Groceries at 11:30 AM.",
            badge_text="AUTO",
            badge_color="#38BDF8",
            primary_btn="Change Category",
            timestamp="1 hour ago",
        ),
        _notification_card(
            icon=ft.Icons.TRENDING_UP,
            icon_color=accent_purple,
            title="Spendora Peer Insight",
            message="Your tech spends are 18% lower than Bengaluru Software Engineers this month.",
            badge_text="INSIGHT",
            badge_color=accent_purple,
            timestamp="2 hours ago",
        ),
        _notification_card(
            icon=ft.Icons.ACCOUNT_BALANCE,
            icon_color=COLOR_EMERALD_ACCENT,
            title="Salary Credited: ₹50,000",
            message="HDFC Bank Account: ****7721. Real-time auto-allocated with monthly budget.",
            badge_text="INCOME",
            badge_color=COLOR_EMERALD_ACCENT,
            timestamp="YESTERDAY",
        ),
        _notification_card(
            icon=ft.Icons.CREDIT_CARD,
            icon_color="#6366F1",
            title="Upcoming Bill: AWS & GitHub Subscriptions",
            message="₹4,200 due on 1st of next month. Funds allocated in software reserve.",
            badge_text="RECURRING",
            badge_color="#6366F1",
            timestamp="IN 3 DAYS",
        ),
    ]

    dialog = ft.AlertDialog(
        modal=True,
        bgcolor=bg_color,
        content_padding=ft.Padding.all(16),
        shape=ft.RoundedRectangleBorder(radius=24),
        content=ft.Container(
            width=420,
            height=620,
            content=ft.Column(
                spacing=12,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Row(
                                spacing=8,
                                controls=[
                                    ft.IconButton(ft.Icons.CLOSE, icon_color=text_primary, icon_size=20, on_click=_close),
                                    ft.Text("Notifications", size=18, weight=ft.FontWeight.W_800, color=text_primary),
                                ],
                            ),
                            ft.Container(
                                bgcolor=border_color,
                                border_radius=12,
                                padding=ft.Padding.symmetric(horizontal=10, vertical=4),
                                ink=True,
                                on_click=lambda e: _close(),
                                content=ft.Text("Clear", size=11, weight=ft.FontWeight.W_700, color=accent_purple),
                            ),
                        ],
                    ),
                    ft.Row(spacing=8, controls=[chip_all, chip_alerts, chip_txns]),
                    ft.Container(
                        expand=True,
                        content=ft.ListView(
                            spacing=12,
                            controls=cards_list,
                        ),
                    ),
                ],
            ),
        ),
    )

    page.overlay.append(dialog)
    dialog.open = True
    try:
        page.update()
    except Exception:
        pass
