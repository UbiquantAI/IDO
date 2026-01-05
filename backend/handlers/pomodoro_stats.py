"""
Pomodoro Statistics Handler - API endpoints for Pomodoro session statistics

Endpoints:
- POST /pomodoro/stats - Get Pomodoro statistics for a specific date
- POST /pomodoro/session-detail - Get detailed session data with activities
- DELETE /pomodoro/sessions/delete - Delete a session and cascade delete activities
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from core.db import get_db
from core.events import emit_pomodoro_session_deleted
from core.logger import get_logger
from llm.focus_evaluator import get_focus_evaluator
from models.base import BaseModel
from models.responses import (
    DeletePomodoroSessionData,
    DeletePomodoroSessionRequest,
    DeletePomodoroSessionResponse,
    FocusMetrics,
    GetPomodoroSessionDetailRequest,
    GetPomodoroSessionDetailResponse,
    LLMFocusAnalysis,
    LLMFocusDimensionScores,
    LLMFocusEvaluation,
    PhaseTimelineItem,
    PomodoroActivityData,
    PomodoroSessionData,
    PomodoroSessionDetailData,
    TimedOperationResponse,
)

# CRITICAL: Use relative import to avoid circular imports
from . import api_handler

logger = get_logger(__name__)


# ============ Request Models ============


class GetPomodoroStatsRequest(BaseModel):
    """Request to get Pomodoro statistics for a specific date"""

    date: str  # YYYY-MM-DD format


class GetPomodoroPeriodStatsRequest(BaseModel):
    """Request to get Pomodoro statistics for a time period"""

    period: str  # "week", "month", or "year"
    reference_date: Optional[str] = None  # YYYY-MM-DD format (defaults to today)


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


class DailyFocusData(BaseModel):
    """Daily focus data for a specific day"""

    day: str  # Day label (e.g., "Mon", "周一")
    date: str  # YYYY-MM-DD format
    sessions: int
    minutes: int


class PomodoroPeriodStatsData(BaseModel):
    """Pomodoro statistics for a time period"""

    period: str  # "week", "month", or "year"
    start_date: str  # YYYY-MM-DD
    end_date: str  # YYYY-MM-DD
    weekly_total: int  # Total sessions in period
    focus_hours: float  # Total focus hours
    daily_average: float  # Average sessions per day
    completion_rate: int  # Percentage of goal completion
    daily_data: List[DailyFocusData]  # Daily breakdown


class GetPomodoroPeriodStatsResponse(TimedOperationResponse):
    """Response with Pomodoro period statistics"""

    data: Optional[PomodoroPeriodStatsData] = None


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

        # Optionally fetch associated TODO titles and activity counts for sessions
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

            # Use actual_duration_minutes as pure work duration
            # This reflects actual work time (completed rounds + partial current round if stopped early)
            session_data["pure_work_duration_minutes"] = session_data.get("actual_duration_minutes", 0)

            # Get activity count for this session
            session_id = session_data.get("id")
            if session_id:
                try:
                    activities = await db.activities.get_by_pomodoro_session(session_id)
                    session_data["activity_count"] = len(activities)
                except Exception as e:
                    logger.warning(
                        f"Failed to fetch activities for session {session_id}: {e}"
                    )
                    session_data["activity_count"] = 0
            else:
                session_data["activity_count"] = 0

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


@api_handler(
    body=GetPomodoroSessionDetailRequest,
    method="POST",
    path="/pomodoro/session-detail",
    tags=["pomodoro"],
)
async def get_pomodoro_session_detail(
    body: GetPomodoroSessionDetailRequest,
) -> GetPomodoroSessionDetailResponse:
    """
    Get detailed Pomodoro session with activities and focus metrics

    Returns:
    - Full session data
    - All activities generated during this session (ordered by work phase)
    - Calculated focus metrics (overall_focus_score, activity_count, topic_diversity, etc.)
    """
    try:
        db = get_db()

        # Get session
        session = await db.pomodoro_sessions.get_by_id(body.session_id)
        if not session:
            return GetPomodoroSessionDetailResponse(
                success=False,
                message=f"Session not found: {body.session_id}",
                timestamp=datetime.now().isoformat(),
            )

        # Get activities for this session
        activities = await db.activities.get_by_pomodoro_session(body.session_id)

        # Convert activities to Pydantic models
        activity_data_list = [
            PomodoroActivityData(
                id=activity["id"],
                title=activity["title"],
                description=activity["description"],
                start_time=activity["start_time"],
                end_time=activity["end_time"],
                session_duration_minutes=activity.get("session_duration_minutes") or 0,
                work_phase=activity.get("pomodoro_work_phase"),
                focus_score=activity.get("focus_score"),
                topic_tags=activity.get("topic_tags") or [],
                source_event_ids=activity.get("source_event_ids") or [],
                source_action_ids=activity.get("source_action_ids") or [],
                aggregation_mode=activity.get("aggregation_mode", "action_based"),
            )
            for activity in activities
        ]

        # Calculate focus metrics
        focus_metrics_dict = _calculate_session_focus_metrics(session, activities)
        focus_metrics = FocusMetrics(
            overall_focus_score=focus_metrics_dict["overall_focus_score"],
            activity_count=focus_metrics_dict["activity_count"],
            topic_diversity=focus_metrics_dict["topic_diversity"],
            average_activity_duration=focus_metrics_dict["average_activity_duration"],
            focus_level=focus_metrics_dict["focus_level"],
        )

        # Use actual_duration_minutes as pure work duration
        # This reflects actual work time (completed rounds + partial current round if stopped early)
        session_with_pure_duration = dict(session)
        session_with_pure_duration["pure_work_duration_minutes"] = session_with_pure_duration.get("actual_duration_minutes", 0)

        # Calculate phase timeline
        phase_timeline_raw = _calculate_phase_timeline(session)
        phase_timeline = [
            PhaseTimelineItem(
                phase_type=phase["phase_type"],
                phase_number=phase["phase_number"],
                start_time=phase["start_time"],
                end_time=phase["end_time"],
                duration_minutes=phase["duration_minutes"],
            )
            for phase in phase_timeline_raw
        ]

        logger.debug(
            f"Retrieved session detail for {body.session_id}: "
            f"{len(activities)} activities, "
            f"focus score: {focus_metrics.overall_focus_score:.2f}"
        )

        # LLM-based focus evaluation (cache-first with on-demand fallback)
        llm_evaluation = None
        try:
            # Step 1: Try to load from cache first
            cached_result = await db.pomodoro_sessions.get_llm_evaluation(body.session_id)

            if cached_result:
                # Cache hit - use cached result
                logger.debug(f"Using cached LLM evaluation for {body.session_id}")
                llm_evaluation = LLMFocusEvaluation(
                    focus_score=cached_result["focus_score"],
                    focus_level=cached_result["focus_level"],
                    dimension_scores=LLMFocusDimensionScores(**cached_result["dimension_scores"]),
                    analysis=LLMFocusAnalysis(**cached_result["analysis"]),
                    work_type=cached_result["work_type"],
                    is_focused_work=cached_result["is_focused_work"],
                    distraction_percentage=cached_result["distraction_percentage"],
                    deep_work_minutes=cached_result["deep_work_minutes"],
                    context_summary=cached_result["context_summary"],
                )
            else:
                # Step 2: Cache miss - compute on-demand (backward compatibility)
                logger.info(
                    f"Cache miss, computing on-demand LLM evaluation for {body.session_id}"
                )

                focus_evaluator = get_focus_evaluator()
                llm_result = await focus_evaluator.evaluate_focus(
                    activities=activities,
                    session_info=session,
                )

                # Convert to Pydantic model
                llm_evaluation = LLMFocusEvaluation(
                    focus_score=llm_result["focus_score"],
                    focus_level=llm_result["focus_level"],
                    dimension_scores=LLMFocusDimensionScores(**llm_result["dimension_scores"]),
                    analysis=LLMFocusAnalysis(**llm_result["analysis"]),
                    work_type=llm_result["work_type"],
                    is_focused_work=llm_result["is_focused_work"],
                    distraction_percentage=llm_result["distraction_percentage"],
                    deep_work_minutes=llm_result["deep_work_minutes"],
                    context_summary=llm_result["context_summary"],
                )

                # Step 3: Cache the result for future requests
                try:
                    await db.pomodoro_sessions.update_llm_evaluation(
                        body.session_id, llm_result
                    )
                    logger.info(f"Cached on-demand evaluation for {body.session_id}")
                except Exception as cache_error:
                    logger.warning(
                        f"Failed to cache on-demand evaluation: {cache_error}"
                    )
                    # Continue - caching failure doesn't affect response

                logger.info(
                    f"LLM focus evaluation completed for {body.session_id}: "
                    f"score={llm_evaluation.focus_score}, level={llm_evaluation.focus_level}"
                )

        except Exception as e:
            logger.warning(
                f"LLM focus evaluation failed for {body.session_id}: {e}. "
                f"Continuing with basic metrics only."
            )
            # Continue without LLM evaluation - it's optional

        return GetPomodoroSessionDetailResponse(
            success=True,
            message="Session details retrieved",
            data=PomodoroSessionDetailData(
                session=session_with_pure_duration,
                activities=activity_data_list,
                focus_metrics=focus_metrics,
                llm_focus_evaluation=llm_evaluation,
                phase_timeline=phase_timeline,
            ),
            timestamp=datetime.now().isoformat(),
        )

    except Exception as e:
        logger.error(
            f"Failed to get session detail for {body.session_id}: {e}",
            exc_info=True,
        )
        return GetPomodoroSessionDetailResponse(
            success=False,
            message=f"Failed to get session details: {str(e)}",
            timestamp=datetime.now().isoformat(),
        )


# ============ Helper Functions ============


def _calculate_session_focus_metrics(
    session: Dict[str, Any], activities: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Calculate session-level focus metrics

    Metrics:
    - overall_focus_score: Weighted average of activity focus scores (by duration)
    - activity_count: Number of activities in session
    - topic_diversity: Number of unique topics across all activities
    - average_activity_duration: Average duration per activity (minutes)
    - focus_level: Human-readable level (excellent/good/moderate/low)

    Args:
        session: Session dictionary
        activities: List of activity dictionaries

    Returns:
        Dictionary with calculated metrics
    """
    if not activities:
        return {
            "overall_focus_score": 0.0,
            "activity_count": 0,
            "topic_diversity": 0,
            "average_activity_duration": 0,
            "focus_level": "low",
        }

    # Calculate weighted average focus score (weighted by activity duration)
    total_duration = sum(
        activity.get("session_duration_minutes") or 0 for activity in activities
    )

    if total_duration > 0:
        weighted_score = sum(
            (activity.get("focus_score") or 0.5)
            * (activity.get("session_duration_minutes") or 0)
            for activity in activities
        ) / total_duration
    else:
        # If no duration info, use simple average
        weighted_score = sum(
            activity.get("focus_score") or 0.5 for activity in activities
        ) / len(activities)

    # Calculate topic diversity
    all_topics = set()
    for activity in activities:
        all_topics.update(activity.get("topic_tags") or [])

    # Calculate average activity duration
    average_duration = (
        total_duration / len(activities) if len(activities) > 0 else 0
    )

    # Map score to focus level
    focus_level = _get_focus_level(weighted_score)

    return {
        "overall_focus_score": round(weighted_score, 2),
        "activity_count": len(activities),
        "topic_diversity": len(all_topics),
        "average_activity_duration": round(average_duration, 1),
        "focus_level": focus_level,
    }


def _get_focus_level(score: float) -> str:
    """
    Map focus score to human-readable level

    Args:
        score: Focus score (0.0-1.0)

    Returns:
        Focus level: "excellent", "good", "moderate", or "low"
    """
    if score >= 0.8:
        return "excellent"
    elif score >= 0.6:
        return "good"
    elif score >= 0.4:
        return "moderate"
    else:
        return "low"


def _calculate_phase_timeline(session: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Reconstruct work/break phase timeline from session metadata

    Calculates the timeline of work and break phases based on the session's
    start time and duration configurations. Assumes phases completed on schedule.

    Args:
        session: Session dictionary with metadata

    Returns:
        List of phase dictionaries with start_time, end_time, phase_type, phase_number
    """
    from datetime import timedelta

    start_time = datetime.fromisoformat(session["start_time"])
    work_duration = session.get("work_duration_minutes", 25)
    break_duration = session.get("break_duration_minutes", 5)
    completed_rounds = session.get("completed_rounds", 0)
    total_rounds = session.get("total_rounds", 4)
    status = session.get("status", "active")

    timeline = []
    current_time = start_time

    for round_num in range(1, completed_rounds + 1):
        # Work phase
        work_end = current_time + timedelta(minutes=work_duration)
        timeline.append({
            "phase_type": "work",
            "phase_number": round_num,
            "start_time": current_time.isoformat(),
            "end_time": work_end.isoformat(),
            "duration_minutes": work_duration,
        })
        current_time = work_end

        # Break phase (skip after last round if session completed)
        if round_num < total_rounds or status != "completed":
            break_end = current_time + timedelta(minutes=break_duration)
            timeline.append({
                "phase_type": "break",
                "phase_number": round_num,
                "start_time": current_time.isoformat(),
                "end_time": break_end.isoformat(),
                "duration_minutes": break_duration,
            })
            current_time = break_end

    return timeline


@api_handler(
    body=GetPomodoroPeriodStatsRequest,
    method="POST",
    path="/pomodoro/period-stats",
    tags=["pomodoro"],
)
async def get_pomodoro_period_stats(
    body: GetPomodoroPeriodStatsRequest,
) -> GetPomodoroPeriodStatsResponse:
    """
    Get Pomodoro statistics for a time period (week/month/year)

    Returns:
    - Period summary statistics (total sessions, focus hours, daily average, completion rate)
    - Daily breakdown data for visualization
    """
    try:
        from datetime import timedelta

        db = get_db()

        # Get reference date (default to today)
        if body.reference_date:
            try:
                reference_date = datetime.fromisoformat(body.reference_date).date()
            except ValueError:
                return GetPomodoroPeriodStatsResponse(
                    success=False,
                    message="Invalid reference_date format. Expected YYYY-MM-DD",
                    timestamp=datetime.now().isoformat(),
                )
        else:
            reference_date = datetime.now().date()

        # Calculate period range
        if body.period == "week":
            # Last 7 days including today
            start_date = reference_date - timedelta(days=6)
            end_date = reference_date
            daily_count = 7
        elif body.period == "month":
            # Last 30 days
            start_date = reference_date - timedelta(days=29)
            end_date = reference_date
            daily_count = 30
        elif body.period == "year":
            # Last 365 days
            start_date = reference_date - timedelta(days=364)
            end_date = reference_date
            daily_count = 365
        else:
            return GetPomodoroPeriodStatsResponse(
                success=False,
                message=f"Invalid period: {body.period}. Must be 'week', 'month', or 'year'",
                timestamp=datetime.now().isoformat(),
            )

        # Fetch daily stats for the entire period
        daily_data = []
        total_sessions = 0
        total_minutes = 0

        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.isoformat()
            day_stats = await db.pomodoro_sessions.get_daily_stats(date_str)

            # Get day label (weekday name)
            day_label = current_date.strftime("%a")  # Mon, Tue, etc.

            daily_data.append(
                DailyFocusData(
                    day=day_label,
                    date=date_str,
                    sessions=day_stats["completed_count"],
                    minutes=day_stats["total_focus_minutes"],
                )
            )

            total_sessions += day_stats["completed_count"]
            total_minutes += day_stats["total_focus_minutes"]

            current_date += timedelta(days=1)

        # Calculate summary statistics
        focus_hours = round(total_minutes / 60, 1)
        daily_average = round(total_sessions / daily_count, 1)

        # Calculate completion rate (assume goal of 4 sessions per day)
        goal_sessions_per_day = 4
        total_goal = daily_count * goal_sessions_per_day
        completion_rate = min(100, int((total_sessions / total_goal) * 100)) if total_goal > 0 else 0

        logger.debug(
            f"Retrieved Pomodoro period stats for {body.period}: "
            f"{total_sessions} sessions, {focus_hours} hours"
        )

        return GetPomodoroPeriodStatsResponse(
            success=True,
            message=f"Retrieved statistics for {body.period}",
            data=PomodoroPeriodStatsData(
                period=body.period,
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                weekly_total=total_sessions,
                focus_hours=focus_hours,
                daily_average=daily_average,
                completion_rate=completion_rate,
                daily_data=daily_data,
            ),
            timestamp=datetime.now().isoformat(),
        )

    except Exception as e:
        logger.error(f"Failed to get Pomodoro period stats: {e}", exc_info=True)
        return GetPomodoroPeriodStatsResponse(
            success=False,
            message=f"Failed to get period statistics: {str(e)}",
            timestamp=datetime.now().isoformat(),
        )


@api_handler(
    body=DeletePomodoroSessionRequest,
    method="DELETE",
    path="/pomodoro/sessions/delete",
    tags=["pomodoro"],
)
async def delete_pomodoro_session(
    body: DeletePomodoroSessionRequest,
) -> DeletePomodoroSessionResponse:
    """
    Delete a Pomodoro session and cascade delete all linked activities

    This operation:
    1. Validates session exists and is not already deleted
    2. Soft deletes all activities linked to this session (cascade)
    3. Soft deletes the session itself
    4. Emits deletion event to notify frontend

    Args:
        body: Request containing session_id

    Returns:
        Response with deletion result and count of cascade-deleted activities
    """
    try:
        db = get_db()

        # Validate session exists and is not deleted
        session = await db.pomodoro_sessions.get_by_id(body.session_id)
        if not session:
            return DeletePomodoroSessionResponse(
                success=False,
                error="Session not found or already deleted",
                timestamp=datetime.now().isoformat(),
            )

        # CASCADE: Soft delete all activities linked to this session
        deleted_activities_count = await db.activities.delete_by_session_id(
            body.session_id
        )

        # Soft delete the session
        await db.pomodoro_sessions.soft_delete(body.session_id)

        # Emit deletion event to frontend
        emit_pomodoro_session_deleted(
            body.session_id, datetime.now().isoformat()
        )

        logger.info(
            f"Deleted Pomodoro session {body.session_id} "
            f"and cascade deleted {deleted_activities_count} activities"
        )

        return DeletePomodoroSessionResponse(
            success=True,
            message=f"Session deleted successfully. {deleted_activities_count} linked activities also removed.",
            data=DeletePomodoroSessionData(
                session_id=body.session_id,
                deleted_activities_count=deleted_activities_count,
            ),
            timestamp=datetime.now().isoformat(),
        )

    except Exception as e:
        logger.error(
            f"Failed to delete Pomodoro session {body.session_id}: {e}",
            exc_info=True,
        )
        return DeletePomodoroSessionResponse(
            success=False,
            error=f"Failed to delete session: {str(e)}",
            timestamp=datetime.now().isoformat(),
        )
