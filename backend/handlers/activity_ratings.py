"""
Activity Ratings Handler - API endpoints for multi-dimensional activity ratings

Endpoints:
- POST /activities/rating/save - Save or update an activity rating
- POST /activities/rating/get - Get all ratings for an activity
- POST /activities/rating/delete - Delete a specific rating
"""

from datetime import datetime
from typing import List, Optional

from core.db import get_db
from core.logger import get_logger
from models.base import BaseModel
from models.responses import TimedOperationResponse

# CRITICAL: Use relative import to avoid circular imports
from . import api_handler

logger = get_logger(__name__)


# ============ Request Models ============


class SaveActivityRatingRequest(BaseModel):
    """Request to save or update an activity rating"""

    activity_id: str
    dimension: str
    rating: int  # 1-5
    note: Optional[str] = None


class GetActivityRatingsRequest(BaseModel):
    """Request to get ratings for an activity"""

    activity_id: str


class DeleteActivityRatingRequest(BaseModel):
    """Request to delete a specific rating"""

    activity_id: str
    dimension: str


# ============ Response Models ============


class ActivityRatingData(BaseModel):
    """Individual rating record"""

    id: str
    activity_id: str
    dimension: str
    rating: int
    note: Optional[str] = None
    created_at: str
    updated_at: str


class SaveActivityRatingResponse(TimedOperationResponse):
    """Response after saving a rating"""

    data: Optional[ActivityRatingData] = None


class GetActivityRatingsResponse(TimedOperationResponse):
    """Response with list of ratings"""

    data: Optional[List[ActivityRatingData]] = None


# ============ API Handlers ============


@api_handler(
    body=SaveActivityRatingRequest,
    method="POST",
    path="/activities/rating/save",
    tags=["activities"],
)
async def save_activity_rating(
    body: SaveActivityRatingRequest,
) -> SaveActivityRatingResponse:
    """
    Save or update an activity rating

    Supports multi-dimensional ratings:
    - focus_level: How focused were you? (1-5)
    - productivity: How productive was this session? (1-5)
    - importance: How important was this activity? (1-5)
    - satisfaction: How satisfied are you with the outcome? (1-5)
    """
    try:
        db = get_db()

        # Validate rating range
        if not 1 <= body.rating <= 5:
            return SaveActivityRatingResponse(
                success=False,
                message="Rating must be between 1 and 5",
                timestamp=datetime.now().isoformat(),
            )

        # Save rating
        rating_record = await db.activity_ratings.save_rating(
            activity_id=body.activity_id,
            dimension=body.dimension,
            rating=body.rating,
            note=body.note,
        )

        logger.info(
            f"Saved activity rating: {body.activity_id} - "
            f"{body.dimension} = {body.rating}"
        )

        return SaveActivityRatingResponse(
            success=True,
            message="Rating saved successfully",
            data=ActivityRatingData(**rating_record),
            timestamp=datetime.now().isoformat(),
        )

    except Exception as e:
        logger.error(f"Failed to save activity rating: {e}", exc_info=True)
        return SaveActivityRatingResponse(
            success=False,
            message=f"Failed to save rating: {str(e)}",
            timestamp=datetime.now().isoformat(),
        )


@api_handler(
    body=GetActivityRatingsRequest,
    method="POST",
    path="/activities/rating/get",
    tags=["activities"],
)
async def get_activity_ratings(
    body: GetActivityRatingsRequest,
) -> GetActivityRatingsResponse:
    """
    Get all ratings for an activity

    Returns ratings for all dimensions that have been rated.
    """
    try:
        db = get_db()

        # Fetch ratings
        ratings = await db.activity_ratings.get_ratings_by_activity(body.activity_id)

        logger.debug(f"Retrieved {len(ratings)} ratings for activity {body.activity_id}")

        return GetActivityRatingsResponse(
            success=True,
            message=f"Retrieved {len(ratings)} rating(s)",
            data=[ActivityRatingData(**r) for r in ratings],
            timestamp=datetime.now().isoformat(),
        )

    except Exception as e:
        logger.error(f"Failed to get activity ratings: {e}", exc_info=True)
        return GetActivityRatingsResponse(
            success=False,
            message=f"Failed to get ratings: {str(e)}",
            timestamp=datetime.now().isoformat(),
        )


@api_handler(
    body=DeleteActivityRatingRequest,
    method="POST",
    path="/activities/rating/delete",
    tags=["activities"],
)
async def delete_activity_rating(
    body: DeleteActivityRatingRequest,
) -> TimedOperationResponse:
    """
    Delete a specific activity rating

    Removes the rating for a specific dimension.
    """
    try:
        db = get_db()

        # Delete rating
        await db.activity_ratings.delete_rating(body.activity_id, body.dimension)

        logger.info(
            f"Deleted activity rating: {body.activity_id} - {body.dimension}"
        )

        return TimedOperationResponse(
            success=True,
            message="Rating deleted successfully",
            timestamp=datetime.now().isoformat(),
        )

    except Exception as e:
        logger.error(f"Failed to delete activity rating: {e}", exc_info=True)
        return TimedOperationResponse(
            success=False,
            message=f"Failed to delete rating: {str(e)}",
            timestamp=datetime.now().isoformat(),
        )
