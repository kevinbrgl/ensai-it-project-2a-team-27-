"""Routes for book recommendations in the FastAPI application."""

import logging
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from src.api.deps import CurrentUser, RecommendationServiceDep
from src.models.recommendations import Recommendation, RecommendationSort
from src.utils.exceptions import DAOError

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])
logger = logging.getLogger(__name__)


@router.get(
    "",
    status_code=status.HTTP_200_OK,
)
def get_recommendations(
    service: RecommendationServiceDep,
    current_user: CurrentUser,
    genre: Annotated[
        str | None,
        Query(
            min_length=1,
            max_length=100,
            description="Genre to recommend (default: favorite genres)",
        ),
    ] = None,
    sort: Annotated[
        RecommendationSort,
        Query(description="Sort order ('rating', 'new', 'title')"),
    ] = "rating",
    limit: Annotated[
        int,
        Query(ge=1, le=50, description="Max books to return"),
    ] = 10,
) -> list[Recommendation]:
    """Recommend books to the authenticated user.

    Books already in the user's library are never recommended.

    :param service: Recommendation service dependency
    :param current_user: The authenticated user
    :param genre: Optional genre to recommend
    :param sort: Sort order of the recommendations
    :param limit: Maximum number of recommendations
    :raises HTTPException: 500 on database error
    :return: The recommended books, with their score and reason
    """
    try:
        return service.get_recommendations(
            current_user.id_user,
            genre=genre,
            sort=sort,
            limit=limit,
        )
    except DAOError:
        logger.exception(
            "Failed to compute recommendations for user %s",
            current_user.id_user,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not compute the recommendations.",
        ) from None
