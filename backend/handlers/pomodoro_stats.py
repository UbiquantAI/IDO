"""
Pomodoro Statistics Handler - API endpoints for Pomodoro session statistics

Endpoints:
- POST /pomodoro/stats - Get Pomodoro statistics for a specific date
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from core.db import get_db
from core.logger import get_logger
from models.base import BaseModel
from models.responses import PomodoroSessionData, TimedOperationResponse

# CRITICAL: Use relative import to avoid circular imports
from . import api_handler

logger = get_logger(__name__)


# ============ Request Models ============


class GetPomodoroStatsRequest(BaseModel):
    """Request to get Pomodoro statistics for a specific date"""

    date: str  # YYYY-MM-DD format


# ============ Response Models ============


class PomodoroStatsData(BaseModel):
    """Pomodoro statistics for a specific date"""

    date: str
    completed_count: int
    total_focus_minutes: int
    average_duration_minutes: int
    sessions: List[Dict[str, Any]]  # Recent sessions for the day


class GetPomodoroStatsResponse(TimedOperationResponse):
    """Response with Pomodoro statistics"""

    data: Optional[PomodoroStatsData] = None


# ============ API Handlers ============


@api_handler(
    body=GetPomodoroStatsRequest,
    method="POST",
    path="/pomodoro/stats",
    tags=["pomodoro"],
)
async def get_pomodoro_stats(
    body: GetPomodoroStatsRequest,
) -> GetPomodoroStatsResponse:
    """
    Get Pomodoro statistics for a specific date

    Returns:
    - Number of completed sessions
    - Total focus time (minutes)
    - Average session duration (minutes)
    - List of all sessions for that day
    """
    try:
        db = get_db()

        # Validate date format
        try:
            datetime.fromisoformat(body.date)
        except ValueError:
            return GetPomodoroStatsResponse(
                success=False,
                message="Invalid date format. Expected YYYY-MM-DD",
                timestamp=datetime.now().isoformat(),
            )

        # Get daily stats from repository
        stats = await db.pomodoro_sessions.get_daily_stats(body.date)

        # Optionally fetch associated TODO titles for sessions
        sessions_with_todos = []
        for session in stats.get("sessions", []):
            session_data = dict(session)

            # If session has associated_todo_id, fetch TODO title
            if session_data.get("associated_todo_id"):
                try:
                    todo = await db.todos.get_by_id(session_data["associated_todo_id"])
                    if todo and not todo.get("deleted"):
                        session_data["associated_todo_title"] = todo.get("title")
                    else:
                        session_data["associated_todo_title"] = None
                except Exception as e:
                    logger.warning(
                        f"Failed to fetch TODO for session {session_data.get('id')}: {e}"
                    )
                    session_data["associated_todo_title"] = None

            sessions_with_todos.append(session_data)

        logger.debug(
            f"Retrieved Pomodoro stats for {body.date}: "
            f"{stats['completed_count']} completed, "
            f"{stats['total_focus_minutes']} minutes"
        )

        return GetPomodoroStatsResponse(
            success=True,
            message=f"Retrieved statistics for {body.date}",
            data=PomodoroStatsData(
                date=body.date,
                completed_count=stats["completed_count"],
                total_focus_minutes=stats["total_focus_minutes"],
                average_duration_minutes=stats["average_duration_minutes"],
                sessions=sessions_with_todos,
            ),
            timestamp=datetime.now().isoformat(),
        )

    except Exception as e:
        logger.error(f"Failed to get Pomodoro stats: {e}", exc_info=True)
        return GetPomodoroStatsResponse(
            success=False,
            message=f"Failed to get statistics: {str(e)}",
            timestamp=datetime.now().isoformat(),
        )
