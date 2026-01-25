"""
Pomodoro Activity Linking Handler - API endpoints for linking unlinked activities

Provides endpoints to find and link unlinked activities to Pomodoro sessions
based on time overlap.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from core.db import get_db
from core.logger import get_logger
from models.base import BaseModel
from models.responses import TimedOperationResponse

# CRITICAL: Use relative import to avoid circular imports
from . import api_handler

logger = get_logger(__name__)


# ============ Request Models ============


class FindUnlinkedActivitiesRequest(BaseModel):
    """Request to find activities that could be linked to a session"""

    session_id: str


class LinkActivitiesRequest(BaseModel):
    """Request to link activities to a session"""

    session_id: str
    activity_ids: List[str]


# ============ Response Models ============


class UnlinkedActivityData(BaseModel):
    """Activity that could be linked to session"""

    id: str
    title: str
    start_time: str
    end_time: str
    session_duration_minutes: int


class FindUnlinkedActivitiesResponse(TimedOperationResponse):
    """Response with unlinked activities"""

    activities: List[UnlinkedActivityData] = []


class LinkActivitiesResponse(TimedOperationResponse):
    """Response after linking activities"""

    linked_count: int = 0


# ============ API Handlers ============


@api_handler(
    body=FindUnlinkedActivitiesRequest,
    method="POST",
    path="/pomodoro/find-unlinked-activities",
    tags=["pomodoro"],
)
async def find_unlinked_activities(
    body: FindUnlinkedActivitiesRequest,
) -> FindUnlinkedActivitiesResponse:
    """
    Find activities that overlap with session time but aren't linked

    Returns list of activities that could be retroactively linked
    """
    try:
        db = get_db()

        # Get session
        session = await db.pomodoro_sessions.get_by_id(body.session_id)
        if not session:
            return FindUnlinkedActivitiesResponse(
                success=False,
                message=f"Session not found: {body.session_id}",
                timestamp=datetime.now().isoformat(),
            )

        # Find overlapping activities
        overlapping = await db.activities.find_unlinked_overlapping_activities(
            session_start_time=session["start_time"],
            session_end_time=session.get("end_time", datetime.now().isoformat()),
        )

        # Convert to response format
        activity_data = [
            UnlinkedActivityData(
                id=a["id"],
                title=a["title"],
                start_time=a["start_time"],
                end_time=a["end_time"],
                session_duration_minutes=a.get("session_duration_minutes", 0),
            )
            for a in overlapping
        ]

        logger.debug(
            f"Found {len(activity_data)} unlinked activities for session {body.session_id}"
        )

        return FindUnlinkedActivitiesResponse(
            success=True,
            message=f"Found {len(activity_data)} unlinked activities",
            activities=activity_data,
            timestamp=datetime.now().isoformat(),
        )

    except Exception as e:
        logger.error(f"Failed to find unlinked activities: {e}", exc_info=True)
        return FindUnlinkedActivitiesResponse(
            success=False,
            message=str(e),
            timestamp=datetime.now().isoformat(),
        )


@api_handler(
    body=LinkActivitiesRequest,
    method="POST",
    path="/pomodoro/link-activities",
    tags=["pomodoro"],
)
async def link_activities_to_session(
    body: LinkActivitiesRequest,
) -> LinkActivitiesResponse:
    """
    Link selected activities to a Pomodoro session

    Updates activity records with pomodoro_session_id and auto-categorizes
    work_phase based on the activity's time period
    """
    try:
        db = get_db()

        # Verify session exists
        session = await db.pomodoro_sessions.get_by_id(body.session_id)
        if not session:
            return LinkActivitiesResponse(
                success=False,
                message=f"Session not found: {body.session_id}",
                timestamp=datetime.now().isoformat(),
            )

        # Calculate phase timeline to determine work phases
        phase_timeline = _calculate_phase_timeline_for_linking(session)

        # Link each activity with auto-categorized work phase
        linked_count = 0
        for activity_id in body.activity_ids:
            # Get activity to check its start time
            activity = await db.activities.get_by_id(activity_id)
            if not activity:
                logger.warning(f"Activity {activity_id} not found, skipping")
                continue

            # Determine work phase based on activity start time
            work_phase = _determine_work_phase(
                activity["start_time"], phase_timeline
            )

            # Link activity with auto-categorized work phase
            count = await db.activities.link_activities_to_session(
                activity_ids=[activity_id],
                session_id=body.session_id,
                work_phase=work_phase,
            )
            linked_count += count

            logger.debug(
                f"Linked activity {activity_id} to session {body.session_id}, "
                f"phase: {work_phase or 'unassigned'}"
            )

        logger.info(
            f"Linked {linked_count} activities to session {body.session_id} "
            f"with auto-categorized phases"
        )

        return LinkActivitiesResponse(
            success=True,
            message=f"Successfully linked {linked_count} activities with auto-categorized phases",
            linked_count=linked_count,
            timestamp=datetime.now().isoformat(),
        )

    except Exception as e:
        logger.error(f"Failed to link activities: {e}", exc_info=True)
        return LinkActivitiesResponse(
            success=False,
            message=str(e),
            timestamp=datetime.now().isoformat(),
        )


# ============ Helper Functions ============


def _calculate_phase_timeline_for_linking(session: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Calculate work phase timeline for a session

    Returns only work phases (not breaks) with their time ranges
    """
    start_time = datetime.fromisoformat(session["start_time"])
    work_duration = session.get("work_duration_minutes", 25)
    break_duration = session.get("break_duration_minutes", 5)
    completed_rounds = session.get("completed_rounds", 0)

    timeline = []
    current_time = start_time

    for round_num in range(1, completed_rounds + 1):
        # Work phase
        work_end = current_time + timedelta(minutes=work_duration)
        timeline.append({
            "phase_number": round_num,
            "start_time": current_time.isoformat(),
            "end_time": work_end.isoformat(),
        })
        current_time = work_end

        # Add break duration to move to next work phase
        current_time = current_time + timedelta(minutes=break_duration)

    return timeline


def _determine_work_phase(
    activity_start_time: str, phase_timeline: List[Dict[str, Any]]
) -> Optional[int]:
    """
    Determine which work phase an activity belongs to based on its start time

    Args:
        activity_start_time: ISO format timestamp of activity start
        phase_timeline: List of work phase dictionaries with start_time, end_time

    Returns:
        Work phase number (1-based) or None if activity doesn't fall in any work phase
    """
    try:
        activity_time = datetime.fromisoformat(activity_start_time)

        for phase in phase_timeline:
            phase_start = datetime.fromisoformat(phase["start_time"])
            phase_end = datetime.fromisoformat(phase["end_time"])

            # Check if activity starts within this work phase
            if phase_start <= activity_time <= phase_end:
                return phase["phase_number"]

        # Activity doesn't fall within any work phase
        # Assign to nearest work phase
        nearest_phase = None
        min_distance = None

        for phase in phase_timeline:
            phase_start = datetime.fromisoformat(phase["start_time"])
            phase_end = datetime.fromisoformat(phase["end_time"])

            # Calculate distance from activity to this phase
            if activity_time < phase_start:
                distance = (phase_start - activity_time).total_seconds()
            elif activity_time > phase_end:
                distance = (activity_time - phase_end).total_seconds()
            else:
                # This shouldn't happen as we already checked above
                return phase["phase_number"]

            if min_distance is None or distance < min_distance:
                min_distance = distance
                nearest_phase = phase["phase_number"]

        logger.debug(
            f"Activity at {activity_start_time} doesn't fall in any work phase, "
            f"assigning to nearest phase: {nearest_phase}"
        )

        return nearest_phase

    except Exception as e:
        logger.error(f"Error determining work phase: {e}", exc_info=True)
        return None
