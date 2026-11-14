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
    summary="✨ Get book recommendations",
    responses={500: {"description": "Database error"}},
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
    """Suggest **books you may like**, each with a score and a reason.

    🔒 Authentication required

    **How it works:**

    - 🎯 With `genre`: popular books of **this genre**
    - 📚 Without `genre`: books of **your favorite genres**, found
      from your library and from the books you rated 4 or more
    - 🏆 If nothing is found: the **best rated** books of Ex-Libris

    **Parameters:**

    - 🔀 `sort`: `rating` (default), `new` or `title`
    - 🔢 `limit`: number of books to return, from 1 to 50 (default 10)

    **Good to know:** books **already in your library** are never
    recommended.

    **Example response:**

    ```json
    [
      {
        "book": {
          "id_book": 42,
          "title": "Dune",
          "author": "Frank Herbert",
          "category": "Science Fiction"
        },
        "score": 4.3,
        "reason": "Because you like Science Fiction"
      }
    ]
    ```
    \f
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
