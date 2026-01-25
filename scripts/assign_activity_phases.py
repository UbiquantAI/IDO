#!/usr/bin/env python3
"""
Assign work phases to existing Pomodoro activities that don't have phases

This script finds all activities linked to Pomodoro sessions but missing
work_phase assignment, and automatically assigns the correct phase based
on the activity's start time and the session's phase timeline.
"""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from core.db import get_db
from core.logger import get_logger

logger = get_logger(__name__)


def calculate_phase_timeline(session: Dict[str, Any]) -> List[Dict[str, Any]]:
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
        timeline.append(
            {
                "phase_number": round_num,
                "start_time": current_time.isoformat(),
                "end_time": work_end.isoformat(),
            }
        )
        current_time = work_end

        # Add break duration to move to next work phase
        current_time = current_time + timedelta(minutes=break_duration)

    return timeline


def determine_work_phase(
    activity_start_time: str, phase_timeline: List[Dict[str, Any]]
) -> Optional[int]:
    """
    Determine which work phase an activity belongs to based on its start time

    Args:
        activity_start_time: ISO format timestamp of activity start
        phase_timeline: List of work phase dictionaries with start_time, end_time

    Returns:
        Work phase number (1-based) or None if no phases available
    """
    if not phase_timeline:
        return None

    try:
        activity_time = datetime.fromisoformat(activity_start_time)

        # First, check if activity falls within any work phase
        for phase in phase_timeline:
            phase_start = datetime.fromisoformat(phase["start_time"])
            phase_end = datetime.fromisoformat(phase["end_time"])

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

        if nearest_phase:
            logger.debug(
                f"Activity at {activity_start_time} doesn't fall in any work phase, "
                f"assigning to nearest phase: {nearest_phase}"
            )

        return nearest_phase

    except Exception as e:
        logger.error(f"Error determining work phase: {e}", exc_info=True)
        return None


async def assign_phases():
    """Main function to assign phases to activities"""
    db = get_db()

    # Find all activities with session but no work phase
    logger.info("Finding activities that need phase assignment...")

    with db.get_connection() as conn:
        cursor = conn.execute(
            """
            SELECT id, title, start_time, pomodoro_session_id
            FROM activities
            WHERE pomodoro_session_id IS NOT NULL
              AND pomodoro_work_phase IS NULL
              AND deleted = 0
            ORDER BY start_time
            """
        )
        activities = cursor.fetchall()

        if not activities:
            logger.info("✓ No activities need phase assignment")
            return

        logger.info(f"Found {len(activities)} activities needing phase assignment")

        updated_count = 0
        failed_count = 0

        for activity_row in activities:
            activity_id = activity_row[0]
            title = activity_row[1]
            start_time = activity_row[2]
            session_id = activity_row[3]

            try:
                # Get session
                session = await db.pomodoro_sessions.get_by_id(session_id)
                if not session:
                    logger.warning(
                        f"Session {session_id} not found for activity {activity_id}"
                    )
                    failed_count += 1
                    continue

                # Calculate phase timeline
                phase_timeline = calculate_phase_timeline(session)

                if not phase_timeline:
                    logger.warning(
                        f"No phases calculated for session {session_id} "
                        f"(completed_rounds: {session.get('completed_rounds', 0)})"
                    )
                    failed_count += 1
                    continue

                # Determine work phase
                work_phase = determine_work_phase(start_time, phase_timeline)

                if work_phase is None:
                    logger.warning(
                        f"Could not determine phase for activity {activity_id} "
                        f"(start_time: {start_time})"
                    )
                    failed_count += 1
                    continue

                # Update activity with work phase
                conn.execute(
                    """
                    UPDATE activities
                    SET pomodoro_work_phase = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (work_phase, activity_id),
                )

                logger.info(
                    f"✓ Assigned phase {work_phase} to activity: {title} "
                    f"(session: {session.get('user_intent', 'Unknown')[:30]}...)"
                )
                updated_count += 1

            except Exception as e:
                logger.error(
                    f"Failed to process activity {activity_id}: {e}", exc_info=True
                )
                failed_count += 1

        conn.commit()

        logger.info("=" * 60)
        logger.info(f"Phase assignment completed:")
        logger.info(f"  ✓ Updated: {updated_count}")
        logger.info(f"  ✗ Failed: {failed_count}")
        logger.info(f"  Total processed: {len(activities)}")
        logger.info("=" * 60)


def main():
    """Entry point"""
    logger.info("Starting activity phase assignment...")
    asyncio.run(assign_phases())
    logger.info("Done!")


if __name__ == "__main__":
    main()
