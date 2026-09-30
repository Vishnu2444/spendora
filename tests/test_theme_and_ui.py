"""
Tests for SPENDORA dark mode toggling, theme manager, and screen interactivity.
"""

import pytest
import flet as ft
from config.theme_manager import theme_manager, ThemeMode
from screens.dashboard.dashboard_screen import DashboardView
from screens.transactions.transactions_screen import TransactionsView
from screens.analytics.analytics_screen import AnalyticsView
from screens.assistant.assistant_screen import AssistantView
from screens.personalization.personalization_screen import PersonalizationView
from screens.onboarding.welcome_screen import WelcomeView
from database.database import init_db


@pytest.fixture(autouse=True)
def setup_db():
    init_db()


def test_theme_manager_modes():
    theme_manager.set_theme(ThemeMode.LIGHT)
    assert not theme_manager.is_dark()
    assert theme_manager.mode == ThemeMode.LIGHT

    theme_manager.set_theme(ThemeMode.DARK)
    assert theme_manager.is_dark()
    assert theme_manager.mode == ThemeMode.DARK

    theme_manager.toggle()
    assert not theme_manager.is_dark()
    assert theme_manager.mode == ThemeMode.LIGHT


def test_theme_manager_listeners():
    listener_called = []

    def on_theme_change(is_dark):
        listener_called.append(is_dark)

    theme_manager.register_listener(on_theme_change)
    theme_manager.set_theme(ThemeMode.DARK)
    assert len(listener_called) > 0
    assert listener_called[-1] is True

    theme_manager.unregister_listener(on_theme_change)


def test_views_build_and_theme_reactivity():
    welcome = WelcomeView(on_complete=lambda: None)
    w_ctrl = welcome.build()
    assert w_ctrl is not None

    dash = DashboardView()
    d_ctrl = dash.build()
    assert d_ctrl is not None

    txns = TransactionsView()
    t_ctrl = txns.build()
    assert t_ctrl is not None

    analytics = AnalyticsView()
    a_ctrl = analytics.build()
    assert a_ctrl is not None

    assistant = AssistantView()
    ast_ctrl = assistant.build()
    assert ast_ctrl is not None

    settings = PersonalizationView()
    s_ctrl = settings.build()
    assert s_ctrl is not None

    # Toggle theme and verify no crashes occur across active views
    theme_manager.toggle()
    theme_manager.set_theme(ThemeMode.DARK)
    theme_manager.set_theme(ThemeMode.LIGHT)


def test_screen_actions_and_buttons():
    # Test transactions filter chips
    txns = TransactionsView()
    txns.build()
    txns._set_chip_filter("ALL")
    assert txns._active_chip == "ALL"
    txns._set_chip_filter("THIS_MONTH")
    assert txns._active_chip == "THIS_MONTH"

    # Test analytics tab switching
    analytics = AnalyticsView()
    analytics.build()
    analytics._switch_segmented_tab("GAIN_LOSS")
    assert analytics._active_tab == "GAIN_LOSS"
    analytics._switch_segmented_tab("CALCULATOR")
    assert analytics._active_tab == "CALCULATOR"

    # Test settings theme segmented button switching
    settings = PersonalizationView()
    settings.build()
    settings._set_theme(ThemeMode.DARK)
    assert theme_manager.mode == ThemeMode.DARK
    settings._set_theme(ThemeMode.LIGHT)
    assert theme_manager.mode == ThemeMode.LIGHT

    # Test assistant query processing
    assistant = AssistantView()
    assistant.build()
    assistant._process_query("How much did I spend on dining?")
    assert len(assistant._chat_column.controls) > 0


def test_add_edit_transaction_delete_safety():
    from screens.transactions.add_edit_transaction_screen import AddEditTransactionView
    add_edit = AddEditTransactionView(go_back_fn=lambda: None)
    ctrl = add_edit.build()
    assert ctrl is not None
    assert hasattr(add_edit, "_user_id")
    assert hasattr(add_edit, "_page")

    # Load a None transaction (New)
    add_edit.load_transaction(None)
    assert add_edit._transaction_id is None
    assert add_edit._delete_btn.visible is False

    # Simulate delete call on unpersisted transaction (should safely return without crash)
    add_edit._on_delete_click(None)


def test_date_range_custom_calculation():
    from datetime import date
    analytics = AnalyticsView()
    analytics.build()

    # Simulate custom 2-date calculation window
    start_d = date(2026, 8, 1)
    end_d = date(2026, 8, 15)
    analytics._on_date_range_applied(start_d, end_d)

    assert analytics._gain_loss_start == start_d
    assert analytics._gain_loss_end == end_d
    assert analytics._gain_loss_period == "CUSTOM"
    assert "15 Days" in analytics._days_selected_badge.value


def test_notifications_sheet_dialog():
    from unittest.mock import MagicMock
    from components.notifications_sheet import show_notifications_dialog
    page = MagicMock()
    page.overlay = []
    show_notifications_dialog(page)
    assert len(page.overlay) > 0
    assert page.overlay[0].open is True


def test_category_management_dialog():
    from unittest.mock import MagicMock
    from components.category_management_dialog import show_category_management_dialog
    page = MagicMock()
    page.overlay = []
    show_category_management_dialog(page)
    assert len(page.overlay) > 0
    assert page.overlay[0].open is True


def test_gain_loss_and_add_edit_views_non_empty():
    from unittest.mock import MagicMock
    from screens.analytics.analytics_screen import AnalyticsView
    from screens.transactions.add_edit_transaction_screen import AddEditTransactionView

    page = MagicMock()
    page.overlay = []

    # 1. Analytics & Gain/Loss switching
    analytics = AnalyticsView()
    analytics.set_page(page)
    actrl = analytics.build()
    assert actrl is not None
    assert len(actrl.controls) == 3

    # Switch to Gain & Loss
    analytics._switch_segmented_tab("GAIN_LOSS")
    assert analytics._tab_content_container.content is not None
    assert len(analytics._tab_content_container.content.controls) == 5

    # Switch to Calculator
    analytics._switch_segmented_tab("CALCULATOR")
    assert analytics._tab_content_container.content is not None
    assert len(analytics._tab_content_container.content.controls) >= 3

    # 2. AddEdit Transaction Entry Form
    add_edit = AddEditTransactionView()
    add_edit.set_page(page)
    aectrl = add_edit.build()
    assert aectrl is not None
    assert len(aectrl.controls) == 2

    add_edit.load_transaction(None)
    assert len(add_edit._category_chips_row.controls) > 0
    # Check scrollable list has all 5 primary cards/buttons
    assert len(aectrl.controls[1].controls) == 5


def test_snackbar_safe_duration():
    from unittest.mock import MagicMock
    from screens.assistant.assistant_screen import AssistantView
    from screens.personalization.personalization_screen import PersonalizationView

    page = MagicMock()
    page.overlay = []

    ast = AssistantView()
    ast.set_page(page)
    ast._show_snackbar("Test message")
    assert len(page.overlay) == 1
    assert page.overlay[0].open is True

    pers = PersonalizationView()
    pers.set_page(page)
    pers._show_snackbar("Settings saved")
    assert len(page.overlay) == 2
    assert page.overlay[1].open is True


def test_dashboard_quick_add_modal():
    from unittest.mock import MagicMock
    from screens.dashboard.dashboard_screen import DashboardView

    page = MagicMock()
    page.overlay = []
    dash = DashboardView()
    dash.set_page(page)
    dash.build()

    dash._open_quick_add_modal()
    assert len(page.overlay) == 1
    dialog = page.overlay[0]
    assert dialog.open is True

    amt_input = dialog.content.content.controls[0]
    desc_input = dialog.content.content.controls[1]
    save_btn = dialog.actions[1]

    amt_input.value = "150.00"
    desc_input.value = "Coffee"
    save_btn.on_click(None)
    assert dialog.open is False


def test_dashboard_quick_add_income_modal():
    from unittest.mock import MagicMock
    from screens.dashboard.dashboard_screen import DashboardView

    page = MagicMock()
    page.overlay = []
    dash = DashboardView()
    dash.set_page(page)
    ctrl = dash.build()
    assert ctrl is not None

    # Verify both Add Expense and Add Income are in the quick action row
    # In dash.build(), controls[1] is scroll_content, and its first control is top formula, second is quick_actions_row
    scroll_col = ctrl.controls[1]
    quick_actions = scroll_col.controls[1]
    assert len(quick_actions.controls) == 4
    # Button 0 is Add Expense, Button 1 is Add Income
    expense_text = quick_actions.controls[0].content.controls[1].value
    income_text = quick_actions.controls[1].content.controls[1].value
    assert expense_text == "Add Expense"
    assert income_text == "Add Income"

    # Test opening income modal directly
    dash._open_quick_add_income_modal()
    assert len(page.overlay) == 1
    dialog = page.overlay[0]
    assert dialog.open is True

    amt_input = dialog.content.content.controls[0]
    desc_input = dialog.content.content.controls[1]
    save_btn = dialog.actions[1]

    amt_input.value = "5000.00"
    desc_input.value = "Consulting Gig"
    save_btn.on_click(None)
    assert dialog.open is False


def test_transactions_fab_connects_to_add_income():
    from unittest.mock import MagicMock
    from screens.transactions.transactions_screen import TransactionsView

    mock_navigate = MagicMock()
    txns = TransactionsView(navigate_to_add_txn=mock_navigate)
    ctrl = txns.build()
    assert ctrl is not None

    # Test direct _open_add_income call
    txns._open_add_income()
    mock_navigate.assert_called_with("INCOME")

    # Verify the floating FAB is configured to call _open_add_income
    # ctrl is ft.Stack: [Column, add_fab]
    fab = ctrl.controls[1]
    assert fab.tooltip == "Add Income"
    mock_navigate.reset_mock()
    fab.on_click(None)
    mock_navigate.assert_called_with("INCOME")


def test_gain_loss_calculator_interactive_calculations():
    from unittest.mock import MagicMock
    from screens.analytics.analytics_screen import AnalyticsView

    analytics = AnalyticsView()
    ctrl = analytics.build()
    assert ctrl is not None
    # Cards in Calculator tab including analytics charts
    assert len(analytics._tab_content_container.content.controls) >= 3

    # Initial standard state: 50,000 Inflow, 20,000 Fixed, 12,000 Variable
    analytics._calc_income_input.value = "50000.00"
    analytics._calc_fixed_input.value = "20000.00"
    analytics._calc_variable_input.value = "12000.00"
    analytics._set_scenario_preset(0)

    assert "18,000" in analytics._calc_net_amount.value
    assert "SURPLUS GAIN" in analytics._calc_status_badge.value
    assert "+36.0%" in analytics._calc_margin_text.value

    # Test Deficit scenario: 25,000 Inflow, 20,000 Fixed, 10,000 Variable -> -5,000 Net
    analytics._calc_income_input.value = "25000.00"
    analytics._calc_fixed_input.value = "20000.00"
    analytics._calc_variable_input.value = "10000.00"
    analytics._recalculate_gain_loss()

    assert "-₹5,000" in analytics._calc_net_amount.value
    assert "DEFICIT LOSS" in analytics._calc_status_badge.value
    assert "-20.0%" in analytics._calc_margin_text.value

    # Test Scenario preset adjustment: -50% spending cut
    analytics._set_scenario_preset(-50)
    # Variable was 10,000 -> with -50% cut it becomes 5,000 -> Total outflow 20,000 + 5,000 = 25,000
    # Net: 25,000 - 25,000 = 0.00 (Break-even!)
    assert "BREAK-EVEN" in analytics._calc_status_badge.value
    assert "0.00" in analytics._calc_net_amount.value

    # Test sync with actuals
    analytics._sync_calc_with_actuals()
    assert float(analytics._calc_income_input.value) >= 0
    assert float(analytics._calc_fixed_input.value) >= 0


def test_calculator_from_to_date_expense_calculation():
    from datetime import date, timedelta
    from unittest.mock import MagicMock
    from screens.analytics.analytics_screen import AnalyticsView

    analytics = AnalyticsView()
    ctrl = analytics.build()
    assert ctrl is not None

    today = date.today()
    start_d = today - timedelta(days=14)
    end_d = today

    # Verify initial from/to date controls
    assert analytics._calc_from_text is not None
    assert analytics._calc_to_text is not None
    assert analytics._calc_days_badge is not None

    # Calculate for arbitrary 15-day range
    analytics._calculate_expenses_for_date_range(start_d, end_d, show_snackbar=False)
    assert analytics._calc_from_date == start_d
    assert analytics._calc_to_date == end_d
    assert "15 Days" in analytics._calc_days_badge.value
    assert start_d.strftime("%d %b %Y") in analytics._calc_from_text.value
    assert end_d.strftime("%d %b %Y") in analytics._calc_to_text.value

    # Test shifting from date by +1 day (becomes 14 days)
    analytics._shift_calc_from_date(1)
    assert analytics._calc_from_date == start_d + timedelta(days=1)
    assert "14 Days" in analytics._calc_days_badge.value

    # Test shifting to date by -1 day (becomes 13 days)
    analytics._shift_calc_to_date(-1)
    assert analytics._calc_to_date == end_d - timedelta(days=1)
    assert "13 Days" in analytics._calc_days_badge.value

    # Test presets
    analytics._set_calc_date_preset("LAST_30")
    assert (analytics._calc_to_date - analytics._calc_from_date).days == 30
    assert "31 Days" in analytics._calc_days_badge.value

    analytics._set_calc_date_preset("LAST_MONTH")
    assert analytics._calc_from_date < today

    # Test dialog apply callback
    d1 = date(2026, 1, 1)
    d2 = date(2026, 1, 15)
    analytics._on_calc_date_range_applied(d1, d2)
    assert analytics._calc_from_date == d1
    assert analytics._calc_to_date == d2
    assert "15 Days" in analytics._calc_days_badge.value


def test_projected_surplus_and_transparent_safe_daily_and_scenario_simulation():
    from screens.analytics.analytics_screen import AnalyticsView

    analytics = AnalyticsView()
    ctrl = analytics.build()
    assert ctrl is not None

    # Verify Projected Surplus in insight text
    assert "Projected surplus" in analytics._calc_insight_text.value

    # Set known standard inputs: 50,000 Inflow, 20,000 Fixed, 12,000 Variable
    analytics._calc_income_input.value = "50000.00"
    analytics._calc_fixed_input.value = "20000.00"
    analytics._calc_variable_input.value = "12000.00"
    analytics._set_scenario_preset(0)

    # 1. Verify Transparent Safe Daily Spend formula and explanation
    assert "Formula: (Inflow ₹50,000.00 - Fixed ₹20,000.00)" in analytics._calc_daily_spend_transparency_text.value
    assert "leaves your savings intact" in analytics._calc_daily_spend_transparency_text.value
    assert "50,000 - ₹20,000" in analytics._calc_daily_spend_formula.value

    # 2. Verify Baseline (0%) Scenario Simulation
    assert "0.00 / mo" in analytics._calc_scenario_monthly_delta.value
    assert "0 / yr" in analytics._calc_scenario_annual_delta.value
    assert "BASELINE" in analytics._calc_scenario_badge.value
    assert "0% adjustment" in analytics._calc_scenario_summary_text.value

    # 3. Verify Frugal Cut (-10%): saves ₹1,200/mo, ₹14,400/yr
    analytics._set_scenario_preset(-10)
    assert "+₹1,200.00 / mo" in analytics._calc_scenario_monthly_delta.value
    assert "+₹14,400 / yr" in analytics._calc_scenario_annual_delta.value
    assert "SURPLUS EXPANSION" in analytics._calc_scenario_badge.value
    assert "saves +₹1,200.00/month" in analytics._calc_scenario_summary_text.value
    assert "boosting your projected annual surplus by +₹14,400" in analytics._calc_scenario_summary_text.value

    # 4. Verify Increased Spend (+15%): reduces surplus by ₹1,800/mo, ₹21,600/yr
    analytics._set_scenario_preset(15)
    assert "-₹1,800.00 / mo" in analytics._calc_scenario_monthly_delta.value
    assert "-₹21,600 / yr" in analytics._calc_scenario_annual_delta.value
    assert "SURPLUS REDUCTION" in analytics._calc_scenario_badge.value
    assert "reduces your surplus by ₹1,800.00/month" in analytics._calc_scenario_summary_text.value
    assert "21,600 less saved per year" in analytics._calc_scenario_summary_text.value

    # 5. Verify Deficit scenario transparency for Safe Daily Spend
    analytics._calc_income_input.value = "20000.00"
    analytics._calc_fixed_input.value = "25000.00"
    analytics._recalculate_gain_loss()
    assert "Fixed costs exceed inflow by ₹5,000.00" in analytics._calc_daily_spend_transparency_text.value


def test_ledger_full_working_condition():
    from unittest.mock import MagicMock
    from screens.analytics.analytics_screen import AnalyticsView
    import os

    page = MagicMock()
    page.overlay = []

    analytics = AnalyticsView()
    analytics.set_page(page)
    analytics.build()

    # Switch to Ledger History
    analytics._switch_segmented_tab("LEDGER")
    assert analytics._active_tab == "LEDGER"
    assert analytics._tab_content_container.content is not None
    # 5 cards in ledger view: header, bento strip, filter toolbar, journal stream, action buttons
    assert len(analytics._tab_content_container.content.controls) == 5

    # Verify ledger summary metrics exist and are non-empty
    assert analytics._ledger_opening_bal_val.value is not None
    assert analytics._ledger_inflow_val.value is not None
    assert analytics._ledger_outflow_val.value is not None
    assert analytics._ledger_closing_bal_val.value is not None
    assert analytics._ledger_status_badge.value in ("SURPLUS (+)", "DEFICIT (-)", "BALANCED")

    # Test period switching
    analytics._set_ledger_period("ALL")
    assert analytics._ledger_period == "ALL"
    assert "All-Time" in analytics._ledger_date_badge.value

    analytics._set_ledger_period("LAST_MONTH")
    assert analytics._ledger_period == "LAST_MONTH"

    analytics._set_ledger_period("THIS_MONTH")
    assert analytics._ledger_period == "THIS_MONTH"

    # Test type filter switching
    analytics._set_ledger_type_filter("INCOME")
    assert analytics._ledger_type_filter == "INCOME"

    analytics._set_ledger_type_filter("EXPENSE")
    assert analytics._ledger_type_filter == "EXPENSE"

    analytics._set_ledger_type_filter("ALL")
    assert analytics._ledger_type_filter == "ALL"

    # Test search query filtering
    analytics._ledger_search_field.value = "Coffee"
    analytics._on_ledger_search_changed(None)
    assert analytics._ledger_search_query == "coffee"

    # Test sorting
    initial_sort = analytics._ledger_sort_desc
    analytics._toggle_ledger_sort()
    assert analytics._ledger_sort_desc != initial_sort

    # Test CSV export
    analytics._export_ledger_csv()
    csv_files = [f for f in os.listdir("data") if f.startswith("spendora_ledger_") and f.endswith(".csv")]
    assert len(csv_files) > 0
    latest_csv = os.path.join("data", sorted(csv_files)[-1])
    with open(latest_csv, "r", encoding="utf-8") as f:
        header = f.readline()
        assert "Running_Balance" in header
        assert "Debit" in header
        assert "Credit" in header


def test_analytics_charts_below_calculator():
    from unittest.mock import MagicMock
    from screens.analytics.analytics_screen import AnalyticsView
    import flet_charts as fc

    page = MagicMock()
    page.overlay = []

    analytics = AnalyticsView()
    analytics.set_page(page)
    ctrl = analytics.build()
    assert ctrl is not None

    # Total 8 cards in calculator tab with the new analytics charts added
    assert len(analytics._tab_content_container.content.controls) == 8

    # Card 4: Cash flow bar chart
    assert analytics._cashflow_barchart_container.content is not None

    # Card 5: Category distribution pie chart
    assert analytics._category_piechart_container.content is not None

    # Card 6: Cumulative savings trajectory line chart
    assert analytics._trajectory_linechart_container.content is not None
    assert isinstance(analytics._trajectory_linechart_container.content, fc.LineChart)

    # Card 7: 50-30-20 budget rule gauge
    assert analytics._budget_rule_gauge_container.content is not None

    # Card 8: Key analytics takeaways highlights
    assert analytics._analytics_highlights_container.content is not None


def test_transactions_extended_filters():
    from unittest.mock import MagicMock
    from screens.transactions.transactions_screen import TransactionsView
    from database.models import Transaction, TransactionType

    txns = TransactionsView()
    ctrl = txns.build()
    assert ctrl is not None

    # Check defaults
    assert txns._filter_period == "THIS_MONTH"
    assert txns._filter_type is None
    assert txns._filter_category_id is None
    assert txns._filter_amount_preset == "ALL"
    assert txns._sort_order == "DATE_DESC"
    assert txns._get_active_filters_count() == 0

    # 1. Type toggle
    txns._toggle_type_filter()
    assert txns._filter_type == "EXPENSE"
    assert txns._get_active_filters_count() == 1

    txns._toggle_type_filter()
    assert txns._filter_type == "INCOME"
    assert txns._get_active_filters_count() == 1

    txns._toggle_type_filter()
    assert txns._filter_type is None
    assert txns._get_active_filters_count() == 0

    # 2. Period cycling
    txns._cycle_period_filter()
    assert txns._filter_period == "LAST_MONTH"
    assert txns._get_active_filters_count() == 1

    txns._cycle_period_filter()
    assert txns._filter_period == "THIS_WEEK"

    # 3. Amount preset cycling
    txns._cycle_amount_filter()
    assert txns._filter_amount_preset == "UNDER_500"
    txns._cycle_amount_filter()
    assert txns._filter_amount_preset == "500_TO_2000"

    # 4. Sort order cycling
    txns._cycle_sort_order()
    assert txns._sort_order == "DATE_ASC"
    txns._cycle_sort_order()
    assert txns._sort_order == "AMOUNT_DESC"

    # 5. Search term
    txns._search_term = "Supermarket"
    assert txns._get_active_filters_count() >= 4

    # 6. Individual removals
    txns._clear_search()
    assert txns._search_term == ""

    txns._remove_amount_filter()
    assert txns._filter_amount_preset == "ALL"

    txns._remove_sort_filter()
    assert txns._sort_order == "DATE_DESC"

    # 7. Reset all filters
    txns._reset_all_filters()
    assert txns._filter_period == "THIS_MONTH"
    assert txns._filter_type is None
    assert txns._filter_category_id is None
    assert txns._filter_amount_preset == "ALL"
    assert txns._sort_order == "DATE_DESC"
    assert txns._get_active_filters_count() == 0


def test_transactions_refresh_filtering_logic():
    from unittest.mock import MagicMock
    from datetime import date
    from screens.transactions.transactions_screen import TransactionsView
    from database.models import Transaction, TransactionType, Category

    txns = TransactionsView()
    txns.build()

    cat_food = Category(id=1, name="Food & Dining", icon="restaurant", color="#8A4CFC")
    cat_shop = Category(id=2, name="Shopping", icon="shopping_bag", color="#CA3513")

    mock_data = [
        Transaction(
            id=101,
            user_id=1,
            transaction_type=TransactionType.EXPENSE,
            amount_paise=35000,  # ₹350 (< ₹500)
            transaction_date=date.today(),
            description="Coffee",
            category=cat_food,
            category_id=1,
        ),
        Transaction(
            id=102,
            user_id=1,
            transaction_type=TransactionType.EXPENSE,
            amount_paise=150000,  # ₹1,500 (₹500 - ₹2k)
            transaction_date=date.today(),
            description="Sneakers",
            category=cat_shop,
            category_id=2,
        ),
        Transaction(
            id=103,
            user_id=1,
            transaction_type=TransactionType.INCOME,
            amount_paise=5000000,  # ₹50,000 (> ₹10k)
            transaction_date=date.today(),
            description="Consulting Fee",
            category=None,
            category_id=None,
        ),
    ]

    txns._transaction_service.list_transactions = MagicMock(return_value=mock_data)

    # 1. Standard unfiltered refresh: all 3 items present in groups
    txns.refresh()
    assert len(txns._grouped_column.controls) > 0

    # 2. Filter by amount: UNDER_500
    txns._filter_amount_preset = "UNDER_500"
    txns.refresh()
    assert len(txns._grouped_column.controls) > 0

    # 3. Filter by amount: ABOVE_10000
    txns._filter_amount_preset = "ABOVE_10000"
    txns.refresh()
    assert len(txns._grouped_column.controls) > 0

    # 4. Zero matching results with active filter triggers empty state card
    txns._filter_amount_preset = "2000_TO_10000"  # No item between ₹2,000 and ₹10,000
    txns.refresh()
    # Expect empty state card because a filter is active
    assert len(txns._grouped_column.controls) == 1
    empty_card = txns._grouped_column.controls[0]
    # Check that empty card contains "No Matching Transactions" text
    assert any("No Matching Transactions" in str(getattr(ctrl, "value", "")) for ctrl in empty_card.content.controls if hasattr(ctrl, "value"))










