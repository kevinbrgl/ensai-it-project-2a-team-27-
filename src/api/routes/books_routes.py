"""Routes for book operations in the FastAPI application.

Provides endpoints for searching and browsing books.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from src.api.deps import BookServiceDep, CurrentUser
from src.models.books import Book
from src.utils.exceptions import DAOError, ExternalServiceError

router = APIRouter(prefix="/books", tags=["Books"])
logger = logging.getLogger(__name__)


@router.get(
    "/search",
    status_code=status.HTTP_200_OK,
)
def search_books(
    service: BookServiceDep,
    _current_user: CurrentUser,
    q: Annotated[str, Query(min_length=1, description="Title/author search")],
    limit: Annotated[
        int,
        Query(ge=1, le=50, description="Max books to return"),
    ] = 10,
) -> list[Book]:
    """Search Open Library by title or author and synchronize local records.

    :param service: Book service dependency
    :param _current_user: Authenticated user dependency
    :param q: Search query parameter
    :param limit: Maximum number of books to return
    :raises HTTPException: 502 if Open Library is unavailable,
        500 if a database error occurs
    :return: List of found books
    """
    try:
        return service.search_books(query=q, limit=limit)
    except ExternalServiceError as exc:
        logger.warning("Open Library unavailable during search: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Open Library service is unavailable.",
        ) from None
    except DAOError:
        logger.exception("Database error while searching books")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred during book search.",
        ) from None
