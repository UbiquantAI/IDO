"""
Pomodoro timer API handlers

Endpoints:
- POST /pomodoro/start - Start a Pomodoro session
- POST /pomodoro/end - End current Pomodoro session
- GET /pomodoro/status - Get current Pomodoro session status
- POST /pomodoro/retry-work-phase - Manually retry work phase activity aggregation
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional

from core.coordinator import get_coordinator
from core.db import get_db
from core.logger import get_logger
from models.base import BaseModel
from models.responses import (
    EndPomodoroData,
    EndPomodoroResponse,
    GetPomodoroStatusResponse,
    PomodoroSessionData,
    StartPomodoroResponse,
    TimedOperationResponse,
    WorkPhaseInfo,
    GetSessionPhasesResponse,
)

from . import api_handler

logger = get_logger(__name__)


class StartPomodoroRequest(BaseModel):
    """Start Pomodoro request with rounds configuration"""

    user_intent: str
    duration_minutes: int = 25  # Legacy field, calculated from rounds
    associated_todo_id: Optional[str] = None  # Optional TODO association
    work_duration_minutes: int = 25  # Duration of work phase
    break_duration_minutes: int = 5  # Duration of break phase
    total_rounds: int = 4  # Number of work rounds


class EndPomodoroRequest(BaseModel):
    """End Pomodoro request"""

    status: str = "completed"  # completed, abandoned, interrupted


class RetryWorkPhaseRequest(BaseModel):
    """Retry work phase activity aggregation request"""

    session_id: str
    work_phase: int


class GetSessionPhasesRequest(BaseModel):
    """Get session phases request"""

    session_id: str


class RetryLLMEvaluationRequest(BaseModel):
    """Retry LLM evaluation request"""

    session_id: str


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
            associated_todo_id=body.associated_todo_id,
            work_duration_minutes=body.work_duration_minutes,
            break_duration_minutes=body.break_duration_minutes,
            total_rounds=body.total_rounds,
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
                associated_todo_id=session_info.get("associated_todo_id"),
                associated_todo_title=session_info.get("associated_todo_title"),
                work_duration_minutes=session_info.get("work_duration_minutes", 25),
                break_duration_minutes=session_info.get("break_duration_minutes", 5),
                total_rounds=session_info.get("total_rounds", 4),
                current_round=session_info.get("current_round", 1),
                current_phase=session_info.get("current_phase", "work"),
                phase_start_time=session_info.get("phase_start_time"),
                completed_rounds=session_info.get("completed_rounds", 0),
                remaining_phase_seconds=session_info.get("remaining_phase_seconds"),
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
                status=result["status"],  # ✅ Use new field
                actual_work_minutes=result["actual_work_minutes"],  # ✅ Use new field
                raw_records_count=result.get("raw_records_count", 0),  # ✅ Safe access
                processing_job_id=None,  # ✅ Deprecated, always None now
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
                # Add all missing fields for complete session state
                associated_todo_id=session_info.get("associated_todo_id"),
                associated_todo_title=session_info.get("associated_todo_title"),
                work_duration_minutes=session_info.get("work_duration_minutes", 25),
                break_duration_minutes=session_info.get("break_duration_minutes", 5),
                total_rounds=session_info.get("total_rounds", 4),
                current_round=session_info.get("current_round", 1),
                current_phase=session_info.get("current_phase", "work"),
                phase_start_time=session_info.get("phase_start_time"),
                completed_rounds=session_info.get("completed_rounds", 0),
                remaining_phase_seconds=session_info.get("remaining_phase_seconds"),
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


@api_handler(
    body=RetryWorkPhaseRequest,
    method="POST",
    path="/pomodoro/retry-work-phase",
    tags=["pomodoro"],
)
async def retry_work_phase_aggregation(
    body: RetryWorkPhaseRequest,
) -> EndPomodoroResponse:
    """
    Manually trigger work phase activity aggregation (for retry)

    This endpoint allows users to manually retry activity aggregation for a specific
    work phase if the automatic aggregation failed or was incomplete.

    Args:
        body: Request containing session_id and work_phase number

    Returns:
        EndPomodoroResponse with success status and processing details
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

        # Get session from database
        db = get_db()
        session = await db.pomodoro_sessions.get_by_id(body.session_id)
        if not session:
            return EndPomodoroResponse(
                success=False,
                message=f"Session {body.session_id} not found",
                error=f"Session {body.session_id} not found",
                timestamp=datetime.now().isoformat(),
            )

        # Validate work_phase number
        total_rounds = session.get("total_rounds", 4)
        if body.work_phase < 1 or body.work_phase > total_rounds:
            return EndPomodoroResponse(
                success=False,
                message=f"Invalid work phase {body.work_phase}. Must be between 1 and {total_rounds}",
                error="Invalid work phase number",
                timestamp=datetime.now().isoformat(),
            )

        # Calculate phase time range based on work_phase
        # Note: This is a simplified calculation. For precise timing,
        # we would need to store each phase's start/end time in database.
        session_start = datetime.fromisoformat(session["start_time"])
        work_duration = session.get("work_duration_minutes", 25)
        break_duration = session.get("break_duration_minutes", 5)

        # Calculate phase start time
        # Each complete round = work + break
        # For work_phase N: start = session_start + (N-1) * (work + break)
        phase_start_offset = (body.work_phase - 1) * (work_duration + break_duration)
        phase_start_time = session_start + timedelta(minutes=phase_start_offset)

        # Phase end time = start + work_duration
        phase_end_time = phase_start_time + timedelta(minutes=work_duration)

        # Use session end time if this was the last work phase
        if session.get("end_time"):
            session_end = datetime.fromisoformat(session["end_time"])
            if phase_end_time > session_end:
                phase_end_time = session_end

        logger.info(
            f"Manually triggering work phase aggregation: "
            f"session={body.session_id}, phase={body.work_phase}, "
            f"time_range={phase_start_time.isoformat()} to {phase_end_time.isoformat()}"
        )

        # Trigger aggregation in background (non-blocking)
        asyncio.create_task(
            coordinator.pomodoro_manager._aggregate_work_phase_activities(
                session_id=body.session_id,
                work_phase=body.work_phase,
                phase_start_time=phase_start_time,
                phase_end_time=phase_end_time,
            )
        )

        return EndPomodoroResponse(
            success=True,
            message=f"Work phase {body.work_phase} aggregation triggered successfully",
            data=EndPomodoroData(
                session_id=body.session_id,
                status="processing",  # Work phase being retried
                actual_work_minutes=0,  # Not applicable for retry
                processing_job_id=None,  # Background task, no job ID
                raw_records_count=0,
                message=f"Aggregation triggered for work phase {body.work_phase}",
            ),
            timestamp=datetime.now().isoformat(),
        )

    except Exception as e:
        logger.error(
            f"Failed to retry work phase aggregation: {e}", exc_info=True
        )
        return EndPomodoroResponse(
            success=False,
            message="Failed to retry work phase aggregation",
            error=str(e),
            timestamp=datetime.now().isoformat(),
        )


@api_handler(
    body=GetSessionPhasesRequest,
    method="POST",
    path="/pomodoro/get-session-phases",
    tags=["pomodoro"],
)
async def get_session_phases(
    body: GetSessionPhasesRequest,
) -> GetSessionPhasesResponse:
    """
    Get all work phase records for a session.
    Used by frontend to display phase status and retry buttons.
    """
    try:
        db = get_db()
        phases = await db.work_phases.get_by_session(body.session_id)

        phase_infos = [
            WorkPhaseInfo(
                phase_id=p["id"],
                phase_number=p["phase_number"],
                status=p["status"],
                processing_error=p.get("processing_error"),
                retry_count=p.get("retry_count", 0),
                phase_start_time=p["phase_start_time"],
                phase_end_time=p.get("phase_end_time"),
                activity_count=p.get("activity_count", 0),
            )
            for p in phases
        ]

        return GetSessionPhasesResponse(
            success=True, data=phase_infos, timestamp=datetime.now().isoformat()
        )

    except Exception as e:
        logger.error(f"Failed to get session phases: {e}", exc_info=True)
        return GetSessionPhasesResponse(
            success=False, error=str(e), timestamp=datetime.now().isoformat()
        )


@api_handler(
    body=RetryLLMEvaluationRequest,
    method="POST",
    path="/pomodoro/retry-llm-evaluation",
    tags=["pomodoro"],
)
async def retry_llm_evaluation(
    body: RetryLLMEvaluationRequest,
) -> TimedOperationResponse:
    """
    Manually retry LLM focus evaluation for a session.
    Independent from phase aggregation retry.
    """
    try:
        coordinator = get_coordinator()

        if not coordinator.pomodoro_manager:
            return TimedOperationResponse(
                success=False,
                error="Pomodoro manager not initialized",
                timestamp=datetime.now().isoformat(),
            )

        # Trigger LLM evaluation (non-blocking)
        asyncio.create_task(
            coordinator.pomodoro_manager._compute_and_cache_llm_evaluation(
                body.session_id
            )
        )

        return TimedOperationResponse(
            success=True,
            message="LLM evaluation retry triggered successfully",
            timestamp=datetime.now().isoformat(),
        )

    except Exception as e:
        logger.error(f"Failed to retry LLM evaluation: {e}", exc_info=True)
        return TimedOperationResponse(
            success=False, error=str(e), timestamp=datetime.now().isoformat()
        )
