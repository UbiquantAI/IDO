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
    ) -> None:
        """
        Create a new Pomodoro session

        Args:
            session_id: Unique session identifier
            user_intent: User's description of what they plan to work on
            planned_duration_minutes: Planned session duration
            start_time: ISO format start timestamp
            status: Session status (default: 'active')
        """
        try:
            with self._get_conn() as conn:
                conn.execute(
                    """
                    INSERT INTO pomodoro_sessions (
                        id, user_intent, planned_duration_minutes,
                        start_time, status, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """,
                    (session_id, user_intent, planned_duration_minutes, start_time, status),
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
