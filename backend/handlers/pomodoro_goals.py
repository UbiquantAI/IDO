"""
Pomodoro Goals Handler - API endpoints for managing focus time goals
"""

from datetime import datetime
from typing import Optional

from core.logger import get_logger
from core.settings import get_settings
from models.base import BaseModel
from models.responses import TimedOperationResponse

# CRITICAL: Use relative import to avoid circular imports
from . import api_handler

logger = get_logger(__name__)


# ============ Request Models ============


class UpdatePomodoroGoalsRequest(BaseModel):
    """Request to update Pomodoro goal settings"""

    daily_focus_goal_minutes: Optional[int] = None
    weekly_focus_goal_minutes: Optional[int] = None


# ============ Response Models ============


class PomodoroGoalsData(BaseModel):
    """Pomodoro goal settings data"""

    daily_focus_goal_minutes: int
    weekly_focus_goal_minutes: int


class GetPomodoroGoalsResponse(TimedOperationResponse):
    """Response with Pomodoro goal settings"""

    data: Optional[PomodoroGoalsData] = None


class UpdatePomodoroGoalsResponse(TimedOperationResponse):
    """Response with updated Pomodoro goal settings"""

    data: Optional[PomodoroGoalsData] = None


# ============ API Handlers ============


@api_handler(
    method="GET",
    path="/pomodoro/goals",
    tags=["pomodoro"],
)
async def get_pomodoro_goals() -> GetPomodoroGoalsResponse:
    """
    Get Pomodoro focus time goal settings

    Returns:
    - daily_focus_goal_minutes: Daily goal in minutes
    - weekly_focus_goal_minutes: Weekly goal in minutes
    """
    try:
        settings = get_settings()
        goals = settings.get_pomodoro_goal_settings()

        return GetPomodoroGoalsResponse(
            success=True,
            message="Retrieved Pomodoro goals",
            data=PomodoroGoalsData(
                daily_focus_goal_minutes=goals["daily_focus_goal_minutes"],
                weekly_focus_goal_minutes=goals["weekly_focus_goal_minutes"],
            ),
            timestamp=datetime.now().isoformat(),
        )
    except Exception as e:
        logger.error(f"Failed to get Pomodoro goals: {e}", exc_info=True)
        return GetPomodoroGoalsResponse(
            success=False,
            message=f"Failed to get goals: {str(e)}",
            timestamp=datetime.now().isoformat(),
        )


@api_handler(
    body=UpdatePomodoroGoalsRequest,
    method="POST",
    path="/pomodoro/goals",
    tags=["pomodoro"],
)
async def update_pomodoro_goals(
    body: UpdatePomodoroGoalsRequest,
) -> UpdatePomodoroGoalsResponse:
    """
    Update Pomodoro focus time goal settings

    Args:
        body: Contains daily and/or weekly goal values

    Returns:
        Updated goal settings
    """
    try:
        settings = get_settings()

        # Build update dict with only provided fields
        updates = {}
        if body.daily_focus_goal_minutes is not None:
            updates["daily_focus_goal_minutes"] = body.daily_focus_goal_minutes
        if body.weekly_focus_goal_minutes is not None:
            updates["weekly_focus_goal_minutes"] = body.weekly_focus_goal_minutes

        # Update settings
        updated_goals = settings.update_pomodoro_goal_settings(updates)

        logger.info(f"Updated Pomodoro goals: {updated_goals}")

        return UpdatePomodoroGoalsResponse(
            success=True,
            message="Pomodoro goals updated successfully",
            data=PomodoroGoalsData(
                daily_focus_goal_minutes=updated_goals["daily_focus_goal_minutes"],
                weekly_focus_goal_minutes=updated_goals["weekly_focus_goal_minutes"],
            ),
            timestamp=datetime.now().isoformat(),
        )
    except Exception as e:
        logger.error(f"Failed to update Pomodoro goals: {e}", exc_info=True)
        return UpdatePomodoroGoalsResponse(
            success=False,
            message=f"Failed to update goals: {str(e)}",
            timestamp=datetime.now().isoformat(),
        )
