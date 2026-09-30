"""
Spendora (Trackz) — Flet 1.0 Compatibility Layer.

Ensures seamless interoperability between Material Design 3 and Flet 1.0
control specifications:
- Maps Padding, BorderRadius, Border, Alignment
- Patches TextButton, ElevatedButton, and OutlinedButton to support both
  content, text, and border_radius keyword arguments.
- Patches Row and Column to accept main_axis_alignment.
"""

from __future__ import annotations

import flet as ft

# 1. Structural styling compatibility
import sys

ft.padding = ft.Padding
ft.border_radius = ft.BorderRadius
ft.border = ft.Border
ft.alignment = ft.Alignment
ft.alignment.center = ft.Alignment.CENTER
ft.alignment.bottom_center = ft.Alignment.BOTTOM_CENTER
ft.alignment.top_center = ft.Alignment.TOP_CENTER
ft.alignment.top_left = ft.Alignment.TOP_LEFT
ft.alignment.bottom_left = ft.Alignment.BOTTOM_LEFT
ft.alignment.center_left = ft.Alignment.CENTER_LEFT
ft.alignment.center_right = ft.Alignment.CENTER_RIGHT

try:
    import flet.controls.border as _b_mod
    _b_mod.all = ft.Border.all
    _b_mod.only = ft.Border.only
    _b_mod.symmetric = ft.Border.symmetric
except Exception:
    pass

try:
    import flet.controls.padding as _p_mod
    _p_mod.all = ft.Padding.all
    _p_mod.only = ft.Padding.only
    _p_mod.symmetric = ft.Padding.symmetric
except Exception:
    pass

try:
    import flet.controls.border_radius as _br_mod
    _br_mod.all = ft.BorderRadius.all
    _br_mod.only = ft.BorderRadius.only
    _br_mod.horizontal = ft.BorderRadius.horizontal
    _br_mod.vertical = ft.BorderRadius.vertical
except Exception:
    pass

try:
    import flet.controls.alignment as _a_mod
    _a_mod.center = ft.Alignment.CENTER
    _a_mod.top_center = ft.Alignment.TOP_CENTER
    _a_mod.bottom_center = ft.Alignment.BOTTOM_CENTER
    _a_mod.top_left = ft.Alignment.TOP_LEFT
    _a_mod.bottom_left = ft.Alignment.BOTTOM_LEFT
    _a_mod.center_left = ft.Alignment.CENTER_LEFT
    _a_mod.center_right = ft.Alignment.CENTER_RIGHT
except Exception:
    pass



def _apply_border_radius(kwargs: dict) -> None:
    br = kwargs.pop("border_radius", None)
    if br is not None:
        style = kwargs.get("style") or ft.ButtonStyle()
        style.shape = ft.RoundedRectangleBorder(radius=br)
        kwargs["style"] = style


# 2. Button class compatibility
class CompatibleElevatedButton(ft.FilledButton):
    def __init__(self, text=None, *args, **kwargs):
        content = kwargs.pop("content", text)
        _apply_border_radius(kwargs)
        super().__init__(content, *args, **kwargs)


class CompatibleTextButton(ft.TextButton):
    def __init__(self, text=None, *args, **kwargs):
        content = kwargs.pop("content", text)
        _apply_border_radius(kwargs)
        super().__init__(content, *args, **kwargs)


class CompatibleOutlinedButton(ft.OutlinedButton):
    def __init__(self, text=None, *args, **kwargs):
        content = kwargs.pop("content", text)
        _apply_border_radius(kwargs)
        super().__init__(content, *args, **kwargs)


# 3. Row & Column layout compatibility
_orig_row = ft.Row


class CompatibleRow(_orig_row):
    def __init__(self, *args, **kwargs):
        if "main_axis_alignment" in kwargs:
            kwargs["alignment"] = kwargs.pop("main_axis_alignment")
        super().__init__(*args, **kwargs)


_orig_col = ft.Column


class CompatibleColumn(_orig_col):
    def __init__(self, *args, **kwargs):
        if "main_axis_alignment" in kwargs:
            kwargs["alignment"] = kwargs.pop("main_axis_alignment")
        super().__init__(*args, **kwargs)


ft.ElevatedButton = CompatibleElevatedButton
ft.TextButton = CompatibleTextButton
ft.OutlinedButton = CompatibleOutlinedButton
ft.Row = CompatibleRow
ft.Column = CompatibleColumn

if hasattr(ft, "NavigationBarDestination"):
    ft.NavigationDestination = ft.NavigationBarDestination

if not hasattr(ft, "app") and hasattr(ft, "run"):
    def _compat_app(target=None, *args, **kwargs):
        if target:
            return ft.run(target, *args, **kwargs)
        return ft.run(*args, **kwargs)
    ft.app = _compat_app


