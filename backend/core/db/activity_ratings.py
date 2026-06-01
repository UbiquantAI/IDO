"""
ActivityRatings Repository - Handles multi-dimensional activity ratings
Manages user ratings for activities across different dimensions (focus, productivity, etc.)
"""

import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.logger import get_logger

from .base import BaseRepository

logger = get_logger(__name__)


class ActivityRatingsRepository(BaseRepository):
    """Repository for managing activity ratings in the database"""

    def __init__(self, db_path: Path):
        super().__init__(db_path)

    async def save_rating(
        self,
        activity_id: str,
        dimension: str,
        rating: int,
        note: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Save or update a rating for an activity dimension

        Args:
            activity_id: Activity ID
            dimension: Rating dimension (e.g., 'focus_level', 'productivity')
            rating: Rating value (1-5)
            note: Optional note/comment

        Returns:
            The saved rating record

        Raises:
            ValueError: If rating is out of range (1-5)
        """
        if not 1 <= rating <= 5:
            raise ValueError(f"Rating must be between 1 and 5, got {rating}")

        try:
            rating_id = str(uuid.uuid4())

            with self._get_conn() as conn:
                # Use INSERT OR REPLACE to handle updates
                # SQLite will replace if (activity_id, dimension) already exists
                conn.execute(
                    """
                    INSERT INTO activity_ratings (
                        id, activity_id, dimension, rating, note,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    ON CONFLICT(activity_id, dimension)
                    DO UPDATE SET
                        rating = excluded.rating,
                        note = excluded.note,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (rating_id, activity_id, dimension, rating, note),
                )
                conn.commit()

                # Fetch the saved rating
                cursor = conn.execute(
                    """
                    SELECT id, activity_id, dimension, rating, note,
                           created_at, updated_at
                    FROM activity_ratings
                    WHERE activity_id = ? AND dimension = ?
                    """,
                    (activity_id, dimension),
                )
                row = cursor.fetchone()

                logger.debug(
                    f"Saved rating for activity {activity_id}, "
                    f"dimension {dimension}: {rating}"
                )

                if not row:
                    raise ValueError(f"Failed to retrieve saved rating")

                result = self._row_to_dict(row)
                if not result:
                    raise ValueError(f"Failed to convert rating to dict")

                return result

        except Exception as e:
            logger.error(
                f"Failed to save rating for activity {activity_id}: {e}",
                exc_info=True,
            )
            raise

    async def get_ratings_by_activity(
        self, activity_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get all ratings for an activity

        Args:
            activity_id: Activity ID

        Returns:
            List of rating records
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    SELECT id, activity_id, dimension, rating, note,
                           created_at, updated_at
                    FROM activity_ratings
                    WHERE activity_id = ?
                    ORDER BY dimension
                    """,
                    (activity_id,),
                )
                rows = cursor.fetchall()
                return [self._row_to_dict(row) for row in rows]

        except Exception as e:
            logger.error(
                f"Failed to get ratings for activity {activity_id}: {e}",
                exc_info=True,
            )
            raise

    async def delete_rating(self, activity_id: str, dimension: str) -> None:
        """
        Delete a specific rating

        Args:
            activity_id: Activity ID
            dimension: Rating dimension
        """
        try:
            with self._get_conn() as conn:
                conn.execute(
                    """
                    DELETE FROM activity_ratings
                    WHERE activity_id = ? AND dimension = ?
                    """,
                    (activity_id, dimension),
                )
                conn.commit()
                logger.debug(
                    f"Deleted rating for activity {activity_id}, dimension {dimension}"
                )

        except Exception as e:
            logger.error(
                f"Failed to delete rating for activity {activity_id}: {e}",
                exc_info=True,
            )
            raise

    async def get_average_ratings_by_dimension(
        self, start_date: str, end_date: str
    ) -> Dict[str, float]:
        """
        Get average ratings by dimension for a date range

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            Dict mapping dimension to average rating
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    SELECT ar.dimension, AVG(ar.rating) as avg_rating
                    FROM activity_ratings ar
                    JOIN activities a ON ar.activity_id = a.id
                    WHERE DATE(a.start_time) >= ? AND DATE(a.start_time) <= ?
                    GROUP BY ar.dimension
                    """,
                    (start_date, end_date),
                )
                rows = cursor.fetchall()
                return {row[0]: row[1] for row in rows}

        except Exception as e:
            logger.error(
                f"Failed to get average ratings for date range {start_date} to {end_date}: {e}",
                exc_info=True,
            )
            raise
