"""
Spendora — Category Management & New Category Creation Dialog (Flet).

Provides full Category CRUD matching Google Stitch:
- Full list of active categories with icons, colors, and subcategories
- "+ New Category" creation with name, icon picker, and palette color selector
- "+ Add Label" to add subcategories under any category
- Soft-delete category and subcategory actions
- Reactive callbacks to refresh dashboard and transaction forms
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
from database.models import Category
from services.category_service import CategoryService
from services.profile_service import ProfileService

POPULAR_ICONS = [
    ("restaurant", ft.Icons.RESTAURANT, "Food"),
    ("shopping", ft.Icons.SHOPPING_BAG, "Shopping"),
    ("car", ft.Icons.DIRECTIONS_CAR, "Transport"),
    ("home", ft.Icons.HOME, "Housing"),
    ("laptop", ft.Icons.LAPTOP, "Tech"),
    ("fitness", ft.Icons.FITNESS_CENTER, "Fitness"),
    ("local_hospital", ft.Icons.LOCAL_HOSPITAL, "Health"),
    ("flight", ft.Icons.FLIGHT, "Travel"),
    ("school", ft.Icons.SCHOOL, "Education"),
    ("movie", ft.Icons.MOVIE, "Entertainment"),
    ("payments", ft.Icons.PAYMENTS, "Salary"),
    ("savings", ft.Icons.SAVINGS, "Savings"),
]

PALETTE_COLORS = [
    "#8B5CF6",  # Electric Purple
    "#3B82F6",  # Royal Blue
    "#10B981",  # Emerald
    "#FF5722",  # Coral
    "#F59E0B",  # Amber
    "#EC4899",  # Pink
    "#06B6D4",  # Cyan
    "#84CC16",  # Lime
]


def show_category_management_dialog(
    page: ft.Page,
    on_change: Optional[Callable[[], None]] = None,
) -> None:
    """Open the Category Management modal."""
    category_service = CategoryService()
    profile_service = ProfileService()
    user = profile_service.get_current_user()
    user_id = user.id if user else 1

    is_dark = theme_manager.is_dark()
    bg_color = "#0B0F19" if is_dark else "#FAF8FF"
    card_bg = "#151D30" if is_dark else "#FFFFFF"
    input_bg = "#0F1726" if is_dark else "#F8FAFC"
    border_color = "#222E48" if is_dark else "#E2E8F0"
    text_primary = "#FFFFFF" if is_dark else "#151B2B"
    text_secondary = "#94A3B8" if is_dark else "#747688"
    accent_purple = "#8B5CF6" if is_dark else COLOR_PRIMARY

    categories_column = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)

    def _close(e=None):
        main_dialog.open = False
        try:
            page.update()
        except Exception:
            pass
        if on_change:
            on_change()

    def _refresh_categories_list():
        categories_column.controls.clear()
        cats = category_service.list_categories(user_id=user_id)
        if not cats:
            categories_column.controls.append(
                ft.Container(
                    padding=ft.Padding.all(20),
                    alignment=ft.Alignment.CENTER,
                    content=ft.Text("No categories found. Create one below!", color=text_secondary, size=13),
                )
            )
        else:
            from components.transaction_card import _resolve_icon
            for cat in cats:
                cat_icon = _resolve_icon(cat.icon or "payments")
                cat_color = cat.color or accent_purple

                # Subcategory chips
                sub_chips = []
                for sub in cat.subcategories or []:
                    if sub.is_active:
                        sub_chips.append(
                            ft.Container(
                                bgcolor=input_bg,
                                border=ft.Border.all(1, border_color),
                                border_radius=12,
                                padding=ft.Padding.symmetric(horizontal=8, vertical=4),
                                content=ft.Row(
                                    spacing=4,
                                    tight=True,
                                    controls=[
                                        ft.Text(sub.name, size=11, color=text_secondary),
                                        ft.GestureDetector(
                                            content=ft.Icon(ft.Icons.CLOSE, size=12, color=text_secondary),
                                            on_tap=lambda ev, sid=sub.id: _delete_sub(sid),
                                        ),
                                    ],
                                ),
                            )
                        )

                cat_card = ft.Container(
                    bgcolor=card_bg,
                    border=ft.Border.all(1, border_color),
                    border_radius=16,
                    padding=ft.Padding.all(12),
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
                                                width=36,
                                                height=36,
                                                border_radius=12,
                                                bgcolor=f"{cat_color}22",
                                                alignment=ft.Alignment.CENTER,
                                                content=ft.Icon(cat_icon, color=cat_color, size=18),
                                            ),
                                            ft.Text(cat.name, size=14, weight=ft.FontWeight.W_700, color=text_primary),
                                        ],
                                    ),
                                    ft.Row(
                                        spacing=2,
                                        controls=[
                                            ft.IconButton(
                                                icon=ft.Icons.ADD_CIRCLE_OUTLINE,
                                                icon_size=18,
                                                icon_color=accent_purple,
                                                tooltip="Add Label / Subcategory",
                                                on_click=lambda ev, c=cat: _open_add_sub_dialog(c),
                                            ),
                                            ft.IconButton(
                                                icon=ft.Icons.DELETE_OUTLINE,
                                                icon_size=18,
                                                icon_color=COLOR_ERROR,
                                                tooltip="Delete Category",
                                                on_click=lambda ev, cid=cat.id, cname=cat.name: _delete_cat(cid, cname),
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                            ft.Row(wrap=True, spacing=6, run_spacing=6, controls=sub_chips) if sub_chips else ft.Container(),
                        ],
                    ),
                )
                categories_column.controls.append(cat_card)
        try:
            categories_column.update()
        except Exception:
            pass

    def _delete_cat(cid: int, name: str):
        def _confirm(ev):
            try:
                category_service.delete_category(cid, soft=True)
                confirm_dlg.open = False
                page.update()
                _refresh_categories_list()
            except Exception as ex:
                pass

        confirm_dlg = ft.AlertDialog(
            title=ft.Text("Delete Category", weight=ft.FontWeight.W_700),
            content=ft.Text(f"Delete category '{name}'? Existing transactions will retain history."),
            actions=[
                ft.TextButton("Cancel", on_click=lambda ev: _close_inner(confirm_dlg)),
                ft.ElevatedButton("Delete", bgcolor=COLOR_ERROR, color=COLOR_ON_PRIMARY, on_click=_confirm),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.overlay.append(confirm_dlg)
        confirm_dlg.open = True
        page.update()

    def _delete_sub(sid: int):
        try:
            category_service.delete_subcategory(sid, soft=True)
            _refresh_categories_list()
        except Exception:
            pass

    def _close_inner(dlg):
        dlg.open = False
        try:
            page.update()
        except Exception:
            pass

    def _open_add_sub_dialog(cat: Category):
        sub_input = ft.TextField(
            hint_text="e.g. Canteen, Online, Metro",
            bgcolor=input_bg,
            border_color=border_color,
            text_style=ft.TextStyle(color=text_primary),
            dense=True,
            autofocus=True,
        )

        def _save_sub(ev):
            val = (sub_input.value or "").strip()
            if val:
                try:
                    category_service.create_subcategory(category_id=cat.id, name=val)
                    sub_dlg.open = False
                    page.update()
                    _refresh_categories_list()
                except Exception as ex:
                    pass

        sub_dlg = ft.AlertDialog(
            title=ft.Text(f"Add Label to {cat.name}", weight=ft.FontWeight.W_700),
            content=ft.Column(
                tight=True,
                spacing=8,
                controls=[
                    ft.Text("Subcategory / Label Name:", size=12, color=text_secondary),
                    sub_input,
                ],
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda ev: _close_inner(sub_dlg)),
                ft.ElevatedButton("Add Label", bgcolor=accent_purple, color=COLOR_ON_PRIMARY, on_click=_save_sub),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.overlay.append(sub_dlg)
        sub_dlg.open = True
        page.update()

    def _open_new_category_dialog(e=None):
        name_input = ft.TextField(
            hint_text="e.g. Gaming, Investments, Gym",
            bgcolor=input_bg,
            border_color=border_color,
            text_style=ft.TextStyle(color=text_primary),
            dense=True,
            autofocus=True,
        )

        selected_icon = ["restaurant"]
        selected_color = [PALETTE_COLORS[0]]

        # Icon selection row
        icon_controls = []
        for key, ico, lbl in POPULAR_ICONS:
            def _select_ico(ev, k=key):
                selected_icon[0] = k
                for ic_c in icon_controls:
                    is_s = ic_c.data == k
                    ic_c.bgcolor = f"{selected_color[0]}33" if is_s else input_bg
                    ic_c.border = ft.Border.all(2 if is_s else 1, selected_color[0] if is_s else border_color)
                try:
                    icons_row.update()
                except Exception:
                    pass

            is_sel = (key == selected_icon[0])
            c_box = ft.Container(
                width=40,
                height=40,
                border_radius=12,
                bgcolor=f"{selected_color[0]}33" if is_sel else input_bg,
                border=ft.Border.all(2 if is_sel else 1, selected_color[0] if is_sel else border_color),
                alignment=ft.Alignment.CENTER,
                content=ft.Icon(ico, color=text_primary, size=18),
                ink=True,
                data=key,
                tooltip=lbl,
                on_click=_select_ico,
            )
            icon_controls.append(c_box)

        icons_row = ft.Row(wrap=True, spacing=8, run_spacing=8, controls=icon_controls)

        # Color selection row
        color_controls = []
        for hex_col in PALETTE_COLORS:
            def _select_col(ev, hc=hex_col):
                selected_color[0] = hc
                for cc in color_controls:
                    is_c = cc.data == hc
                    cc.border = ft.Border.all(3 if is_c else 0, "#FFFFFF" if is_c else border_color)
                # update icon box colors
                for ic_c in icon_controls:
                    if ic_c.data == selected_icon[0]:
                        ic_c.bgcolor = f"{hc}33"
                        ic_c.border = ft.Border.all(2, hc)
                try:
                    colors_row.update()
                    icons_row.update()
                except Exception:
                    pass

            is_c = (hex_col == selected_color[0])
            c_box = ft.Container(
                width=28,
                height=28,
                border_radius=14,
                bgcolor=hex_col,
                border=ft.Border.all(3 if is_c else 0, "#FFFFFF" if is_c else border_color),
                ink=True,
                data=hex_col,
                on_click=_select_col,
            )
            color_controls.append(c_box)

        colors_row = ft.Row(spacing=8, controls=color_controls)

        error_msg = ft.Text("", color=COLOR_ERROR, size=12, visible=False)

        def _create_cat(ev):
            cname = (name_input.value or "").strip()
            if not cname:
                error_msg.value = "Please enter a category name."
                error_msg.visible = True
                try:
                    error_msg.update()
                except Exception:
                    pass
                return

            try:
                category_service.create_category(
                    user_id=user_id,
                    name=cname,
                    icon=selected_icon[0],
                    color=selected_color[0],
                )
                new_cat_dlg.open = False
                page.update()
                _refresh_categories_list()
            except Exception as ex:
                error_msg.value = str(ex)
                error_msg.visible = True
                try:
                    error_msg.update()
                except Exception:
                    pass

        new_cat_dlg = ft.AlertDialog(
            title=ft.Text("Create New Category", weight=ft.FontWeight.W_700),
            content=ft.Container(
                width=360,
                content=ft.Column(
                    tight=True,
                    spacing=12,
                    controls=[
                        ft.Text("Category Name", size=12, weight=ft.FontWeight.W_600, color=text_secondary),
                        name_input,
                        error_msg,
                        ft.Text("Select Icon", size=12, weight=ft.FontWeight.W_600, color=text_secondary),
                        icons_row,
                        ft.Text("Select Accent Color", size=12, weight=ft.FontWeight.W_600, color=text_secondary),
                        colors_row,
                    ],
                ),
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda ev: _close_inner(new_cat_dlg)),
                ft.ElevatedButton("Create", bgcolor=accent_purple, color=COLOR_ON_PRIMARY, on_click=_create_cat),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.overlay.append(new_cat_dlg)
        new_cat_dlg.open = True
        page.update()

    _refresh_categories_list()

    main_dialog = ft.AlertDialog(
        modal=True,
        bgcolor=bg_color,
        content_padding=ft.Padding.all(16),
        shape=ft.RoundedRectangleBorder(radius=24),
        content=ft.Container(
            width=420,
            height=620,
            content=ft.Column(
                spacing=14,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Row(
                                spacing=8,
                                controls=[
                                    ft.IconButton(ft.Icons.CLOSE, icon_color=text_primary, icon_size=20, on_click=_close),
                                    ft.Text("Categories & Labels", size=18, weight=ft.FontWeight.W_800, color=text_primary),
                                ],
                            ),
                            ft.Container(
                                gradient=ft.LinearGradient(colors=[accent_purple, "#6D28D9"]),
                                border_radius=14,
                                padding=ft.Padding.symmetric(horizontal=12, vertical=6),
                                ink=True,
                                on_click=_open_new_category_dialog,
                                content=ft.Row(
                                    spacing=4,
                                    tight=True,
                                    controls=[
                                        ft.Icon(ft.Icons.ADD, size=14, color="#FFFFFF"),
                                        ft.Text("New Category", size=11, weight=ft.FontWeight.W_700, color="#FFFFFF"),
                                    ],
                                ),
                            ),
                        ],
                    ),
                    ft.Container(
                        expand=True,
                        content=categories_column,
                    ),
                ],
            ),
        ),
    )

    page.overlay.append(main_dialog)
    main_dialog.open = True
    try:
        page.update()
    except Exception:
        pass
