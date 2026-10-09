"""
Spendora — Real-Time Clock & Date Service.

Provides real-time auto-updating of:
- Time (12-hour format with AM/PM and seconds)
- Date (formatted day, month, year)
- Day of the week (e.g., Sunday, Monday)
- Dynamic contextual greeting (Good Morning, Good Afternoon, Good Evening, Good Night)
- Centralized subscriber bus to tick and update UI controls across the entire app in real time.
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import date, datetime
from typing import Callable, List, Optional, Tuple

import flet as ft

logger = logging.getLogger(__name__)


class ClockService:
    """Central singleton managing real-time time, date, day and UI subscriptions."""

    _instance: Optional[ClockService] = None

    def __new__(cls) -> ClockService:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self._listeners: List[Callable[[datetime], None]] = []
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._ticker_thread: Optional[threading.Thread] = None

    # ---------------------------------------------------------------------------
    # Time & Date Formats
    # ---------------------------------------------------------------------------

    def get_now(self) -> datetime:
        """Return current local datetime."""
        return datetime.now()

    def get_current_date(self) -> date:
        """Return current local date."""
        return date.today()

    def get_day_name(self, dt: Optional[datetime] = None) -> str:
        """Return full weekday name (e.g., 'Sunday', 'Monday')."""
        target = dt or datetime.now()
        return target.strftime("%A")

    def get_day_short(self, dt: Optional[datetime] = None) -> str:
        """Return abbreviated weekday name (e.g., 'Sun', 'Mon')."""
        target = dt or datetime.now()
        return target.strftime("%a")

    def get_date_formatted(self, dt: Optional[datetime] = None, style: str = "medium") -> str:
        """Return formatted date string (e.g., '04 Oct 2026' or '04 October 2026')."""
        target = dt or datetime.now()
        if style == "full":
            return target.strftime("%d %B %Y")
        elif style == "us":
            return target.strftime("%b %d, %Y")
        return target.strftime("%d %b %Y")

    def get_time_formatted(self, dt: Optional[datetime] = None, include_seconds: bool = True) -> str:
        """Return formatted 12-hour time string with AM/PM (e.g., '04:31:49 PM')."""
        target = dt or datetime.now()
        fmt = "%I:%M:%S %p" if include_seconds else "%I:%M %p"
        return target.strftime(fmt)

    def get_greeting(self, dt: Optional[datetime] = None) -> Tuple[str, str]:
        """
        Return contextual greeting and emoji based on current hour.
        - 05:00 to 11:59 -> ('Good Morning', '☀️')
        - 12:00 to 16:59 -> ('Good Afternoon', '🌤️')
        - 17:00 to 20:59 -> ('Good Evening', '🌆')
        - 21:00 to 04:59 -> ('Good Night', '🌙')
        """
        target = dt or datetime.now()
        hour = target.hour
        if 5 <= hour < 12:
            return "Good Morning", "☀️"
        elif 12 <= hour < 17:
            return "Good Afternoon", "🌤️"
        elif 17 <= hour < 21:
            return "Good Evening", "🌆"
        else:
            return "Good Night", "🌙"

    def get_greeting_str(self, dt: Optional[datetime] = None) -> str:
        """Return combined greeting string (e.g., 'Good Afternoon 🌤️')."""
        text, emoji = self.get_greeting(dt)
        return f"{text} {emoji}"

    def format_live_display(self, dt: Optional[datetime] = None) -> str:
        """Return full live display: 'Sunday, 04 Oct 2026 • 04:31:49 PM'."""
        target = dt or datetime.now()
        day = self.get_day_name(target)
        d_str = self.get_date_formatted(target, "medium")
        t_str = self.get_time_formatted(target, include_seconds=True)
        return f"{day}, {d_str} • {t_str}"

    def format_short_status(self, dt: Optional[datetime] = None) -> str:
        """Return short status bar format: 'Sun, 04 Oct 2026 • 04:31:49 PM'."""
        target = dt or datetime.now()
        day = self.get_day_short(target)
        d_str = self.get_date_formatted(target, "medium")
        t_str = self.get_time_formatted(target, include_seconds=True)
        return f"{day}, {d_str} • {t_str}"

    def format_day_and_date(self, d: Optional[date | datetime] = None) -> str:
        """Return day and date string: 'Sunday, 04 Oct 2026'."""
        target = d or date.today()
        day = target.strftime("%A")
        d_str = target.strftime("%d %b %Y")
        return f"{day}, {d_str}"

    # ---------------------------------------------------------------------------
    # Real-Time Subscription & Ticker Thread
    # ---------------------------------------------------------------------------

    def subscribe(self, listener: Callable[[datetime], None]) -> None:
        """Subscribe a callable to receive 1-second real-time clock updates."""
        with self._lock:
            if listener not in self._listeners:
                self._listeners.append(listener)
        self.start()

    def unsubscribe(self, listener: Callable[[datetime], None]) -> None:
        """Unsubscribe a callable from clock updates."""
        with self._lock:
            if listener in self._listeners:
                self._listeners.remove(listener)

    @staticmethod
    def is_control_attached(control: Any) -> bool:
        """Safely check if a Flet control is currently attached/mounted on an active Page."""
        if control is None:
            return False
        try:
            return control.page is not None
        except Exception:
            return False

    def register_control(
        self,
        control: ft.Control,
        format_fn: Callable[[datetime], str],
    ) -> Callable[[], None]:
        """
        Safely bind a Flet Text-like control to real-time clock updates.
        Returns an unregister callback to disconnect when unmounted.
        """
        def _on_tick(now: datetime) -> None:
            new_val = format_fn(now)
            if getattr(control, "value", None) != new_val:
                control.value = new_val
            # Only attempt update if the control is attached to a mounted page
            if self.is_control_attached(control):
                try:
                    control.update()
                except Exception as ex:
                    logger.debug("Failed updating live clock control: %s", ex)

        self.subscribe(_on_tick)
        return lambda: self.unsubscribe(_on_tick)

    def start(self) -> None:
        """Start the background ticker thread if not already running."""
        if self._ticker_thread is not None and self._ticker_thread.is_alive():
            return
        self._stop_event.clear()
        self._ticker_thread = threading.Thread(
            target=self._run_ticker,
            daemon=True,
            name="LeakseeClockTicker",
        )
        self._ticker_thread.start()

    def stop(self) -> None:
        """Stop the background ticker thread cleanly."""
        self._stop_event.set()
        if self._ticker_thread is not None:
            self._ticker_thread.join(timeout=1.5)
            self._ticker_thread = None

    def is_running(self) -> bool:
        """Return True if background ticker is currently active."""
        return self._ticker_thread is not None and self._ticker_thread.is_alive()

    def _run_ticker(self) -> None:
        """Internal background ticker loop aligned with exact seconds."""
        while not self._stop_event.is_set():
            now = datetime.now()
            # Sub-second alignment so updates occur promptly on second roll-over
            micro = now.microsecond
            sleep_sec = 1.0 - (micro / 1_000_000.0)
            if sleep_sec < 0.05:
                sleep_sec = 1.0

            if self._stop_event.wait(timeout=sleep_sec):
                break

            current_now = datetime.now()
            with self._lock:
                listeners_copy = list(self._listeners)

            for listener in listeners_copy:
                try:
                    listener(current_now)
                except Exception as ex:
                    logger.debug("Clock listener error: %s", ex)


# Global singleton instance
clock_service = ClockService()
