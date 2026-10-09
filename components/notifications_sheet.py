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

    # Load actual user data & transactions
    cards_list = []
    try:
        from services.profile_service import ProfileService
        from services.transaction_service import TransactionService
        from config.settings import DEFAULT_CURRENCY, CURRENCY_SYMBOLS
        from database.models import TransactionType

        prof_service = ProfileService()
        txn_service = TransactionService()
        user = prof_service.get_current_user()
        user_id = user.id if user else 1
        cur = user.currency if user and user.currency else DEFAULT_CURRENCY
        sym = CURRENCY_SYMBOLS.get(cur, "₹")

        txns = txn_service.list_transactions(user_id=user_id)
        peer_enabled = (prof_service.get_preference(user_id, "ai_peer_insights_enabled", "true") or "").lower() == "true"
        daily_check_time = prof_service.get_preference(user_id, "daily_expense_check_time", "8:00 PM")

        # 1. Daily check reminder notice if active
        if daily_check_time != "Off":
            cards_list.append(
                _notification_card(
                    icon=ft.Icons.SCHEDULE,
                    icon_color=COLOR_PRIMARY,
                    title="Daily Expense Check Active",
                    message=f"Evening financial check-in scheduled daily for {daily_check_time}.",
                    badge_text="REMINDER",
                    badge_color=COLOR_PRIMARY,
                    timestamp="SCHEDULED",
                )
            )

        # 2. Peer insights card (only if enabled and user has a profession)
        if peer_enabled and user and user.profession:
            cards_list.append(
                _notification_card(
                    icon=ft.Icons.AUTO_AWESOME,
                    icon_color=accent_purple,
                    title="Peer Insights Active",
                    message=f"Spending metrics benchmarked against {user.profession} lifestyle standards.",
                    badge_text="INSIGHT",
                    badge_color=accent_purple,
                    timestamp="ACTIVE",
                )
            )

        # 3. Recent actual transactions as notifications
        for t in sorted(txns, key=lambda x: (x.transaction_date, x.id), reverse=True)[:5]:
            is_income = t.transaction_type == TransactionType.INCOME
            cat_name = t.category.name if t.category else "General"
            amt_formatted = f"{sym}{t.amount_paise / 100:,.2f}"
            cards_list.append(
                _notification_card(
                    icon=ft.Icons.ACCOUNT_BALANCE if is_income else ft.Icons.RECEIPT_LONG,
                    icon_color=COLOR_EMERALD_ACCENT if is_income else COLOR_CORAL_ACCENT,
                    title=f"{'Income Added' if is_income else 'Expense Recorded'}: {amt_formatted}",
                    message=f"{t.description or cat_name} • Category: {cat_name}",
                    badge_text="INCOME" if is_income else "EXPENSE",
                    badge_color=COLOR_EMERALD_ACCENT if is_income else COLOR_CORAL_ACCENT,
                    timestamp=t.transaction_date.strftime("%d %b %Y"),
                )
            )
    except Exception:
        cards_list = []

    # Filter chips
    txn_count = len([c for c in cards_list if "INCOME" in str(c) or "EXPENSE" in str(c)])
    alert_count = len(cards_list) - txn_count
    total_count = len(cards_list)

    chip_all = ft.Container(
        bgcolor=accent_purple,
        border_radius=16,
        padding=ft.Padding.symmetric(horizontal=12, vertical=6),
        ink=True,
        content=ft.Text(f"All ({total_count})", size=11, weight=ft.FontWeight.W_700, color="#FFFFFF"),
    )
    chip_alerts = ft.Container(
        bgcolor=card_bg,
        border=ft.Border.all(1, border_color),
        border_radius=16,
        padding=ft.Padding.symmetric(horizontal=12, vertical=6),
        ink=True,
        content=ft.Text(f"Alerts ({alert_count})", size=11, weight=ft.FontWeight.W_500, color=text_primary),
    )
    chip_txns = ft.Container(
        bgcolor=card_bg,
        border=ft.Border.all(1, border_color),
        border_radius=16,
        padding=ft.Padding.symmetric(horizontal=12, vertical=6),
        ink=True,
        content=ft.Text(f"Transactions ({txn_count})", size=11, weight=ft.FontWeight.W_500, color=text_primary),
    )

    empty_view = ft.Container(
        expand=True,
        alignment=ft.Alignment.CENTER,
        padding=ft.Padding.symmetric(vertical=40, horizontal=20),
        content=ft.Column(
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=10,
            controls=[
                ft.Container(
                    width=60,
                    height=60,
                    border_radius=20,
                    bgcolor=border_color,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Icon(ft.Icons.NOTIFICATIONS_NONE, size=30, color=text_secondary),
                ),
                ft.Text("No notifications yet", size=15, weight=ft.FontWeight.W_700, color=text_primary),
                ft.Text(
                    "You are all caught up! Real-time alerts and ledger updates will appear here as you log transactions.",
                    size=12,
                    color=text_secondary,
                    text_align=ft.TextAlign.CENTER,
                ),
            ],
        ),
    )

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
                                content=ft.Text("Close", size=11, weight=ft.FontWeight.W_700, color=accent_purple),
                            ),
                        ],
                    ),
                    ft.Row(spacing=8, controls=[chip_all, chip_alerts, chip_txns]),
                    ft.Container(
                        expand=True,
                        content=ft.ListView(
                            spacing=12,
                            controls=cards_list,
                        ) if cards_list else empty_view,
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
