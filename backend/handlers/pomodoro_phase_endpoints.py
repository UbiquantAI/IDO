"""
New Pomodoro API endpoints for phase-level retry mechanisms.

These endpoints should be added to backend/handlers/pomodoro.py
"""

from datetime import datetime
from typing import List, Optional
import asyncio

from models.base import BaseModel
from models.responses import (
    TimedOperationResponse,
    WorkPhaseInfo,
    GetSessionPhasesResponse,
)
from . import api_handler

# ==================== Request Models ====================


class RetryWorkPhaseRequest(BaseModel):
    session_id: str
    work_phase: int


class GetSessionPhasesRequest(BaseModel):
    session_id: str


class RetryLLMEvaluationRequest(BaseModel):
    session_id: str


# ==================== API Handlers ====================


@api_handler(
    body=RetryWorkPhaseRequest,
    method="POST",
    path="/pomodoro/retry-work-phase",
    tags=["pomodoro"],
)
async def retry_work_phase_aggregation(
    body: RetryWorkPhaseRequest,
) -> TimedOperationResponse:
    """
    FIXED: Retry work phase aggregation using stored timing.

    Now uses phase_start_time/phase_end_time from phase record
    instead of hardcoded calculations.
    """
    from core.coordinator import get_coordinator
    from core.db import get_db
    from core.logger import get_logger

    logger = get_logger(__name__)

    try:
        coordinator = get_coordinator()
        db = get_db()

        if not coordinator.pomodoro_manager:
            return TimedOperationResponse(
                success=False,
                error="Pomodoro manager not initialized",
                timestamp=datetime.now().isoformat(),
            )

        # ★ Get phase record (contains accurate timing) ★
        phase_record = await db.work_phases.get_by_session_and_phase(
            body.session_id, body.work_phase
        )

        if not phase_record:
            return TimedOperationResponse(
                success=False,
                error=f"Phase record not found for session {body.session_id}, phase {body.work_phase}",
                timestamp=datetime.now().isoformat(),
            )

        # ★ Extract timing from phase record (NOT calculated) ★
        phase_start_time = datetime.fromisoformat(phase_record["phase_start_time"])
        phase_end_time = datetime.fromisoformat(phase_record["phase_end_time"])

        logger.info(
            f"Manual retry: session={body.session_id}, phase={body.work_phase}, "
            f"time_range={phase_start_time.isoformat()} to {phase_end_time.isoformat()}"
        )

        # Reset status for retry (clear error, reset retry count)
        await db.work_phases.update_status(phase_record["id"], "pending", None, 0)

        # Trigger aggregation (non-blocking)
        asyncio.create_task(
            coordinator.pomodoro_manager._aggregate_work_phase_activities(
                session_id=body.session_id,
                work_phase=body.work_phase,
                phase_start_time=phase_start_time,
                phase_end_time=phase_end_time,
                phase_id=phase_record["id"],
            )
        )

        return TimedOperationResponse(
            success=True,
            message=f"Work phase {body.work_phase} retry triggered successfully",
            timestamp=datetime.now().isoformat(),
        )

    except Exception as e:
        logger.error(f"Failed to retry work phase: {e}", exc_info=True)
        return TimedOperationResponse(
            success=False, error=str(e), timestamp=datetime.now().isoformat()
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
    from core.db import get_db
    from core.logger import get_logger

    logger = get_logger(__name__)

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
    from core.coordinator import get_coordinator
    from core.logger import get_logger

    logger = get_logger(__name__)

    try:
        coordinator = get_coordinator()

        if not coordinator.pomodoro_manager:
            return TimedOperationResponse(
                success=False,
                error="Pomodoro manager not initialized",
                timestamp=datetime.now().isoformat(),
            )

        # Trigger LLM evaluation (non-blocking, manual retry)
        asyncio.create_task(
            coordinator.pomodoro_manager._compute_and_cache_llm_evaluation(
                body.session_id, is_first_attempt=False
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
