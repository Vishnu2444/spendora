"""
Spendora — DistributionBar component (Flet).

Simple wrapper around ft.ProgressBar for spending distribution gauges.
"""

from __future__ import annotations

import flet as ft


def build_distribution_bar(
    percentage: float,
    color: str = "#4ECDC4",
) -> ft.ProgressBar:
    """Build a coloured progress bar for category spending share."""
    return ft.ProgressBar(
        value=percentage / 100.0,
        color=color,
        bgcolor=f"{color}1A",
        bar_height=6,
        border_radius=3,
    )
