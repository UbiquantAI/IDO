"""
RawRecords Repository - Handles raw record persistence for Pomodoro sessions
Raw records are temporary storage for screenshots, keyboard, and mouse activity
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.logger import get_logger

from .base import BaseRepository

logger = get_logger(__name__)


class RawRecordsRepository(BaseRepository):
    """Repository for managing raw records in the database"""

    def __init__(self, db_path: Path):
        super().__init__(db_path)

    async def save(
        self,
        timestamp: str,
        record_type: str,
        data: str,
        pomodoro_session_id: Optional[str] = None,
    ) -> Optional[int]:
        """
        Save a raw record to database

        Args:
            timestamp: ISO format timestamp
            record_type: Type of record (SCREENSHOT_RECORD, KEYBOARD_RECORD, MOUSE_RECORD)
            data: JSON string of record data
            pomodoro_session_id: Optional Pomodoro session ID

        Returns:
            Record ID if successful, None otherwise
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO raw_records (
                        timestamp, type, data, pomodoro_session_id, created_at
                    ) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """,
                    (timestamp, record_type, data, pomodoro_session_id),
                )
                conn.commit()
                record_id = cursor.lastrowid
                logger.debug(
                    f"Saved raw record: {record_id}, "
                    f"type={record_type}, pomodoro_session={pomodoro_session_id}"
                )
                return record_id
        except Exception as e:
            logger.error(f"Failed to save raw record: {e}", exc_info=True)
            raise

    async def get_by_session(
        self,
        session_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Get raw records for a specific Pomodoro session

        Args:
            session_id: Pomodoro session ID
            limit: Maximum number of records to return
            offset: Number of records to skip

        Returns:
            List of raw record dictionaries
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    SELECT * FROM raw_records
                    WHERE pomodoro_session_id = ?
                    ORDER BY timestamp ASC
                    LIMIT ? OFFSET ?
                    """,
                    (session_id, limit, offset),
                )
                rows = cursor.fetchall()
                return self._rows_to_dicts(rows)
        except Exception as e:
            logger.error(
                f"Failed to get raw records for session {session_id}: {e}",
                exc_info=True,
            )
            raise

    async def count_by_session(self, session_id: str) -> int:
        """
        Count raw records for a session

        Args:
            session_id: Pomodoro session ID

        Returns:
            Number of raw records
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    SELECT COUNT(*) as count FROM raw_records
                    WHERE pomodoro_session_id = ?
                    """,
                    (session_id,),
                )
                row = cursor.fetchone()
                return row["count"] if row else 0
        except Exception as e:
            logger.error(
                f"Failed to count raw records for session {session_id}: {e}",
                exc_info=True,
            )
            raise

    async def delete_by_session(self, session_id: str) -> int:
        """
        Delete raw records for a session

        Args:
            session_id: Pomodoro session ID

        Returns:
            Number of records deleted
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    DELETE FROM raw_records
                    WHERE pomodoro_session_id = ?
                    """,
                    (session_id,),
                )
                conn.commit()
                deleted_count = cursor.rowcount
                logger.debug(
                    f"Deleted {deleted_count} raw records for session {session_id}"
                )
                return deleted_count
        except Exception as e:
            logger.error(
                f"Failed to delete raw records for session {session_id}: {e}",
                exc_info=True,
            )
            raise

    async def get_by_time_range(
        self,
        start_time: str,
        end_time: str,
        record_type: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get raw records within a time range

        Args:
            start_time: Start timestamp (ISO format)
            end_time: End timestamp (ISO format)
            record_type: Optional filter by record type
            session_id: Optional filter by Pomodoro session ID

        Returns:
            List of raw record dictionaries
        """
        try:
            with self._get_conn() as conn:
                # Build query based on filters
                if record_type and session_id:
                    cursor = conn.execute(
                        """
                        SELECT * FROM raw_records
                        WHERE timestamp >= ? AND timestamp <= ?
                        AND type = ? AND pomodoro_session_id = ?
                        ORDER BY timestamp ASC
                        """,
                        (start_time, end_time, record_type, session_id),
                    )
                elif record_type:
                    cursor = conn.execute(
                        """
                        SELECT * FROM raw_records
                        WHERE timestamp >= ? AND timestamp <= ? AND type = ?
                        ORDER BY timestamp ASC
                        """,
                        (start_time, end_time, record_type),
                    )
                elif session_id:
                    cursor = conn.execute(
                        """
                        SELECT * FROM raw_records
                        WHERE timestamp >= ? AND timestamp <= ?
                        AND pomodoro_session_id = ?
                        ORDER BY timestamp ASC
                        """,
                        (start_time, end_time, session_id),
                    )
                else:
                    cursor = conn.execute(
                        """
                        SELECT * FROM raw_records
                        WHERE timestamp >= ? AND timestamp <= ?
                        ORDER BY timestamp ASC
                        """,
                        (start_time, end_time),
                    )
                rows = cursor.fetchall()
                return self._rows_to_dicts(rows)
        except Exception as e:
            logger.error(
                f"Failed to get raw records by time range: {e}", exc_info=True
            )
            raise
