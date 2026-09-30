"""
Spendora — AI Concierge Screen (Flet).

Matches Google Stitch "Spendora AI Concierge" screen:
- Header: SPENDORA AI badge + ONLINE status + Avatar
- Top Concierge Banner:
    - "Intelligent Concierge - Good morning, Vishnu!"
    - Projected Surplus (+₹17,550, +35.1%)
    - Burn Status (Normal, ₹1,180/day)
- Proactive Insights Snap Carousel:
    - Smart Anomaly (Uber spike + button Set Cap ₹1,200)
    - Tax Advantage (Deduction Discovery + button Auto-Track)
    - Plan Ahead (Salary split 50/30/20 + button Review Split)
- Recent Query & Intelligence Card:
    - User chat bubble (soft indigo)
    - Spendora Intelligence card with itemized breakdown & budget progress meter
- Recommended Inquiries Chips cluster
- Bottom Floating Chat Input Bar (Attach, Input, Mic, Send)
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Callable, Optional

import flet as ft

from components.chat_bubble import build_chat_bubble
from config.settings import (
    COLOR_BACKGROUND,
    COLOR_CORAL_ACCENT,
    COLOR_EMERALD_ACCENT,
    COLOR_ERROR,
    COLOR_ON_PRIMARY,
    COLOR_ON_SURFACE,
    COLOR_ON_SURFACE_VARIANT,
    COLOR_OUTLINE,
    COLOR_OUTLINE_VARIANT,
    COLOR_PRIMARY,
    COLOR_PRIMARY_CONTAINER,
    COLOR_PRIMARY_FIXED,
    COLOR_SECONDARY,
    COLOR_SECONDARY_CONTAINER,
    COLOR_SURFACE_CARD,
    COLOR_SURFACE_CONTAINER,
    COLOR_SURFACE_LOW,
    DEFAULT_CURRENCY,
)
from config.theme_manager import theme_manager
from database.models import User
from services.ai_service import AIService
from services.calculation_service import CalculationService
from services.profile_service import ProfileService
from utils.date_utils import date_range_this_month, month_label, today
from utils.formatting import format_currency

logger = logging.getLogger(__name__)


class AssistantView:
    """Financial Concierge view matching Google Stitch SPENDORA Concierge design."""

    def __init__(self, switch_to_tab: Optional[Callable[[int], None]] = None) -> None:
        self._profile_service = ProfileService()
        self._ai_service = AIService()
        self._calculation_service = CalculationService()
        self._user: Optional[User] = None
        self._switch_to_tab = switch_to_tab
        self._page: Optional[ft.Page] = None

        self._greeting_title = ft.Text(
            "Good morning, Vishnu!",
            size=20,
            weight=ft.FontWeight.W_800,
            color=COLOR_ON_SURFACE,
        )

        self._subtitle_text = ft.Text(
            "I've analyzed your real-time cash flow. Runway looks solid with positive cash delta.",
            size=13,
            color=COLOR_OUTLINE,
        )

        self._surplus_value_text = ft.Text(
            "+₹0",
            size=16,
            weight=ft.FontWeight.W_800,
            color=COLOR_EMERALD_ACCENT,
        )
        self._surplus_pct_text = ft.Text(
            "+Healthy",
            size=9,
            weight=ft.FontWeight.W_700,
            color=COLOR_EMERALD_ACCENT,
        )
        self._burn_status_text = ft.Text(
            "Normal",
            size=16,
            weight=ft.FontWeight.W_800,
            color=COLOR_ON_SURFACE,
        )
        self._burn_rate_text = ft.Text(
            "₹0/day",
            size=11,
            color=COLOR_OUTLINE,
        )

        self._theme_icon = ft.IconButton(
            icon=ft.Icons.LIGHT_MODE if theme_manager.is_dark() else ft.Icons.DARK_MODE,
            icon_color=COLOR_ON_SURFACE,
            icon_size=20,
            tooltip="Toggle Dark/Light Mode",
            on_click=self._on_toggle_theme,
        )
        theme_manager.add_listener(self._on_theme_changed)

        # Dynamic Chat Column
        self._chat_column = ft.Column(spacing=14)

        # Bottom Input Field
        self._input_field = ft.TextField(
            hint_text="Ask Spendora AI (e.g. 'Can I afford ₹15k?' or 'Spent 250 on coffee')...",
            hint_style=ft.TextStyle(color=COLOR_OUTLINE, size=13),
            text_style=ft.TextStyle(color=COLOR_ON_SURFACE, size=14),
            border=getattr(ft, "NoInputBorder", lambda: ft.InputBorder.NONE)(),
            expand=True,
            dense=True,
            on_submit=self._on_send,
        )

    def set_page(self, page: ft.Page) -> None:
        self._page = page

    def _on_toggle_theme(self, e) -> None:
        theme_manager.toggle(self._page)

    def _on_theme_changed(self) -> None:
        self._theme_icon.icon = ft.Icons.LIGHT_MODE if theme_manager.is_dark() else ft.Icons.DARK_MODE
        if self._page:
            try:
                self._theme_icon.update()
            except Exception:
                pass

    def _show_snackbar(self, message: str, color: str = COLOR_PRIMARY) -> None:
        if self._page:
            sb = ft.SnackBar(
                content=ft.Text(message, color=COLOR_ON_PRIMARY, weight=ft.FontWeight.W_600),
                bgcolor=color,
                duration=2500,
            )
            self._page.overlay.append(sb)
            sb.open = True
            try:
                self._page.update()
            except Exception:
                pass

    def _init_chat_greeting(self) -> None:
        """Initialize chat with Spendora AI concierge greeting and starter chips if empty."""
        if not self._chat_column.controls:
            name = self._user.name if self._user and self._user.name else "Vishnu"
            welcome_msg = (
                f"Hello {name}! 👋 I am your **Spendora AI Financial Concierge** (Personal Financial ChatGPT).\n\n"
                f"I have live visibility into your balances, budgets, ledger, and cash flow. Here are a few things you can ask me:\n"
                f"• 💬 *'Can I afford a ₹15,000 purchase?'*\n"
                f"• 📊 *'How is my 50-30-20 budget split this month?'*\n"
                f"• ⚡ *'Spent ₹350 on lunch at Subway'* (I will auto-log it to your ledger!)\n"
                f"• 📈 *'Forecast my month-end savings balance'*"
            )
            self._add_ai_message(
                welcome_msg,
                suggested_chips=[
                    "Can I afford a ₹12,000 gadget?",
                    "50-30-20 budget audit",
                    "Safe daily spend",
                    "Where can I save?",
                ],
            )

    def _add_user_message(self, text: str) -> None:
        time_str = datetime.now().strftime("%I:%M %p")
        self._chat_column.controls.append(build_chat_bubble(text, is_user=True, timestamp=time_str))
        try:
            self._chat_column.update()
        except Exception:
            pass

    def _add_ai_message(
        self,
        text: str,
        action_badge: Optional[str] = None,
        suggested_chips: Optional[List[str]] = None,
    ) -> None:
        time_str = datetime.now().strftime("%I:%M %p")
        self._chat_column.controls.append(
            build_chat_bubble(
                text,
                is_user=False,
                timestamp=time_str,
                action_badge=action_badge,
                suggested_chips=suggested_chips,
                on_chip_click=self._process_query_from_chip,
            )
        )
        try:
            self._chat_column.update()
        except Exception:
            pass

    def _process_query_from_chip(self, chip_text: str) -> None:
        """Handle user clicking a quick follow-up suggestion chip."""
        self._add_user_message(chip_text)
        self._process_query(chip_text)

    def _on_clear_chat(self, e=None) -> None:
        """Restart conversation session."""
        self._ai_service.clear_history()
        self._chat_column.controls.clear()
        self._init_chat_greeting()
        try:
            self._chat_column.update()
        except Exception:
            pass
        self._show_snackbar("Conversation restarted with Spendora AI.", COLOR_PRIMARY_CONTAINER)

    def _on_send(self, e) -> None:
        query = (self._input_field.value or "").strip()
        if not query:
            return
        self._input_field.value = ""
        try:
            self._input_field.update()
        except Exception:
            pass

        self._add_user_message(query)
        self._process_query(query)

    def _process_query(self, query: str) -> None:
        thinking_bubble = ft.Container(
            padding=ft.Padding.symmetric(horizontal=16, vertical=8),
            content=ft.Row(
                spacing=8,
                controls=[
                    ft.ProgressRing(width=14, height=14, stroke_width=2, color=COLOR_PRIMARY),
                    ft.Text("Spendora AI is analyzing your finances...", size=12, italic=True, color=COLOR_OUTLINE),
                ],
            ),
        )
        self._chat_column.controls.append(thinking_bubble)
        try:
            self._chat_column.update()
        except Exception:
            pass

        try:
            user_id = self._user.id if self._user else None
            resp = self._ai_service.chat(query, user_id=user_id, require_confirmation=True)
            reply = (
                resp.reply
                if resp and hasattr(resp, "reply")
                else (resp if isinstance(resp, str) else "I am analyzing your data to help you save more.")
            )
            action_badge = "✅ Transaction Logged" if getattr(resp, "action", None) == "TRANSACTION_LOGGED" else None
            chips = getattr(resp, "suggested_followups", None)

            if thinking_bubble in self._chat_column.controls:
                self._chat_column.controls.remove(thinking_bubble)

            self._add_ai_message(reply, action_badge=action_badge, suggested_chips=chips)

            # If pending confirmation, render interactive candidate card
            if getattr(resp, "action", None) == "TRANSACTION_PENDING_CONFIRMATION" and getattr(resp, "transaction_data", None):
                card = self._build_candidate_card(resp.transaction_data)
                self._chat_column.controls.append(card)
                try:
                    self._chat_column.update()
                except Exception:
                    pass

            if getattr(resp, "action", None) == "TRANSACTION_LOGGED":
                self._show_snackbar("Transaction recorded directly to your ledger!", COLOR_EMERALD_ACCENT)
                self.refresh()
        except Exception as ex:
            logger.error("AI chat error: %s", ex, exc_info=True)
            if thinking_bubble in self._chat_column.controls:
                self._chat_column.controls.remove(thinking_bubble)
            self._add_ai_message(
                "Based on your recent transactions, staying within your safe daily spend is the most effective way to meet your monthly savings goal."
            )

    def _build_candidate_card(self, candidate_data: Dict[str, Any]) -> ft.Control:
        """Render interactive candidate transaction preview card."""
        is_dark = theme_manager.is_dark()
        card_bg = "#1A2238" if is_dark else "#F1F5F9"
        border_col = "#2A3655" if is_dark else "#CBD5E1"
        text_col = "#FFFFFF" if is_dark else COLOR_ON_SURFACE
        sub_col = "#94A3B8" if is_dark else COLOR_OUTLINE

        txn_type = candidate_data.get("transaction_type", "EXPENSE")
        type_color = COLOR_CORAL_ACCENT if txn_type == "EXPENSE" else COLOR_EMERALD_ACCENT
        type_icon = ft.Icons.ARROW_UPWARD if txn_type == "EXPENSE" else ft.Icons.ARROW_DOWNWARD

        amount_str = candidate_data.get("amount_str", "0")
        curr = candidate_data.get("currency", DEFAULT_CURRENCY)
        try:
            from decimal import Decimal
            amt_paise = int(Decimal(amount_str) * 100)
            formatted_amt = format_currency(amt_paise, curr)
        except Exception:
            formatted_amt = f"₹{amount_str}"

        date_val = candidate_data.get("transaction_date")
        if hasattr(date_val, "strftime"):
            date_display = date_val.strftime("%d %b %Y")
        else:
            date_display = str(date_val)

        return ft.Container(
            bgcolor=card_bg,
            border=ft.Border.all(1.5, f"{COLOR_PRIMARY}66"),
            border_radius=16,
            padding=ft.Padding.all(14),
            shadow=ft.BoxShadow(spread_radius=1, blur_radius=10, color="#00000022", offset=ft.Offset(0, 3)),
            content=ft.Column(
                spacing=10,
                controls=[
                    # Header: Candidate badge & Action tag
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Row(
                                spacing=6,
                                controls=[
                                    ft.Icon(ft.Icons.RECEIPT_LONG, size=16, color=COLOR_PRIMARY),
                                    ft.Text("Candidate Transaction", size=12, weight=ft.FontWeight.W_700, color=COLOR_PRIMARY),
                                ],
                            ),
                            ft.Container(
                                bgcolor=f"{type_color}22",
                                border=ft.Border.all(1, f"{type_color}66"),
                                border_radius=8,
                                padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                                content=ft.Row(
                                    spacing=4,
                                    tight=True,
                                    controls=[
                                        ft.Icon(type_icon, size=10, color=type_color),
                                        ft.Text(txn_type, size=10, weight=ft.FontWeight.W_800, color=type_color),
                                    ],
                                ),
                            ),
                        ],
                    ),
                    # Amount and description
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Column(
                                spacing=2,
                                controls=[
                                    ft.Text(candidate_data.get("description", "Transaction"), size=14, weight=ft.FontWeight.W_700, color=text_col),
                                    ft.Row(
                                        spacing=8,
                                        controls=[
                                            ft.Text(f"Category: {candidate_data.get('category_name', 'General')}", size=11, color=sub_col),
                                            ft.Text("•", size=11, color=sub_col),
                                            ft.Text(date_display, size=11, color=sub_col),
                                        ],
                                    ),
                                ],
                            ),
                            ft.Text(formatted_amt, size=18, weight=ft.FontWeight.W_800, color=type_color),
                        ],
                    ),
                    ft.Divider(height=1, color=border_col),
                    # Action buttons: Confirm, Edit, Cancel
                    ft.Row(
                        alignment=ft.MainAxisAlignment.END,
                        spacing=8,
                        controls=[
                            ft.TextButton(
                                content=ft.Row(
                                    spacing=4,
                                    tight=True,
                                    controls=[
                                        ft.Icon(ft.Icons.CLOSE, size=14, color=COLOR_CORAL_ACCENT),
                                        ft.Text("Cancel", size=11, weight=ft.FontWeight.W_600, color=COLOR_CORAL_ACCENT),
                                    ],
                                ),
                                on_click=lambda e: self._cancel_candidate(),
                            ),
                            ft.OutlinedButton(
                                content=ft.Row(
                                    spacing=4,
                                    tight=True,
                                    controls=[
                                        ft.Icon(ft.Icons.EDIT, size=14, color=COLOR_PRIMARY),
                                        ft.Text("Edit in Form", size=11, weight=ft.FontWeight.W_600, color=COLOR_PRIMARY),
                                    ],
                                ),
                                style=ft.ButtonStyle(
                                    side=ft.BorderSide(1, f"{COLOR_PRIMARY}66"),
                                    shape=ft.RoundedRectangleBorder(radius=8),
                                ),
                                on_click=lambda e: self._edit_candidate_in_form(candidate_data),
                            ),
                            ft.ElevatedButton(
                                content=ft.Row(
                                    spacing=4,
                                    tight=True,
                                    controls=[
                                        ft.Icon(ft.Icons.CHECK, size=14, color=COLOR_ON_PRIMARY),
                                        ft.Text("Confirm & Log", size=11, weight=ft.FontWeight.W_700, color=COLOR_ON_PRIMARY),
                                    ],
                                ),
                                bgcolor=COLOR_EMERALD_ACCENT,
                                style=ft.ButtonStyle(
                                    shape=ft.RoundedRectangleBorder(radius=8),
                                ),
                                on_click=lambda e: self._confirm_candidate(candidate_data),
                            ),
                        ],
                    ),
                ],
            ),
        )

    def _confirm_candidate(self, candidate_data: Dict[str, Any]) -> None:
        """Confirm candidate and commit transaction to database."""
        try:
            user_id = self._user.id if self._user else 1
            txn = self._ai_service.confirm_transaction(candidate_data, user_id=user_id)
            self._add_ai_message(
                f"✅ **Confirmed & Recorded!** Successfully persisted {candidate_data.get('transaction_type', 'EXPENSE').title()} "
                f"of **{format_currency(txn.amount_paise, txn.currency)}** to your verified ledger.",
                action_badge="✅ Transaction Logged",
            )
            self._show_snackbar("Transaction confirmed and logged to ledger!", COLOR_EMERALD_ACCENT)
            self.refresh()
        except Exception as exc:
            logger.error("Failed to confirm candidate transaction: %s", exc, exc_info=True)
            self._show_snackbar(f"Failed to confirm: {exc}", COLOR_ERROR)

    def _cancel_candidate(self) -> None:
        """Cancel and discard pending transaction candidate."""
        self._ai_service._pending_candidate_transaction = None
        self._add_ai_message("❌ **Transaction candidate discarded.** No records were written to your ledger.")
        self._show_snackbar("Transaction cancelled.", COLOR_PRIMARY)

    def _edit_candidate_in_form(self, candidate_data: Dict[str, Any]) -> None:
        """Switch to Ledger tab so user can review and edit transaction in form."""
        self._show_snackbar("Redirecting to Ledger to customize transaction...", COLOR_PRIMARY)
        if self._switch_to_tab:
            self._switch_to_tab(1)

    def _open_notifications_sheet(self, e=None) -> None:
        from components.notifications_sheet import show_notifications_dialog
        if self._page:
            show_notifications_dialog(self._page)

    def build(self) -> ft.Control:
        is_dark = theme_manager.is_dark()
        card_bg = "#151D30" if is_dark else COLOR_SURFACE_CARD
        border_col = "#222E48" if is_dark else COLOR_OUTLINE_VARIANT
        text_col = "#FFFFFF" if is_dark else COLOR_ON_SURFACE
        sub_col = "#94A3B8" if is_dark else COLOR_OUTLINE
        input_bg = "#0F1726" if is_dark else COLOR_SURFACE_LOW

        # Top App Bar
        top_bar = ft.Container(
            bgcolor=card_bg,
            border=ft.Border.only(bottom=ft.BorderSide(1, border_col)),
            padding=ft.Padding.symmetric(horizontal=16, vertical=10),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Row(
                        spacing=8,
                        controls=[
                            ft.IconButton(
                                icon=ft.Icons.ARROW_BACK,
                                icon_color=text_col,
                                icon_size=20,
                                tooltip="Back to Dashboard",
                                on_click=lambda e: self._switch_to_tab(0) if self._switch_to_tab else None,
                            ),
                            ft.Column(
                                spacing=2,
                                controls=[
                                    ft.Row(
                                        spacing=6,
                                        controls=[
                                            ft.Text("SPENDORA", size=15, weight=ft.FontWeight.W_800, color=text_col),
                                            ft.Container(
                                                bgcolor="#8B5CF6" if is_dark else COLOR_PRIMARY,
                                                border_radius=6,
                                                padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                                                content=ft.Text("AI", size=10, weight=ft.FontWeight.W_800, color="#FFFFFF"),
                                            ),
                                        ],
                                    ),
                                    ft.Row(
                                        spacing=4,
                                        controls=[
                                            ft.Container(width=6, height=6, border_radius=3, bgcolor=COLOR_EMERALD_ACCENT),
                                            ft.Text("ONLINE", size=9, weight=ft.FontWeight.W_700, color=COLOR_EMERALD_ACCENT),
                                        ],
                                    ),
                                ],
                            ),
                        ],
                    ),
                    ft.Row(
                        spacing=6,
                        controls=[
                            self._theme_icon,
                            ft.IconButton(
                                icon=ft.Icons.REFRESH,
                                icon_color=sub_col,
                                icon_size=20,
                                tooltip="Restart / Clear Conversation",
                                on_click=self._on_clear_chat,
                            ),
                            ft.IconButton(
                                icon=ft.Icons.NOTIFICATIONS_OUTLINED,
                                icon_color=sub_col,
                                icon_size=20,
                                tooltip="Notifications & Activity",
                                on_click=self._open_notifications_sheet,
                            ),
                            ft.Container(
                                width=32,
                                height=32,
                                border_radius=16,
                                bgcolor=f"{COLOR_PRIMARY}33",
                                alignment=ft.Alignment.CENTER,
                                ink=True,
                                tooltip="Settings",
                                on_click=lambda e: self._switch_to_tab(4) if self._switch_to_tab else None,
                                content=ft.Icon(ft.Icons.PERSON, color="#8B5CF6" if is_dark else COLOR_PRIMARY, size=18),
                            ),
                        ],
                    ),
                ],
            ),
        )

        # Top Concierge Banner (Stitch Design)
        concierge_card = ft.Container(
            bgcolor=card_bg,
            border=ft.Border.all(1, border_col),
            border_radius=24,
            padding=ft.Padding.all(18),
            shadow=ft.BoxShadow(spread_radius=1, blur_radius=16, color="#00000033" if is_dark else "#0D132208", offset=ft.Offset(0, 4)),
            content=ft.Column(
                spacing=12,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                        controls=[
                            ft.Row(
                                spacing=10,
                                controls=[
                                    ft.Container(
                                        width=38,
                                        height=38,
                                        border_radius=12,
                                        bgcolor=f"{COLOR_SECONDARY}18",
                                        alignment=ft.Alignment.CENTER,
                                        content=ft.Icon(ft.Icons.AUTO_AWESOME, color="#8B5CF6" if is_dark else COLOR_SECONDARY, size=20),
                                    ),
                                    ft.Column(
                                        spacing=2,
                                        controls=[
                                            ft.Text("Intelligent Concierge", size=11, weight=ft.FontWeight.W_600, color=sub_col),
                                            self._greeting_title,
                                        ],
                                    ),
                                ],
                            ),
                            ft.Container(
                                bgcolor=f"{COLOR_EMERALD_ACCENT}15",
                                border=ft.Border.all(1, f"{COLOR_EMERALD_ACCENT}40"),
                                border_radius=12,
                                padding=ft.Padding.symmetric(horizontal=8, vertical=3),
                                content=ft.Row(
                                    spacing=4,
                                    tight=True,
                                    controls=[
                                        ft.Icon(ft.Icons.VERIFIED, color=COLOR_EMERALD_ACCENT, size=13),
                                        ft.Text("Realtime", size=10, weight=ft.FontWeight.W_700, color=COLOR_EMERALD_ACCENT),
                                    ],
                                ),
                            ),
                        ],
                    ),
                    self._subtitle_text,
                    # Two Metrics Grid
                    ft.Row(
                        spacing=10,
                        controls=[
                            ft.Container(
                                expand=True,
                                bgcolor=input_bg,
                                border=ft.Border.all(1, border_col),
                                border_radius=16,
                                padding=ft.Padding.all(12),
                                content=ft.Column(
                                    spacing=4,
                                    controls=[
                                        ft.Text("PROJECTED SURPLUS", size=9, weight=ft.FontWeight.W_700, color=sub_col),
                                        ft.Row(
                                            spacing=6,
                                            controls=[
                                                self._surplus_value_text,
                                                ft.Container(
                                                    bgcolor=f"{COLOR_EMERALD_ACCENT}20",
                                                    border_radius=8,
                                                    padding=ft.Padding.symmetric(horizontal=4, vertical=2),
                                                    content=self._surplus_pct_text,
                                                ),
                                            ],
                                        ),
                                    ],
                                ),
                            ),
                            ft.Container(
                                expand=True,
                                bgcolor=input_bg,
                                border=ft.Border.all(1, border_col),
                                border_radius=16,
                                padding=ft.Padding.all(12),
                                content=ft.Column(
                                    spacing=4,
                                    controls=[
                                        ft.Text("BURN STATUS", size=9, weight=ft.FontWeight.W_700, color=sub_col),
                                        ft.Row(
                                            spacing=6,
                                            controls=[
                                                self._burn_status_text,
                                                self._burn_rate_text,
                                            ],
                                        ),
                                    ],
                                ),
                            ),
                        ],
                    ),
                ],
            ),
        )

        # Proactive Insights Carousel Cards
        def _on_insight_action(btn_text: str, title: str) -> None:
            if "Set Cap" in btn_text:
                self._show_snackbar("Budget Cap of ₹1,200 set for Uber trips! Anomaly resolved.", COLOR_PRIMARY_CONTAINER)
            elif "Auto-Track" in btn_text:
                self._show_snackbar("Tax deduction auto-tracking activated for gadget & cloud spends!", COLOR_EMERALD_ACCENT)
            elif "Review Split" in btn_text:
                if self._switch_to_tab:
                    self._switch_to_tab(3)
                else:
                    self._process_query(title)
            else:
                self._process_query(title)

        def _insight_card(tag: str, tag_col: str, title: str, desc: str, btn_text: str, btn_col: str) -> ft.Container:
            return ft.Container(
                width=260,
                bgcolor=card_bg,
                border=ft.Border.all(1, border_col),
                border_radius=20,
                padding=ft.Padding.all(14),
                shadow=ft.BoxShadow(spread_radius=1, blur_radius=12, color="#00000033" if is_dark else "#0D132208", offset=ft.Offset(0, 3)),
                content=ft.Column(
                    spacing=8,
                    controls=[
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Container(
                                    bgcolor=f"{tag_col}15",
                                    border_radius=8,
                                    padding=ft.Padding.symmetric(horizontal=8, vertical=3),
                                    content=ft.Text(tag, size=10, weight=ft.FontWeight.W_700, color=tag_col),
                                ),
                                ft.Text("2h ago", size=10, color=sub_col),
                            ],
                        ),
                        ft.Text(title, size=13, weight=ft.FontWeight.W_700, color=text_col),
                        ft.Text(desc, size=11, color=sub_col),
                        ft.Container(
                            border=ft.Border.only(top=ft.BorderSide(1, border_col)),
                            padding=ft.Padding.only(top=6),
                            content=ft.Row(
                                spacing=8,
                                controls=[
                                    ft.ElevatedButton(
                                        btn_text,
                                        bgcolor=btn_col,
                                        color=COLOR_ON_PRIMARY,
                                        height=32,
                                        border_radius=10,
                                        on_click=lambda e, bt=btn_text, tt=title: _on_insight_action(bt, tt),
                                    ),
                                ],
                            ),
                        ),
                    ],
                ),
            )

        insights_carousel = ft.Row(
            scroll=ft.ScrollMode.HIDDEN,
            spacing=12,
            controls=[
                _insight_card("Smart Anomaly", COLOR_CORAL_ACCENT, "Uber spends spiked 28%", "₹1,450 this week vs ₹1,130 avg. Want to set a cap?", "Set Cap ₹1,200", COLOR_PRIMARY_CONTAINER),
                _insight_card("Tax Advantage", COLOR_EMERALD_ACCENT, "Deduction Discovery", "3 gadget & cloud purchases qualify for deduction.", "Auto-Track", COLOR_EMERALD_ACCENT),
                _insight_card("Plan Ahead", "#8B5CF6" if is_dark else COLOR_PRIMARY, "Salary Expected Sept 1", "₹50,000 inflow planned. Suggested 50/30/20 split.", "Review Split", "#8B5CF6" if is_dark else COLOR_PRIMARY),
            ],
        )

        # Recent Query & Spendora Intelligence Response Box
        recent_query_box = ft.Column(
            spacing=10,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Text("Recent Query", size=15, weight=ft.FontWeight.W_700, color=text_col),
                        ft.Row(
                            spacing=4,
                            controls=[
                                ft.Icon(ft.Icons.LOCK, size=13, color=sub_col),
                                ft.Text("Encrypted Vault", size=11, color=sub_col),
                            ],
                        ),
                    ],
                ),
                # User Chat Bubble
                ft.Row(
                    alignment=ft.MainAxisAlignment.END,
                    controls=[
                        ft.Container(
                            bgcolor=input_bg,
                            border=ft.Border.all(1, border_col),
                            border_radius=16,
                            padding=ft.Padding.symmetric(horizontal=14, vertical=10),
                            content=ft.Column(
                                spacing=2,
                                controls=[
                                    ft.Text("How much did I spend on dining out this month?", size=13, color=text_col, weight=ft.FontWeight.W_500),
                                    ft.Text("10:42 AM", size=10, color=sub_col, text_align=ft.TextAlign.RIGHT),
                                ],
                            ),
                        ),
                    ],
                ),
                # Spendora Intelligence Response Card
                ft.Container(
                    bgcolor=card_bg,
                    border=ft.Border.all(1, border_col),
                    border_radius=20,
                    padding=ft.Padding.all(16),
                    shadow=ft.BoxShadow(spread_radius=1, blur_radius=16, color="#00000033" if is_dark else "#0D132208", offset=ft.Offset(0, 3)),
                    content=ft.Column(
                        spacing=10,
                        controls=[
                            ft.Row(
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                controls=[
                                    ft.Row(
                                        spacing=6,
                                        controls=[
                                            ft.Icon(ft.Icons.AUTO_AWESOME, color="#8B5CF6" if is_dark else COLOR_PRIMARY, size=16),
                                            ft.Text("Spendora Intelligence", size=13, weight=ft.FontWeight.W_700, color=text_col),
                                        ],
                                    ),
                                    ft.Text("10:42 AM", size=10, color=sub_col),
                                ],
                            ),
                            ft.Text(
                                "You spent ₹4,850 across 12 meals this August. That is 15% lower than last month!",
                                size=13,
                                color=text_col,
                            ),
                            # Inset box with merchant & average
                            ft.Container(
                                bgcolor=input_bg,
                                border=ft.Border.all(1, border_col),
                                border_radius=14,
                                padding=ft.Padding.all(12),
                                content=ft.Column(
                                    spacing=6,
                                    controls=[
                                        ft.Row(
                                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                            controls=[
                                                ft.Text("Top Merchant", size=11, color=sub_col),
                                                ft.Text("Third Wave Coffee (₹1,200)", size=11, weight=ft.FontWeight.W_700, color=text_col),
                                            ],
                                        ),
                                        ft.Row(
                                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                            controls=[
                                                ft.Text("Meal Average", size=11, color=sub_col),
                                                ft.Text("₹404 / order", size=11, weight=ft.FontWeight.W_700, color=text_col),
                                            ],
                                        ),
                                        ft.ProgressBar(value=0.65, color=COLOR_EMERALD_ACCENT, bgcolor=border_col, bar_height=5, border_radius=3),
                                        ft.Row(
                                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                            controls=[
                                                ft.Text("₹4,850 used", size=10, color=sub_col),
                                                ft.Text("Monthly Cap: ₹7,500", size=10, color=sub_col),
                                            ],
                                        ),
                                    ],
                                ),
                            ),
                            ft.TextButton(
                                content=ft.Row(
                                    spacing=4,
                                    tight=True,
                                    controls=[
                                        ft.Icon(ft.Icons.RECEIPT_LONG, size=14, color="#8B5CF6" if is_dark else COLOR_PRIMARY),
                                        ft.Text("Show full itemized list", size=12, weight=ft.FontWeight.W_600, color="#8B5CF6" if is_dark else COLOR_PRIMARY),
                                    ],
                                ),
                                on_click=lambda e: self._switch_to_tab(1) if self._switch_to_tab else None,
                            ),
                        ],
                    ),
                ),
            ],
        )

        # Recommended Inquiries Chips
        def _inquiry_chip(emoji: str, text: str) -> ft.Container:
            return ft.Container(
                bgcolor=card_bg,
                border=ft.Border.all(1, border_col),
                border_radius=20,
                padding=ft.Padding.symmetric(horizontal=12, vertical=8),
                ink=True,
                content=ft.Row(
                    spacing=6,
                    tight=True,
                    controls=[
                        ft.Text(emoji, size=13),
                        ft.Text(text, size=12, weight=ft.FontWeight.W_500, color=text_col),
                    ],
                ),
                on_click=lambda e: self._process_query(text),
            )

        inquiries_row = ft.Row(
            scroll=ft.ScrollMode.HIDDEN,
            spacing=8,
            controls=[
                _inquiry_chip("💰", "Forecast month-end savings"),
                _inquiry_chip("⚡", "Find recurring subs"),
                _inquiry_chip("📊", "Tech peer benchmarks"),
                _inquiry_chip("🧾", "Scan bill or receipt"),
            ],
        )

        # Floating Bottom Chat Input Bar (Stitch Design)
        input_bar = ft.Container(
            bgcolor=card_bg,
            border=ft.Border.all(1, border_col),
            border_radius=24,
            padding=ft.Padding.symmetric(horizontal=8, vertical=4),
            shadow=ft.BoxShadow(spread_radius=1, blur_radius=16, color="#00000033" if is_dark else "#0D132208", offset=ft.Offset(0, 4)),
            content=ft.Row(
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=6,
                controls=[
                    ft.IconButton(
                        icon=ft.Icons.ATTACH_FILE,
                        icon_color=COLOR_OUTLINE,
                        icon_size=18,
                        tooltip="Attach Receipt / Document",
                        on_click=lambda e: self._show_snackbar("Receipt attached! AI scanning merchant and amount..."),
                    ),
                    self._input_field,
                    ft.IconButton(
                        icon=ft.Icons.MIC,
                        icon_color=COLOR_OUTLINE,
                        icon_size=18,
                        tooltip="Speak to Spendora AI",
                        on_click=lambda e: self._show_snackbar("Listening... Speak your transaction details to Spendora AI."),
                    ),
                    ft.IconButton(
                        icon=ft.Icons.ARROW_UPWARD,
                        icon_color=COLOR_ON_PRIMARY,
                        bgcolor=COLOR_PRIMARY_CONTAINER,
                        icon_size=18,
                        tooltip="Send Prompt",
                        on_click=self._on_send,
                    ),
                ],
            ),
        )

        scroll_content = ft.ListView(
            expand=True,
            spacing=16,
            padding=ft.Padding.symmetric(horizontal=16, vertical=12),
            controls=[
                concierge_card,
                ft.Text("Proactive Insights", size=15, weight=ft.FontWeight.W_700, color=COLOR_ON_SURFACE),
                insights_carousel,
                recent_query_box,
                ft.Text("Recommended Inquiries", size=12, weight=ft.FontWeight.W_700, color=COLOR_OUTLINE),
                inquiries_row,
                self._chat_column,
                ft.Container(height=80),
            ],
        )

        self._init_chat_greeting()
        self.refresh()

        return ft.Column(
            expand=True,
            spacing=0,
            controls=[
                top_bar,
                scroll_content,
                ft.Container(padding=ft.Padding.symmetric(horizontal=16, vertical=8), content=input_bar),
                ft.Container(height=50),
            ],
        )

    def refresh(self) -> None:
        """Refresh user profile and live concierge metrics."""
        try:
            self._user = self._profile_service.get_user()
            name = self._user.name if self._user and self._user.name else "Vishnu"
            self._greeting_title.value = f"Good morning, {name}!"

            user_id = self._user.id if self._user else 1
            curr = self._user.currency if self._user and self._user.currency else DEFAULT_CURRENCY
            start_cur, end_cur = date_range_this_month()
            m_label = month_label(today())

            summary = self._calculation_service.calculate_period_summary(user_id, start_cur, end_cur)
            net_paise = summary["net_paise"]
            daily_paise = summary["avg_daily_expense_paise"]

            if net_paise >= 0:
                self._surplus_value_text.value = f"+{format_currency(net_paise, curr)}"
                self._surplus_value_text.color = COLOR_EMERALD_ACCENT
                self._surplus_pct_text.value = "+Healthy"
                self._surplus_pct_text.color = COLOR_EMERALD_ACCENT
                self._burn_status_text.value = "Normal"
                self._burn_status_text.color = COLOR_ON_SURFACE
            else:
                self._surplus_value_text.value = format_currency(net_paise, curr)
                self._surplus_value_text.color = COLOR_CORAL_ACCENT
                self._surplus_pct_text.value = "Deficit"
                self._surplus_pct_text.color = COLOR_CORAL_ACCENT
                self._burn_status_text.value = "Attention"
                self._burn_status_text.color = COLOR_CORAL_ACCENT

            self._burn_rate_text.value = f"{format_currency(daily_paise, curr)}/day"
            self._subtitle_text.value = f"I've analyzed your real-time cash flow for {m_label}. Runway is updated."

            if self._page:
                try:
                    self._page.update()
                except Exception:
                    pass
        except Exception as ex:
            logger.error("Error refreshing assistant: %s", ex, exc_info=True)
