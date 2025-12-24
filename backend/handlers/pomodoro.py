"""
Pomodoro timer API handlers

Endpoints:
- POST /pomodoro/start - Start a Pomodoro session
- POST /pomodoro/end - End current Pomodoro session
- GET /pomodoro/status - Get current Pomodoro session status
"""

from datetime import datetime

from core.coordinator import get_coordinator
from core.logger import get_logger
from models.base import BaseModel
from models.responses import (
    EndPomodoroData,
    EndPomodoroResponse,
    GetPomodoroStatusResponse,
    PomodoroSessionData,
    StartPomodoroResponse,
)

from . import api_handler

logger = get_logger(__name__)


class StartPomodoroRequest(BaseModel):
    """Start Pomodoro request"""

    user_intent: str
    duration_minutes: int = 25


class EndPomodoroRequest(BaseModel):
    """End Pomodoro request"""

    status: str = "completed"  # completed, abandoned, interrupted


@api_handler(
    body=StartPomodoroRequest,
    method="POST",
    path="/pomodoro/start",
    tags=["pomodoro"],
)
async def start_pomodoro(body: StartPomodoroRequest) -> StartPomodoroResponse:
    """
    Start a new Pomodoro session

    Args:
        body: Request containing user_intent and duration_minutes

    Returns:
        StartPomodoroResponse with session data

    Raises:
        ValueError: If a Pomodoro session is already active or previous session is still processing
    """
    try:
        coordinator = get_coordinator()

        if not coordinator.pomodoro_manager:
            return StartPomodoroResponse(
                success=False,
                message="Pomodoro manager not initialized",
                error="Pomodoro manager not initialized",
                timestamp=datetime.now().isoformat(),
            )

        # Start Pomodoro session
        session_id = await coordinator.pomodoro_manager.start_pomodoro(
            user_intent=body.user_intent,
            duration_minutes=body.duration_minutes,
        )

        # Get session info
        session_info = await coordinator.pomodoro_manager.get_current_session_info()

        if not session_info:
            return StartPomodoroResponse(
                success=False,
                message="Failed to retrieve session info",
                error="Failed to retrieve session info after starting",
                timestamp=datetime.now().isoformat(),
            )

        logger.info(
            f"Pomodoro session started via API: {session_id}, intent='{body.user_intent}'"
        )

        return StartPomodoroResponse(
            success=True,
            message="Pomodoro session started successfully",
            data=PomodoroSessionData(
                session_id=session_info["session_id"],
                user_intent=session_info["user_intent"],
                start_time=session_info["start_time"],
                elapsed_minutes=session_info["elapsed_minutes"],
                planned_duration_minutes=session_info["planned_duration_minutes"],
            ),
            timestamp=datetime.now().isoformat(),
        )

    except ValueError as e:
        # Expected errors (session already active, previous processing)
        logger.warning(f"Failed to start Pomodoro session: {e}")
        return StartPomodoroResponse(
            success=False,
            message=str(e),
            error=str(e),
            timestamp=datetime.now().isoformat(),
        )
    except Exception as e:
        logger.error(f"Unexpected error starting Pomodoro session: {e}", exc_info=True)
        return StartPomodoroResponse(
            success=False,
            message="Failed to start Pomodoro session",
            error=str(e),
            timestamp=datetime.now().isoformat(),
        )


@api_handler(
    body=EndPomodoroRequest,
    method="POST",
    path="/pomodoro/end",
    tags=["pomodoro"],
)
async def end_pomodoro(body: EndPomodoroRequest) -> EndPomodoroResponse:
    """
    End current Pomodoro session

    Args:
        body: Request containing status (completed/abandoned/interrupted)

    Returns:
        EndPomodoroResponse with processing job info

    Raises:
        ValueError: If no active Pomodoro session
    """
    try:
        coordinator = get_coordinator()

        if not coordinator.pomodoro_manager:
            return EndPomodoroResponse(
                success=False,
                message="Pomodoro manager not initialized",
                error="Pomodoro manager not initialized",
                timestamp=datetime.now().isoformat(),
            )

        # End Pomodoro session
        result = await coordinator.pomodoro_manager.end_pomodoro(status=body.status)

        logger.info(
            f"Pomodoro session ended via API: {result['session_id']}, status={body.status}"
        )

        return EndPomodoroResponse(
            success=True,
            message="Pomodoro session ended successfully",
            data=EndPomodoroData(
                session_id=result["session_id"],
                processing_job_id=result.get("processing_job_id"),
                raw_records_count=result["raw_records_count"],
                message=result.get("message", ""),
            ),
            timestamp=datetime.now().isoformat(),
        )

    except ValueError as e:
        # Expected error (no active session)
        logger.warning(f"Failed to end Pomodoro session: {e}")
        return EndPomodoroResponse(
            success=False,
            message=str(e),
            error=str(e),
            timestamp=datetime.now().isoformat(),
        )
    except Exception as e:
        logger.error(f"Unexpected error ending Pomodoro session: {e}", exc_info=True)
        return EndPomodoroResponse(
            success=False,
            message="Failed to end Pomodoro session",
            error=str(e),
            timestamp=datetime.now().isoformat(),
        )


@api_handler(method="GET", path="/pomodoro/status", tags=["pomodoro"])
async def get_pomodoro_status() -> GetPomodoroStatusResponse:
    """
    Get current Pomodoro session status

    Returns:
        GetPomodoroStatusResponse with current session info or None if no active session
    """
    try:
        coordinator = get_coordinator()

        if not coordinator.pomodoro_manager:
            return GetPomodoroStatusResponse(
                success=False,
                message="Pomodoro manager not initialized",
                error="Pomodoro manager not initialized",
                timestamp=datetime.now().isoformat(),
            )

        # Get current session info
        session_info = await coordinator.pomodoro_manager.get_current_session_info()

        if not session_info:
            # No active session
            return GetPomodoroStatusResponse(
                success=True,
                message="No active Pomodoro session",
                data=None,
                timestamp=datetime.now().isoformat(),
            )

        return GetPomodoroStatusResponse(
            success=True,
            message="Active Pomodoro session found",
            data=PomodoroSessionData(
                session_id=session_info["session_id"],
                user_intent=session_info["user_intent"],
                start_time=session_info["start_time"],
                elapsed_minutes=session_info["elapsed_minutes"],
                planned_duration_minutes=session_info["planned_duration_minutes"],
            ),
            timestamp=datetime.now().isoformat(),
        )

    except Exception as e:
        logger.error(
            f"Unexpected error getting Pomodoro status: {e}", exc_info=True
        )
        return GetPomodoroStatusResponse(
            success=False,
            message="Failed to get Pomodoro status",
            error=str(e),
            timestamp=datetime.now().isoformat(),
        )
