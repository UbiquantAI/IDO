"""
Pomodoro Configuration Presets - API endpoint for getting preset configurations

Provides predefined Pomodoro configurations for common use cases.
"""

from datetime import datetime
from typing import List

from core.logger import get_logger
from models.base import BaseModel
from models.responses import TimedOperationResponse

# CRITICAL: Use relative import to avoid circular imports
from . import api_handler

logger = get_logger(__name__)


# ============ Response Models ============


class PomodoroPreset(BaseModel):
    """Pomodoro configuration preset"""

    id: str
    name: str
    description: str
    work_duration_minutes: int
    break_duration_minutes: int
    total_rounds: int
    icon: str = "⏱️"


class GetPomodoroPresetsResponse(TimedOperationResponse):
    """Response with list of Pomodoro presets"""

    data: List[PomodoroPreset] = []


# ============ Preset Definitions ============

POMODORO_PRESETS = [
    PomodoroPreset(
        id="classic",
        name="Classic Pomodoro",
        description="Traditional 25/5 technique - 4 rounds",
        work_duration_minutes=25,
        break_duration_minutes=5,
        total_rounds=4,
        icon="🍅",
    ),
    PomodoroPreset(
        id="deep-work",
        name="Deep Work",
        description="Extended focus sessions - 50/10 for intense work",
        work_duration_minutes=50,
        break_duration_minutes=10,
        total_rounds=3,
        icon="🎯",
    ),
    PomodoroPreset(
        id="quick-sprint",
        name="Quick Sprint",
        description="Short bursts - 15/3 for quick tasks",
        work_duration_minutes=15,
        break_duration_minutes=3,
        total_rounds=6,
        icon="⚡",
    ),
    PomodoroPreset(
        id="ultra-focus",
        name="Ultra Focus",
        description="Maximum concentration - 90/15 for deep thinking",
        work_duration_minutes=90,
        break_duration_minutes=15,
        total_rounds=2,
        icon="🧠",
    ),
    PomodoroPreset(
        id="balanced",
        name="Balanced Flow",
        description="Moderate pace - 40/8 for sustained productivity",
        work_duration_minutes=40,
        break_duration_minutes=8,
        total_rounds=4,
        icon="⚖️",
    ),
]


# ============ API Handler ============


@api_handler(method="GET", path="/pomodoro/presets", tags=["pomodoro"])
async def get_pomodoro_presets() -> GetPomodoroPresetsResponse:
    """
    Get available Pomodoro configuration presets

    Returns a list of predefined configurations including:
    - Classic Pomodoro (25/5)
    - Deep Work (50/10)
    - Quick Sprint (15/3)
    - Ultra Focus (90/15)
    - Balanced Flow (40/8)
    """
    try:
        logger.debug(f"Returning {len(POMODORO_PRESETS)} Pomodoro presets")

        return GetPomodoroPresetsResponse(
            success=True,
            message=f"Retrieved {len(POMODORO_PRESETS)} presets",
            data=POMODORO_PRESETS,
            timestamp=datetime.now().isoformat(),
        )

    except Exception as e:
        logger.error(f"Failed to get Pomodoro presets: {e}", exc_info=True)
        return GetPomodoroPresetsResponse(
            success=False,
            message=f"Failed to get presets: {str(e)}",
            timestamp=datetime.now().isoformat(),
        )
