"""
Unit tests for Spendora's real-time ClockService and dynamic date/time/day displays.
"""

from datetime import datetime, date, time
import pytest
import flet as ft

from services.clock_service import ClockService, clock_service
from screens.dashboard.dashboard_screen import DashboardView
from screens.transactions.transactions_screen import TransactionsView
from screens.assistant.assistant_screen import AssistantView
from screens.analytics.analytics_screen import AnalyticsView
from screens.personalization.personalization_screen import PersonalizationView
from screens.transactions.add_edit_transaction_screen import AddEditTransactionView


def test_clock_service_singleton():
    c1 = ClockService()
    c2 = ClockService()
    assert c1 is c2
    assert c1 is clock_service


def test_clock_service_formats():
    fixed_dt = datetime(2026, 10, 4, 16, 30, 45)  # Sunday 4:30:45 PM
    assert clock_service.get_day_name(fixed_dt) == "Sunday"
    assert clock_service.get_day_short(fixed_dt) == "Sun"
    assert clock_service.get_date_formatted(fixed_dt, "medium") == "04 Oct 2026"
    assert clock_service.get_date_formatted(fixed_dt, "full") == "04 October 2026"
    assert clock_service.get_time_formatted(fixed_dt, include_seconds=True) == "04:30:45 PM"
    assert clock_service.get_time_formatted(fixed_dt, include_seconds=False) == "04:30 PM"
    assert clock_service.format_day_and_date(fixed_dt) == "Sunday, 04 Oct 2026"
    assert "Sunday" in clock_service.format_live_display(fixed_dt)
    assert "04 Oct 2026" in clock_service.format_live_display(fixed_dt)
    assert "04:30:45 PM" in clock_service.format_live_display(fixed_dt)


def test_clock_service_greetings():
    # Morning: 05:00 - 11:59
    morning_dt = datetime(2026, 10, 4, 8, 15, 0)
    assert clock_service.get_greeting(morning_dt)[0] == "Good Morning"
    assert "☀️" in clock_service.get_greeting_str(morning_dt)

    # Afternoon: 12:00 - 16:59
    afternoon_dt = datetime(2026, 10, 4, 14, 30, 0)
    assert clock_service.get_greeting(afternoon_dt)[0] == "Good Afternoon"
    assert "🌤️" in clock_service.get_greeting_str(afternoon_dt)

    # Evening: 17:00 - 20:59
    evening_dt = datetime(2026, 10, 4, 19, 0, 0)
    assert clock_service.get_greeting(evening_dt)[0] == "Good Evening"
    assert "🌆" in clock_service.get_greeting_str(evening_dt)

    # Night: 21:00 - 04:59
    night_dt1 = datetime(2026, 10, 4, 22, 45, 0)
    night_dt2 = datetime(2026, 10, 4, 2, 30, 0)
    assert clock_service.get_greeting(night_dt1)[0] == "Good Night"
    assert "🌙" in clock_service.get_greeting_str(night_dt1)
    assert clock_service.get_greeting(night_dt2)[0] == "Good Night"
    assert "🌙" in clock_service.get_greeting_str(night_dt2)


def test_clock_service_subscription_and_tick():
    ticks = []

    def on_tick(now):
        ticks.append(now)

    clock_service.subscribe(on_tick)
    assert on_tick in clock_service._listeners

    simulated_dt = datetime(2026, 10, 4, 16, 35, 10)
    # Manually invoke listeners to test safely in test environment
    with clock_service._lock:
        listeners_copy = list(clock_service._listeners)
    for listener in listeners_copy:
        listener(simulated_dt)

    assert len(ticks) >= 1
    assert ticks[-1] == simulated_dt

    clock_service.unsubscribe(on_tick)
    assert on_tick not in clock_service._listeners


def test_dashboard_realtime_clock_controls():
    dash = DashboardView()
    ctrl = dash.build()
    assert ctrl is not None
    assert hasattr(dash, "_greeting_title")
    assert hasattr(dash, "_date_subtext")
    assert hasattr(dash, "_live_date_badge")
    assert dash._greeting_title.value is not None
    assert dash._date_subtext.value is not None

    # Simulate tick and check greeting & live text updates
    dt_evening = datetime(2026, 10, 4, 18, 0, 0)
    dash._on_clock_tick(dt_evening)
    assert "Good Evening" in dash._greeting_title.value
    assert "Sunday" in dash._date_subtext.value
    assert "06:00:00 PM" in dash._date_subtext.value


def test_screens_have_live_time_indicators():
    # Transactions
    txns = TransactionsView()
    t_ctrl = txns.build()
    assert t_ctrl is not None
    assert hasattr(txns, "_live_time_text")
    assert txns._live_time_text.value is not None

    # Assistant
    ast = AssistantView()
    ast_ctrl = ast.build()
    assert ast_ctrl is not None
    assert hasattr(ast, "_live_time_text")
    assert ast._live_time_text.value is not None

    # Analytics
    anl = AnalyticsView()
    anl_ctrl = anl.build()
    assert anl_ctrl is not None
    assert hasattr(anl, "_live_time_text")
    assert anl._live_time_text.value is not None

    # Settings / Personalization
    stg = PersonalizationView()
    stg_ctrl = stg.build()
    assert stg_ctrl is not None
    assert hasattr(stg, "_live_time_text")
    assert stg._live_time_text.value is not None

    # Add/Edit Transaction
    add_edit = AddEditTransactionView(go_back_fn=lambda: None)
    ae_ctrl = add_edit.build()
    assert ae_ctrl is not None
    assert hasattr(add_edit, "_date_text")
    # Date text displays day and date e.g. "Sunday, 04 Oct 2026"
    assert "," in add_edit._date_text.value
