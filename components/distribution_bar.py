"""
Spendora — DistributionBar component.

A lightweight horizontal progress indicator that displays a filled percentage gauge
using hardware-accelerated Kivy canvas instructions.
"""

from __future__ import annotations

from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp
from kivy.uix.widget import Widget


class DistributionBar(Widget):
    """
    Renders a rounded track and filled progress indicator representing a percentage (0.0 to 100.0).
    """

    def __init__(
        self,
        percentage: float = 0.0,
        color_rgba: tuple = (0.58, 0.45, 0.95, 1.0),
        track_rgba: tuple = (0.2, 0.25, 0.35, 0.5),
        bar_height: float = 8.0,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.size_hint_y = None
        self.height = dp(bar_height)
        self._percentage = max(0.0, min(100.0, float(percentage)))
        self._color_rgba = color_rgba
        self._track_rgba = track_rgba
        self.bind(pos=self._redraw, size=self._redraw)
        self._redraw()

    def set_percentage(self, percentage: float, color_rgba: tuple = None) -> None:
        """Update the percentage and redraw."""
        self._percentage = max(0.0, min(100.0, float(percentage)))
        if color_rgba is not None:
            self._color_rgba = color_rgba
        self._redraw()

    def _redraw(self, *args) -> None:
        self.canvas.clear()
        with self.canvas:
            # Track (background)
            Color(*self._track_rgba)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(self.height / 2)])

            # Filled bar
            if self._percentage > 0:
                Color(*self._color_rgba)
                fill_w = max(dp(self.height), self.width * (self._percentage / 100.0))
                # Clamp to avoid extending past widget width
                fill_w = min(self.width, fill_w)
                RoundedRectangle(
                    pos=self.pos,
                    size=(fill_w, self.height),
                    radius=[dp(self.height / 2)],
                )
