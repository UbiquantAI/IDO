"""
PomodoroSessions Repository - Handles Pomodoro session lifecycle
Manages session metadata, status tracking, and processing state
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.logger import get_logger

from .base import BaseRepository

logger = get_logger(__name__)


class PomodoroSessionsRepository(BaseRepository):
    """Repository for managing Pomodoro sessions in the database"""

    def __init__(self, db_path: Path):
        super().__init__(db_path)

    async def create(
        self,
        session_id: str,
        user_intent: str,
        planned_duration_minutes: int,
        start_time: str,
        status: str = "active",
        associated_todo_id: Optional[str] = None,
        work_duration_minutes: int = 25,
        break_duration_minutes: int = 5,
        total_rounds: int = 4,
    ) -> None:
        """
        Create a new Pomodoro session

        Args:
            session_id: Unique session identifier
            user_intent: User's description of what they plan to work on
            planned_duration_minutes: Planned session duration (total for all rounds)
            start_time: ISO format start timestamp
            status: Session status (default: 'active')
            associated_todo_id: Optional TODO ID to associate with this session
            work_duration_minutes: Duration of each work phase (default: 25)
            break_duration_minutes: Duration of each break phase (default: 5)
            total_rounds: Total number of work rounds (default: 4)
        """
        try:
            with self._get_conn() as conn:
                conn.execute(
                    """
                    INSERT INTO pomodoro_sessions (
                        id, user_intent, planned_duration_minutes,
                        start_time, status, associated_todo_id,
                        work_duration_minutes, break_duration_minutes, total_rounds,
                        current_round, current_phase, phase_start_time, completed_rounds,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 'work', ?, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """,
                    (
                        session_id,
                        user_intent,
                        planned_duration_minutes,
                        start_time,
                        status,
                        associated_todo_id,
                        work_duration_minutes,
                        break_duration_minutes,
                        total_rounds,
                        start_time,  # phase_start_time = start_time initially
                    ),
                )
                conn.commit()
                logger.debug(f"Created Pomodoro session: {session_id}")
        except Exception as e:
            logger.error(f"Failed to create Pomodoro session {session_id}: {e}", exc_info=True)
            raise

    async def update(self, session_id: str, **kwargs) -> None:
        """
        Update Pomodoro session fields

        Args:
            session_id: Session ID to update
            **kwargs: Fields to update (e.g., end_time, status, processing_status)
        """
        try:
            if not kwargs:
                return

            set_clauses = []
            params = []

            for key, value in kwargs.items():
                set_clauses.append(f"{key} = ?")
                params.append(value)

            set_clauses.append("updated_at = CURRENT_TIMESTAMP")
            params.append(session_id)

            query = f"""
                UPDATE pomodoro_sessions
                SET {', '.join(set_clauses)}
                WHERE id = ?
            """

            with self._get_conn() as conn:
                conn.execute(query, params)
                conn.commit()
                logger.debug(f"Updated Pomodoro session {session_id}: {list(kwargs.keys())}")
        except Exception as e:
            logger.error(f"Failed to update Pomodoro session {session_id}: {e}", exc_info=True)
            raise

    async def get_by_id(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session by ID

        Args:
            session_id: Session ID

        Returns:
            Session dictionary or None if not found
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    SELECT * FROM pomodoro_sessions
                    WHERE id = ? AND deleted = 0
                    """,
                    (session_id,),
                )
                row = cursor.fetchone()
                return self._row_to_dict(row)
        except Exception as e:
            logger.error(f"Failed to get Pomodoro session {session_id}: {e}", exc_info=True)
            raise

    async def get_by_status(
        self,
        status: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Get sessions by status

        Args:
            status: Session status ('active', 'completed', 'abandoned', etc.)
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of session dictionaries
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    SELECT * FROM pomodoro_sessions
                    WHERE status = ? AND deleted = 0
                    ORDER BY start_time DESC
                    LIMIT ? OFFSET ?
                    """,
                    (status, limit, offset),
                )
                rows = cursor.fetchall()
                return self._rows_to_dicts(rows)
        except Exception as e:
            logger.error(f"Failed to get sessions by status {status}: {e}", exc_info=True)
            raise

    async def get_by_processing_status(
        self,
        processing_status: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Get sessions by processing status

        Args:
            processing_status: Processing status ('pending', 'processing', 'completed', 'failed')
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of session dictionaries
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    SELECT * FROM pomodoro_sessions
                    WHERE processing_status = ? AND deleted = 0
                    ORDER BY start_time DESC
                    LIMIT ? OFFSET ?
                    """,
                    (processing_status, limit, offset),
                )
                rows = cursor.fetchall()
                return self._rows_to_dicts(rows)
        except Exception as e:
            logger.error(
                f"Failed to get sessions by processing status {processing_status}: {e}",
                exc_info=True,
            )
            raise

    async def get_recent(
        self,
        limit: int = 10,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Get recent Pomodoro sessions

        Args:
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of session dictionaries
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    SELECT * FROM pomodoro_sessions
                    WHERE deleted = 0
                    ORDER BY start_time DESC
                    LIMIT ? OFFSET ?
                    """,
                    (limit, offset),
                )
                rows = cursor.fetchall()
                return self._rows_to_dicts(rows)
        except Exception as e:
            logger.error(f"Failed to get recent Pomodoro sessions: {e}", exc_info=True)
            raise

    async def get_stats(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get Pomodoro session statistics

        Args:
            start_date: Optional start date (ISO format)
            end_date: Optional end date (ISO format)

        Returns:
            Dictionary with statistics (total, completed, abandoned, avg_duration, etc.)
        """
        try:
            with self._get_conn() as conn:
                where_clauses = ["deleted = 0"]
                params = []

                if start_date:
                    where_clauses.append("start_time >= ?")
                    params.append(start_date)
                if end_date:
                    where_clauses.append("start_time <= ?")
                    params.append(end_date)

                where_sql = " AND ".join(where_clauses)

                cursor = conn.execute(
                    f"""
                    SELECT
                        COUNT(*) as total,
                        SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                        SUM(CASE WHEN status = 'abandoned' THEN 1 ELSE 0 END) as abandoned,
                        SUM(CASE WHEN status = 'interrupted' THEN 1 ELSE 0 END) as interrupted,
                        AVG(actual_duration_minutes) as avg_duration,
                        SUM(actual_duration_minutes) as total_duration
                    FROM pomodoro_sessions
                    WHERE {where_sql}
                    """,
                    params,
                )
                row = cursor.fetchone()
                return self._row_to_dict(row) if row else None
        except Exception as e:
            logger.error(f"Failed to get Pomodoro session stats: {e}", exc_info=True)
            raise

    async def soft_delete(self, session_id: str) -> None:
        """
        Soft delete a session

        Args:
            session_id: Session ID to delete
        """
        try:
            with self._get_conn() as conn:
                conn.execute(
                    """
                    UPDATE pomodoro_sessions
                    SET deleted = 1, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (session_id,),
                )
                conn.commit()
                logger.debug(f"Soft deleted Pomodoro session: {session_id}")
        except Exception as e:
            logger.error(f"Failed to soft delete Pomodoro session {session_id}: {e}", exc_info=True)
            raise

    async def hard_delete_old(self, days: int = 90) -> int:
        """
        Hard delete old completed sessions

        Args:
            days: Delete sessions older than this many days

        Returns:
            Number of sessions deleted
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    DELETE FROM pomodoro_sessions
                    WHERE deleted = 1
                    AND created_at < datetime('now', '-' || ? || ' days')
                    """,
                    (days,),
                )
                conn.commit()
                deleted_count = cursor.rowcount
                logger.debug(f"Hard deleted {deleted_count} old Pomodoro sessions")
                return deleted_count
        except Exception as e:
            logger.error(f"Failed to hard delete old sessions: {e}", exc_info=True)
            raise

    async def update_todo_association(
        self, session_id: str, todo_id: Optional[str]
    ) -> None:
        """
        Update the associated TODO for a Pomodoro session

        Args:
            session_id: Session ID
            todo_id: TODO ID to associate (None to clear association)
        """
        try:
            with self._get_conn() as conn:
                conn.execute(
                    """
                    UPDATE pomodoro_sessions
                    SET associated_todo_id = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (todo_id, session_id),
                )
                conn.commit()
                logger.debug(
                    f"Updated TODO association for session {session_id}: {todo_id}"
                )
        except Exception as e:
            logger.error(
                f"Failed to update TODO association for session {session_id}: {e}",
                exc_info=True,
            )
            raise

    async def get_sessions_by_todo(self, todo_id: str) -> List[Dict[str, Any]]:
        """
        Get all sessions associated with a TODO

        Args:
            todo_id: TODO ID

        Returns:
            List of session dictionaries
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    SELECT * FROM pomodoro_sessions
                    WHERE associated_todo_id = ? AND deleted = 0
                    ORDER BY start_time DESC
                    """,
                    (todo_id,),
                )
                rows = cursor.fetchall()
                return self._rows_to_dicts(rows)
        except Exception as e:
            logger.error(
                f"Failed to get sessions for TODO {todo_id}: {e}", exc_info=True
            )
            raise

    async def get_daily_stats(self, date: str) -> Dict[str, Any]:
        """
        Get Pomodoro statistics for a specific date

        Args:
            date: Date in YYYY-MM-DD format

        Returns:
            Dictionary with daily statistics:
            - completed_count: Number of completed sessions
            - total_focus_minutes: Total focus time in minutes
            - average_duration_minutes: Average session duration
            - sessions: List of sessions for that day
        """
        try:
            with self._get_conn() as conn:
                # Get aggregated stats
                cursor = conn.execute(
                    """
                    SELECT
                        COUNT(*) as completed_count,
                        COALESCE(SUM(actual_duration_minutes), 0) as total_focus_minutes,
                        COALESCE(AVG(actual_duration_minutes), 0) as average_duration_minutes
                    FROM pomodoro_sessions
                    WHERE DATE(start_time) = ?
                    AND status = 'completed'
                    AND deleted = 0
                    """,
                    (date,),
                )
                stats_row = cursor.fetchone()

                # Get session list for the day (only completed sessions)
                cursor = conn.execute(
                    """
                    SELECT * FROM pomodoro_sessions
                    WHERE DATE(start_time) = ?
                    AND status = 'completed'
                    AND deleted = 0
                    ORDER BY start_time DESC
                    """,
                    (date,),
                )
                sessions = self._rows_to_dicts(cursor.fetchall())

                return {
                    "completed_count": stats_row[0] if stats_row else 0,
                    "total_focus_minutes": int(stats_row[1]) if stats_row else 0,
                    "average_duration_minutes": int(stats_row[2]) if stats_row else 0,
                    "sessions": sessions,
                }
        except Exception as e:
            logger.error(f"Failed to get daily stats for {date}: {e}", exc_info=True)
            raise

    async def switch_phase(
        self, session_id: str, new_phase: str, phase_start_time: str
    ) -> Dict[str, Any]:
        """
        Switch to next phase in Pomodoro session

        Phase transitions:
        - work → break: Increment completed_rounds
        - break → work: Increment current_round
        - Automatically mark as completed if all rounds finished

        Args:
            session_id: Session ID
            new_phase: New phase ('work' or 'break')
            phase_start_time: ISO timestamp when new phase starts

        Returns:
            Updated session record
        """
        try:
            with self._get_conn() as conn:
                # Get current session state
                cursor = conn.execute(
                    """
                    SELECT current_phase, current_round, completed_rounds, total_rounds
                    FROM pomodoro_sessions
                    WHERE id = ?
                    """,
                    (session_id,),
                )
                row = cursor.fetchone()
                if not row:
                    raise ValueError(f"Session {session_id} not found")

                current_phase, current_round, completed_rounds, total_rounds = row

                # Calculate new state based on phase transition
                if current_phase == "work" and new_phase == "break":
                    # Completed a work phase
                    completed_rounds += 1
                    # current_round stays the same during break

                elif current_phase == "break" and new_phase == "work":
                    # Starting next work round
                    current_round += 1

                # Check if all rounds are completed
                new_status = "active"
                if completed_rounds >= total_rounds and new_phase == "break":
                    # After completing the last work round, mark as completed
                    new_status = "completed"
                    new_phase = "completed"

                # Update session
                conn.execute(
                    """
                    UPDATE pomodoro_sessions
                    SET current_phase = ?,
                        current_round = ?,
                        completed_rounds = ?,
                        phase_start_time = ?,
                        status = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (
                        new_phase,
                        current_round,
                        completed_rounds,
                        phase_start_time,
                        new_status,
                        session_id,
                    ),
                )
                conn.commit()

                logger.debug(
                    f"Switched session {session_id} to phase '{new_phase}', "
                    f"round {current_round}/{total_rounds}, "
                    f"completed {completed_rounds}"
                )

                # Return updated session
                return await self.get_by_id(session_id) or {}

        except Exception as e:
            logger.error(
                f"Failed to switch phase for session {session_id}: {e}",
                exc_info=True,
            )
            raise

    async def update_llm_evaluation(
        self,
        session_id: str,
        evaluation_result: Dict[str, Any]
    ) -> None:
        """
        Save LLM evaluation result to database

        Args:
            session_id: Session ID
            evaluation_result: Complete LLM evaluation dict (will be JSON-serialized)
        """
        try:
            from datetime import datetime

            with self._get_conn() as conn:
                conn.execute(
                    """
                    UPDATE pomodoro_sessions
                    SET llm_evaluation_result = ?,
                        llm_evaluation_computed_at = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (
                        json.dumps(evaluation_result),
                        datetime.now().isoformat(),
                        session_id,
                    ),
                )
                conn.commit()
                logger.debug(f"Saved LLM evaluation for session {session_id}")
        except Exception as e:
            logger.error(
                f"Failed to save LLM evaluation for session {session_id}: {e}",
                exc_info=True,
            )
            raise

    async def get_llm_evaluation(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached LLM evaluation result

        Args:
            session_id: Session ID

        Returns:
            LLM evaluation dict or None if not cached
        """
        try:
            session = await self.get_by_id(session_id)
            if not session or not session.get("llm_evaluation_result"):
                return None

            return json.loads(session["llm_evaluation_result"])
        except Exception as e:
            logger.warning(
                f"Failed to retrieve cached LLM evaluation for {session_id}: {e}"
            )
            return None
