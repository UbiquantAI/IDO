"""
Repository for Pomodoro work phases.

This repository handles phase-level tracking for Pomodoro sessions,
enabling independent status management and retry mechanisms for each work phase.
"""

from pathlib import Path
from typing import Optional, List, Dict, Any
from uuid import uuid4

from core.logger import get_logger
from core.sqls.queries import (
    INSERT_WORK_PHASE,
    SELECT_WORK_PHASES_BY_SESSION,
    SELECT_WORK_PHASE_BY_SESSION_AND_NUMBER,
    UPDATE_WORK_PHASE_STATUS,
    UPDATE_WORK_PHASE_COMPLETED,
    INCREMENT_WORK_PHASE_RETRY,
)

from .base import BaseRepository

logger = get_logger(__name__)


class PomodoroWorkPhasesRepository(BaseRepository):
    """Repository for managing Pomodoro work phase records."""

    def __init__(self, db_path: Path):
        super().__init__(db_path)

    async def create(
        self,
        session_id: str,
        phase_number: int,
        phase_start_time: str,
        phase_end_time: Optional[str] = None,
        status: str = "pending",
        retry_count: int = 0,
    ) -> str:
        """
        Create a work phase record.

        Args:
            session_id: Pomodoro session ID
            phase_number: Phase number (1-4)
            phase_start_time: ISO format start time
            phase_end_time: ISO format end time (optional)
            status: Initial status (default: pending)
            retry_count: Initial retry count (default: 0)

        Returns:
            phase_id: Created phase record ID
        """
        phase_id = str(uuid4())

        try:
            with self._get_conn() as conn:
                conn.execute(
                    INSERT_WORK_PHASE,
                    (
                        phase_id,
                        session_id,
                        phase_number,
                        status,
                        phase_start_time,
                        phase_end_time,
                        retry_count,
                    ),
                )
                conn.commit()

            logger.info(
                f"Created work phase: id={phase_id}, session={session_id}, "
                f"phase={phase_number}, status={status}"
            )

            return phase_id
        except Exception as e:
            logger.error(f"Failed to create work phase: {e}", exc_info=True)
            raise

    async def get_by_session(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get all work phase records for a session.

        Args:
            session_id: Pomodoro session ID

        Returns:
            List of phase records (sorted by phase_number ASC)
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(SELECT_WORK_PHASES_BY_SESSION, (session_id,))
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get phases for session {session_id}: {e}", exc_info=True)
            return []

    async def get_by_session_and_phase(
        self, session_id: str, phase_number: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get a specific work phase record.

        Args:
            session_id: Pomodoro session ID
            phase_number: Phase number (1-4)

        Returns:
            Phase record dict or None if not found
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    SELECT_WORK_PHASE_BY_SESSION_AND_NUMBER, (session_id, phase_number)
                )
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(
                f"Failed to get phase for session {session_id}, phase {phase_number}: {e}",
                exc_info=True
            )
            return None

    async def update_status(
        self,
        phase_id: str,
        status: str,
        processing_error: Optional[str] = None,
        retry_count: Optional[int] = None,
    ) -> None:
        """
        Update phase status and error information.

        Args:
            phase_id: Phase record ID
            status: New status (pending/processing/completed/failed)
            processing_error: Error message (optional)
            retry_count: Retry count (optional)
        """
        try:
            with self._get_conn() as conn:
                conn.execute(
                    UPDATE_WORK_PHASE_STATUS,
                    (status, processing_error, retry_count, phase_id),
                )
                conn.commit()

            logger.debug(
                f"Updated phase status: id={phase_id}, status={status}, "
                f"error={processing_error}, retry_count={retry_count}"
            )
        except Exception as e:
            logger.error(f"Failed to update phase status: {e}", exc_info=True)
            raise

    async def mark_completed(self, phase_id: str, activity_count: int) -> None:
        """
        Mark phase as completed with activity count.

        Args:
            phase_id: Phase record ID
            activity_count: Number of activities created for this phase
        """
        try:
            with self._get_conn() as conn:
                conn.execute(UPDATE_WORK_PHASE_COMPLETED, (activity_count, phase_id))
                conn.commit()

            logger.info(
                f"Marked phase completed: id={phase_id}, activity_count={activity_count}"
            )
        except Exception as e:
            logger.error(f"Failed to mark phase completed: {e}", exc_info=True)
            raise

    async def increment_retry_count(self, phase_id: str) -> int:
        """
        Increment retry count and return new value.

        Args:
            phase_id: Phase record ID

        Returns:
            New retry count value
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(INCREMENT_WORK_PHASE_RETRY, (phase_id,))
                row = cursor.fetchone()
                conn.commit()

                new_count = row[0] if row else 0
                logger.debug(f"Incremented retry count for phase {phase_id}: {new_count}")
                return new_count
        except Exception as e:
            logger.error(f"Failed to increment retry count: {e}", exc_info=True)
            return 0
