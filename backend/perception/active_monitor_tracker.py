"""
Active monitor tracker for smart screenshot filtering

Tracks which monitor is currently active based on mouse/keyboard activity,
enabling smart screenshot capture that only captures the active screen.

Key behavior:
- Always uses the last known mouse position to determine active monitor
- Never falls back to capturing all monitors due to inactivity
- This ensures correct behavior when watching videos (cursor hidden but still on one screen)
"""

import time
from typing import Dict, List, Optional

from core.logger import get_logger

logger = get_logger(__name__)


class ActiveMonitorTracker:
    """Tracks the currently active monitor based on user activity"""

    def __init__(self):
        """Initialize active monitor tracker"""
        self._current_monitor_index: int = 1  # Default to primary monitor
        self._monitors_info: List[Dict] = []
        self._last_activity_time: float = time.time()
        self._last_mouse_position: Optional[tuple[int, int]] = None

    def update_monitors_info(self, monitors: List[Dict]) -> None:
        """
        Update the list of available monitors

        Args:
            monitors: List of monitor info dicts with 'index', 'left', 'top', 'width', 'height'
        """
        self._monitors_info = monitors
        logger.debug(f"Updated monitors info: {len(monitors)} monitors")

    def update_from_mouse(self, x: int, y: int) -> None:
        """
        Update active monitor based on mouse position

        Args:
            x: Mouse X coordinate (absolute)
            y: Mouse Y coordinate (absolute)
        """
        if not self._monitors_info:
            logger.warning("No monitor info available, cannot update active monitor")
            return

        # Find which monitor contains this coordinate
        new_monitor_index = self._get_monitor_from_position(x, y)

        if new_monitor_index != self._current_monitor_index:
            logger.debug(
                f"Active monitor changed: {self._current_monitor_index} -> {new_monitor_index} "
                f"(mouse at {x}, {y})"
            )
            self._current_monitor_index = new_monitor_index

        self._last_activity_time = time.time()
        self._last_mouse_position = (x, y)

    def update_from_keyboard(self) -> None:
        """
        Update last activity time from keyboard event

        Keeps the tracker aware of user activity even when mouse isn't moving
        (e.g., watching videos, reading content, typing)
        """
        self._last_activity_time = time.time()
        logger.debug("Activity time updated from keyboard event")

    def _get_monitor_from_position(self, x: int, y: int) -> int:
        """
        Determine which monitor contains the given coordinates

        Args:
            x: Absolute X coordinate
            y: Absolute Y coordinate

        Returns:
            Monitor index (1-based), defaults to primary (1) if not found
        """
        for monitor in self._monitors_info:
            left = monitor.get("left", 0)
            top = monitor.get("top", 0)
            width = monitor.get("width", 0)
            height = monitor.get("height", 0)

            # Check if point is within monitor bounds
            if (left <= x < left + width) and (top <= y < top + height):
                return monitor.get("index", 1)

        # Fallback: return primary monitor
        logger.debug(
            f"Position ({x}, {y}) not found in any monitor bounds, "
            f"using primary monitor"
        )
        return self._get_primary_monitor_index()

    def _get_primary_monitor_index(self) -> int:
        """Get the primary monitor index (marked as is_primary or first monitor)"""
        for monitor in self._monitors_info:
            if monitor.get("is_primary", False):
                return monitor.get("index", 1)
        return 1  # Default to first monitor

    def get_active_monitor_index(self) -> int:
        """
        Get the currently active monitor index

        Always returns the last known active monitor based on mouse position.
        Never returns "capture all" - maintains single monitor focus even
        during long periods of inactivity (e.g., watching videos).

        Returns:
            Monitor index (1-based)
        """
        return self._current_monitor_index

    def get_stats(self) -> Dict:
        """Get tracker statistics for debugging"""
        inactive_duration = time.time() - self._last_activity_time
        return {
            "current_monitor_index": self._current_monitor_index,
            "monitors_count": len(self._monitors_info),
            "last_mouse_position": self._last_mouse_position,
            "inactive_duration_seconds": round(inactive_duration, 2),
        }
