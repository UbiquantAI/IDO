"""
ActivitiesV2 Repository - Handles all activity-related database operations
Activities are coarse-grained work sessions (NEW top layer)
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.logger import get_logger

from .base import BaseRepository

logger = get_logger(__name__)


class ActivitiesRepository(BaseRepository):
    """Repository for managing activities (work sessions) in the database"""

    def __init__(self, db_path: Path):
        super().__init__(db_path)

    async def save(
        self,
        activity_id: str,
        title: str,
        description: str,
        start_time: str,
        end_time: str,
        source_event_ids: Optional[List[str]] = None,
        source_action_ids: Optional[List[str]] = None,
        aggregation_mode: str = "action_based",
        session_duration_minutes: Optional[int] = None,
        topic_tags: Optional[List[str]] = None,
        user_merged_from_ids: Optional[List[str]] = None,
        user_split_into_ids: Optional[List[str]] = None,
        pomodoro_session_id: Optional[str] = None,
        pomodoro_work_phase: Optional[int] = None,
        focus_score: Optional[float] = None,
    ) -> None:
        """
        Save or update an activity (work session)

        Args:
            activity_id: Unique activity ID
            title: Activity title
            description: Activity description
            start_time: Activity start time (ISO format)
            end_time: Activity end time (ISO format)
            source_event_ids: List of event IDs (for event-based aggregation, deprecated)
            source_action_ids: List of action IDs (for action-based aggregation, preferred)
            aggregation_mode: 'event_based' or 'action_based' (default: 'action_based')
            session_duration_minutes: Session duration in minutes
            topic_tags: List of topic tags
            user_merged_from_ids: IDs of activities merged by user
            user_split_into_ids: IDs of activities split by user
            pomodoro_session_id: Associated Pomodoro session ID
            pomodoro_work_phase: Work phase number (1-4)
            focus_score: Focus metric (0.0-1.0)

        Raises:
            ValueError: If neither source_event_ids nor source_action_ids is provided
        """
        # Validation: at least one source type must be provided
        if not source_event_ids and not source_action_ids:
            raise ValueError("Either source_event_ids or source_action_ids must be provided")

        # Auto-detect aggregation mode if source_action_ids is provided
        if source_action_ids:
            aggregation_mode = "action_based"
        elif source_event_ids and not source_action_ids:
            aggregation_mode = "event_based"

        try:
            with self._get_conn() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO activities (
                        id, title, description, start_time, end_time,
                        source_event_ids, source_action_ids, aggregation_mode,
                        session_duration_minutes, topic_tags,
                        user_merged_from_ids, user_split_into_ids,
                        pomodoro_session_id, pomodoro_work_phase, focus_score,
                        created_at, updated_at, deleted
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 0)
                    """,
                    (
                        activity_id,
                        title,
                        description,
                        start_time,
                        end_time,
                        json.dumps(source_event_ids) if source_event_ids else None,
                        json.dumps(source_action_ids) if source_action_ids else None,
                        aggregation_mode,
                        session_duration_minutes,
                        json.dumps(topic_tags) if topic_tags else None,
                        json.dumps(user_merged_from_ids) if user_merged_from_ids else None,
                        json.dumps(user_split_into_ids) if user_split_into_ids else None,
                        pomodoro_session_id,
                        pomodoro_work_phase,
                        focus_score,
                    ),
                )
                conn.commit()
                logger.debug(f"Saved activity: {activity_id} (mode: {aggregation_mode})")
        except Exception as e:
            logger.error(f"Failed to save activity {activity_id}: {e}", exc_info=True)
            raise

    async def update(
        self,
        activity_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        source_event_ids: Optional[List[str]] = None,
        topic_tags: Optional[List[str]] = None,
    ) -> None:
        """Update an existing activity"""
        try:
            updates = []
            params = []

            if title is not None:
                updates.append("title = ?")
                params.append(title)
            if description is not None:
                updates.append("description = ?")
                params.append(description)
            if source_event_ids is not None:
                updates.append("source_event_ids = ?")
                params.append(json.dumps(source_event_ids))
            if topic_tags is not None:
                updates.append("topic_tags = ?")
                params.append(json.dumps(topic_tags))

            if not updates:
                return

            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(activity_id)

            with self._get_conn() as conn:
                conn.execute(
                    f"UPDATE activities SET {', '.join(updates)} WHERE id = ?",
                    params,
                )
                conn.commit()
                logger.debug(f"Updated activity: {activity_id}")

        except Exception as e:
            logger.error(f"Failed to update activity {activity_id}: {e}", exc_info=True)
            raise

    async def get_recent(
        self,
        limit: int = 50,
        offset: int = 0,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> List[Dict[str, Any]]:
        """Get recent activities with pagination and optional date filtering

        Args:
            limit: Maximum number of activities to return
            offset: Number of activities to skip
            start_date: Optional start date filter (YYYY-MM-DD format)
            end_date: Optional end date filter (YYYY-MM-DD format)
        """
        try:
            # Build WHERE clause
            where_clauses = ["deleted = 0"]
            params: list[str | int] = []

            if start_date:
                where_clauses.append("date(start_time) >= date(?)")
                params.append(start_date)

            if end_date:
                where_clauses.append("date(start_time) <= date(?)")
                params.append(end_date)

            where_clause = " AND ".join(where_clauses)

            # Add limit and offset
            params.extend([limit, offset])

            with self._get_conn() as conn:
                cursor = conn.execute(
                    f"""
                    SELECT id, title, description, start_time, end_time,
                           source_event_ids, source_action_ids, aggregation_mode,
                           session_duration_minutes, topic_tags,
                           user_merged_from_ids, user_split_into_ids,
                           pomodoro_session_id, pomodoro_work_phase, focus_score,
                           created_at, updated_at
                    FROM activities
                    WHERE {where_clause}
                    ORDER BY start_time DESC
                    LIMIT ? OFFSET ?
                    """,
                    tuple(params),
                )
                rows = cursor.fetchall()

            return [self._row_to_dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get recent activities: {e}", exc_info=True)
            return []

    async def get_by_id(self, activity_id: str) -> Optional[Dict[str, Any]]:
        """Get activity by ID"""
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    SELECT id, title, description, start_time, end_time,
                           source_event_ids, source_action_ids, aggregation_mode,
                           session_duration_minutes, topic_tags,
                           user_merged_from_ids, user_split_into_ids,
                           pomodoro_session_id, pomodoro_work_phase, focus_score,
                           created_at, updated_at
                    FROM activities
                    WHERE id = ? AND deleted = 0
                    """,
                    (activity_id,),
                )
                row = cursor.fetchone()

            if not row:
                return None

            return self._row_to_dict(row)

        except Exception as e:
            logger.error(f"Failed to get activity {activity_id}: {e}", exc_info=True)
            return None

    async def get_by_ids(self, activity_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Get multiple activities by their IDs

        Args:
            activity_ids: List of activity identifiers

        Returns:
            List of activity dictionaries
        """
        if not activity_ids:
            return []

        try:
            placeholders = ",".join("?" * len(activity_ids))
            with self._get_conn() as conn:
                cursor = conn.execute(
                    f"""
                    SELECT id, title, description, start_time, end_time,
                           source_event_ids, source_action_ids, aggregation_mode,
                           session_duration_minutes, topic_tags,
                           user_merged_from_ids, user_split_into_ids,
                           pomodoro_session_id, pomodoro_work_phase, focus_score,
                           created_at, updated_at
                    FROM activities
                    WHERE id IN ({placeholders}) AND deleted = 0
                    ORDER BY start_time DESC
                    """,
                    activity_ids,
                )
                rows = cursor.fetchall()

            activities = []
            for row in rows:
                activity = self._row_to_dict(row)
                if activity:
                    activities.append(activity)

            return activities

        except Exception as e:
            logger.error(
                f"Failed to get activities by IDs: {e}", exc_info=True
            )
            return []

    async def get_by_date(
        self, start_date: str, end_date: str
    ) -> List[Dict[str, Any]]:
        """Get activities within a date range"""
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    SELECT id, title, description, start_time, end_time,
                           source_event_ids, source_action_ids, aggregation_mode,
                           session_duration_minutes, topic_tags,
                           user_merged_from_ids, user_split_into_ids,
                           pomodoro_session_id, pomodoro_work_phase, focus_score,
                           created_at, updated_at
                    FROM activities
                    WHERE deleted = 0
                      AND DATE(start_time) >= ?
                      AND DATE(start_time) <= ?
                    ORDER BY start_time DESC
                    """,
                    (start_date, end_date),
                )
                rows = cursor.fetchall()

            return [self._row_to_dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get activities by date: {e}", exc_info=True)
            return []

    async def get_all_source_event_ids(self) -> List[str]:
        """Return all event ids referenced by non-deleted activities"""
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    SELECT source_event_ids
                    FROM activities
                    WHERE deleted = 0
                    """
                )
                rows = cursor.fetchall()

            aggregated_ids: List[str] = []
            for row in rows:
                if not row["source_event_ids"]:
                    continue
                try:
                    aggregated_ids.extend(json.loads(row["source_event_ids"]))
                except (TypeError, json.JSONDecodeError):
                    continue

            return aggregated_ids

        except Exception as e:
            logger.error(
                f"Failed to load aggregated activity event ids: {e}", exc_info=True
            )
            return []

    async def record_user_merge(
        self, activity_id: str, merged_from_ids: List[str]
    ) -> None:
        """Record user manual merge operation for learning"""
        try:
            with self._get_conn() as conn:
                conn.execute(
                    """
                    UPDATE activities
                    SET user_merged_from_ids = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (json.dumps(merged_from_ids), activity_id),
                )
                conn.commit()
                logger.debug(f"Recorded user merge for activity: {activity_id}")

        except Exception as e:
            logger.error(f"Failed to record user merge: {e}", exc_info=True)
            raise

    async def record_user_split(
        self, activity_id: str, split_into_ids: List[str]
    ) -> None:
        """Record user manual split operation for learning"""
        try:
            with self._get_conn() as conn:
                conn.execute(
                    """
                    UPDATE activities
                    SET user_split_into_ids = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (json.dumps(split_into_ids), activity_id),
                )
                conn.commit()
                logger.debug(f"Recorded user split for activity: {activity_id}")

        except Exception as e:
            logger.error(f"Failed to record user split: {e}", exc_info=True)
            raise

    async def delete(self, activity_id: str) -> None:
        """Soft delete an activity"""
        try:
            with self._get_conn() as conn:
                conn.execute(
                    "UPDATE activities SET deleted = 1 WHERE id = ?", (activity_id,)
                )
                conn.commit()
                logger.debug(f"Deleted activity: {activity_id}")
        except Exception as e:
            logger.error(
                f"Failed to delete activity {activity_id}: {e}", exc_info=True
            )
            raise

    async def mark_deleted(self, activity_id: str) -> None:
        """Alias for delete() - soft delete an activity"""
        await self.delete(activity_id)

    async def delete_by_date_range(self, start_iso: str, end_iso: str) -> int:
        """Soft delete activities inside the given timestamp window"""
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    UPDATE activities
                    SET deleted = 1
                    WHERE deleted = 0
                      AND start_time >= ?
                      AND start_time <= ?
                    """,
                    (start_iso, end_iso),
                )
                conn.commit()
                logger.debug(
                    f"Deleted {cursor.rowcount} activities between {start_iso} and {end_iso}"
                )
                return cursor.rowcount

        except Exception as e:
            logger.error(
                f"Failed to delete activities between {start_iso} and {end_iso}: {e}",
                exc_info=True,
            )
            raise

    async def get_count_by_date(self) -> Dict[str, int]:
        """Get activity count grouped by date"""
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    SELECT DATE(start_time) as date, COUNT(*) as count
                    FROM activities
                    WHERE deleted = 0
                    GROUP BY DATE(start_time)
                    ORDER BY date DESC
                    """
                )
                rows = cursor.fetchall()

            return {row["date"]: row["count"] for row in rows}

        except Exception as e:
            logger.error(
                f"Failed to get activity count by date: {e}", exc_info=True
            )
            return {}

    def _row_to_dict(self, row) -> Dict[str, Any]:
        """Convert database row to dictionary"""
        # Helper function to safely get column value
        def safe_get(row, key, default=None):
            try:
                return row[key]
            except (KeyError, IndexError):
                return default

        return {
            "id": row["id"],
            "title": row["title"],
            "description": row["description"],
            "start_time": row["start_time"],
            "end_time": row["end_time"],
            "source_event_ids": json.loads(row["source_event_ids"])
            if row["source_event_ids"]
            else [],
            "source_action_ids": json.loads(safe_get(row, "source_action_ids"))
            if safe_get(row, "source_action_ids")
            else [],
            "aggregation_mode": safe_get(row, "aggregation_mode", "action_based"),
            "session_duration_minutes": row["session_duration_minutes"],
            "topic_tags": json.loads(row["topic_tags"]) if row["topic_tags"] else [],
            "user_merged_from_ids": json.loads(row["user_merged_from_ids"])
            if row["user_merged_from_ids"]
            else None,
            "user_split_into_ids": json.loads(row["user_split_into_ids"])
            if row["user_split_into_ids"]
            else None,
            "pomodoro_session_id": safe_get(row, "pomodoro_session_id"),
            "pomodoro_work_phase": safe_get(row, "pomodoro_work_phase"),
            "focus_score": safe_get(row, "focus_score"),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    async def get_by_pomodoro_session(
        self, session_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get all activities associated with a Pomodoro session

        Args:
            session_id: Pomodoro session ID

        Returns:
            List of activity dictionaries, ordered by work phase and start time
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    SELECT id, title, description, start_time, end_time,
                           source_event_ids, source_action_ids, aggregation_mode,
                           session_duration_minutes, topic_tags,
                           pomodoro_session_id, pomodoro_work_phase, focus_score,
                           user_merged_from_ids, user_split_into_ids,
                           created_at, updated_at
                    FROM activities
                    WHERE pomodoro_session_id = ? AND deleted = 0
                    ORDER BY pomodoro_work_phase ASC, start_time ASC
                    """,
                    (session_id,),
                )
                rows = cursor.fetchall()

            activities = [self._row_to_dict(row) for row in rows]

            logger.debug(
                f"Retrieved {len(activities)} activities for Pomodoro session {session_id}"
            )

            return activities

        except Exception as e:
            logger.error(
                f"Failed to get activities for Pomodoro session {session_id}: {e}",
                exc_info=True,
            )
            return []

    async def find_unlinked_overlapping_activities(
        self,
        session_start_time: str,
        session_end_time: str,
    ) -> List[Dict[str, Any]]:
        """
        Find activities that overlap with session time and have no pomodoro_session_id

        Overlap logic: activity overlaps if activity.start_time < session.end_time
                       AND activity.end_time > session.start_time

        Args:
            session_start_time: Session start (ISO format)
            session_end_time: Session end (ISO format)

        Returns:
            List of unlinked activity dictionaries
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    SELECT id, title, description, start_time, end_time,
                           source_event_ids, source_action_ids, aggregation_mode,
                           session_duration_minutes, topic_tags,
                           pomodoro_session_id, pomodoro_work_phase, focus_score,
                           user_merged_from_ids, user_split_into_ids,
                           created_at, updated_at
                    FROM activities
                    WHERE deleted = 0
                      AND pomodoro_session_id IS NULL
                      AND start_time < ?
                      AND end_time > ?
                    ORDER BY start_time ASC
                    """,
                    (session_end_time, session_start_time),
                )
                rows = cursor.fetchall()

            activities = [self._row_to_dict(row) for row in rows]

            logger.debug(
                f"Found {len(activities)} unlinked activities overlapping "
                f"{session_start_time} - {session_end_time}"
            )

            return activities

        except Exception as e:
            logger.error(
                f"Failed to find overlapping activities: {e}",
                exc_info=True,
            )
            return []

    async def link_activities_to_session(
        self,
        activity_ids: List[str],
        session_id: str,
        work_phase: Optional[int] = None,
    ) -> int:
        """
        Link multiple activities to a Pomodoro session

        Args:
            activity_ids: List of activity IDs to link
            session_id: Pomodoro session ID
            work_phase: Optional work phase number (if known)

        Returns:
            Number of activities linked
        """
        try:
            if not activity_ids:
                return 0

            placeholders = ",".join("?" * len(activity_ids))
            params = [session_id, work_phase] + activity_ids

            with self._get_conn() as conn:
                cursor = conn.execute(
                    f"""
                    UPDATE activities
                    SET pomodoro_session_id = ?,
                        pomodoro_work_phase = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id IN ({placeholders})
                      AND deleted = 0
                      AND pomodoro_session_id IS NULL
                    """,
                    params,
                )
                conn.commit()
                linked_count = cursor.rowcount

            logger.info(
                f"Linked {linked_count} activities to session {session_id}"
            )

            return linked_count

        except Exception as e:
            logger.error(
                f"Failed to link activities to session: {e}",
                exc_info=True,
            )
            raise

    async def delete_by_session_id(self, session_id: str) -> int:
        """
        Soft delete all activities linked to a Pomodoro session
        Used for cascade deletion when a session is deleted

        Args:
            session_id: Pomodoro session ID

        Returns:
            Number of activities deleted
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    UPDATE activities
                    SET deleted = 1, updated_at = CURRENT_TIMESTAMP
                    WHERE pomodoro_session_id = ? AND deleted = 0
                    """,
                    (session_id,),
                )
                conn.commit()
                deleted_count = cursor.rowcount

            logger.info(
                f"Cascade deleted {deleted_count} activities for session {session_id}"
            )
            return deleted_count

        except Exception as e:
            logger.error(
                f"Failed to cascade delete activities for session {session_id}: {e}",
                exc_info=True,
            )
            raise

    async def update_focus_score(self, activity_id: str, focus_score: float) -> None:
        """
        Update focus score for a specific activity

        Args:
            activity_id: Activity ID
            focus_score: Focus score (0.0-100.0)
        """
        try:
            # Ensure focus_score is within valid range
            focus_score = max(0.0, min(100.0, focus_score))

            with self._get_conn() as conn:
                conn.execute(
                    """
                    UPDATE activities
                    SET focus_score = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (focus_score, activity_id),
                )
                conn.commit()

            logger.debug(f"Updated focus_score for activity {activity_id}: {focus_score}")

        except Exception as e:
            logger.error(
                f"Failed to update focus_score for activity {activity_id}: {e}",
                exc_info=True,
            )
            raise

    async def batch_update_focus_scores(
        self, activity_scores: List[Dict[str, Any]]
    ) -> int:
        """
        Batch update focus scores for multiple activities

        Args:
            activity_scores: List of dicts with 'activity_id' and 'focus_score' keys

        Returns:
            Number of activities updated
        """
        if not activity_scores:
            return 0

        try:
            with self._get_conn() as conn:
                updated_count = 0
                for item in activity_scores:
                    activity_id = item.get("activity_id")
                    focus_score = item.get("focus_score", 0.0)

                    if not activity_id:
                        continue

                    # Ensure focus_score is within valid range
                    focus_score = max(0.0, min(100.0, focus_score))

                    cursor = conn.execute(
                        """
                        UPDATE activities
                        SET focus_score = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                        """,
                        (focus_score, activity_id),
                    )
                    updated_count += cursor.rowcount

                conn.commit()

            logger.info(f"Batch updated focus_scores for {updated_count} activities")
            return updated_count

        except Exception as e:
            logger.error(f"Failed to batch update focus_scores: {e}", exc_info=True)
            raise
