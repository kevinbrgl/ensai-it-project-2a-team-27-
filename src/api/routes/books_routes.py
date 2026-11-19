"""Routes for book operations in the FastAPI application.

Provides endpoints for searching and browsing books.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query, status

from src.api.deps import BookServiceDep, CurrentUser
from src.models.books import Book, BookDetails
from src.utils.exceptions import (
    BookNotFoundError,
    DAOError,
    ExternalServiceError,
    InvalidSearchQueryError,
)

router = APIRouter(prefix="/books", tags=["Books"])
logger = logging.getLogger(__name__)


@router.get(
    "/search",
    status_code=status.HTTP_200_OK,
    summary="🔍 Search books",
    responses={
        400: {"description": "Search is too generic (e.g. only 'the')"},
        500: {"description": "Database error"},
        502: {"description": "Open Library is unavailable"},
    },
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
    """Search books by **title** or **author** on Open Library.

    🔒 Authentication required

    **Behaviour:** the books found are **saved in the local catalog**,
    so they get an ID you can use in the other routes (library,
    playlists, reviews).

    **Parameters:**

    - 🔤 `q`: the text to search for
    - 🔢 `limit`: number of books to return, from 1 to 50 (default 10)

    **Use cases:**

    - Find a book before adding it to your library
    - Discover the books of an author
    \f

    Parameters
    ----------
    service : BookService
        Book service dependency.
    _current_user : User
        Authenticated user dependency.
    q : str
        Title or author search text.
    limit : int, optional
        Maximum number of books to return. Defaults to 10.

    Returns
    -------
    list[Book]
        List of found books.

    Raises
    ------
    HTTPException
        400 if the search is too generic, 502 if Open Library is
        unavailable, 500 if a database error occurs.

    """
    try:
        return service.search_books(query=q, limit=limit)
    except InvalidSearchQueryError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from None
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


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    summary="📚 Browse the local catalog",
    responses={500: {"description": "Database error"}},
)
def get_books(
    service: BookServiceDep,
    _current_user: CurrentUser,
    category: Annotated[
        str | None,
        Query(description="Filter books by category"),
    ] = None,
    author: Annotated[
        str | None,
        Query(description="Filter books by author"),
    ] = None,
) -> list[Book]:
    """List the books of the **local catalog**, with optional filters.

    🔒 Authentication required

    **Filters:**

    - 🏷️ `category`: keep only the books of this category
    - ✍️ `author`: keep only the books of this author

    **Behaviour:** both filters can be combined. Without any filter,
    the **whole catalog** is returned.
    \f

    Parameters
    ----------
    service : BookService
        Book service dependency.
    _current_user : User
        Authenticated user dependency.
    category : str | None, optional
        Category to filter by.
    author : str | None, optional
        Author to filter by.

    Returns
    -------
    list[Book]
        List of found books from the local catalog.

    Raises
    ------
    HTTPException
        500 if a database error occurs.

    """
    try:
        return service.get_books(category=category, author=author)
    except DAOError:
        logger.exception("Database error while retrieving books catalog")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred while retrieving books.",
        ) from None


@router.get(
    "/{book_id}",
    status_code=status.HTTP_200_OK,
    summary="📖 Get a book",
    responses={
        404: {"description": "Book not found"},
        500: {"description": "Database error"},
    },
)
def get_book_details(
    book_id: Annotated[
        int,
        Path(ge=1, description="Database ID of the book"),
    ],
    service: BookServiceDep,
    _current_user: CurrentUser,
) -> BookDetails:
    """Return the **details** of one book, with its **editions**.

    🔒 Authentication required

    **Returns:** title, author, category, publication date,
    description, cover image, number of pages and the list of
    `editions`.

    **Editions:** they are read live on Open Library (up to 20) and
    are **not stored**. For each edition: title, publishers,
    publication date, number of pages, ISBN and language.

    **Good to know:**

    - `book_id` is the **database ID** of the book, as returned by
      the search route
    - if Open Library is unavailable, the book is still returned,
      with an **empty** `editions` list
    \f

    Parameters
    ----------
    book_id : int
        Unique database identifier of the book.
    service : BookService
        Book service dependency.
    _current_user : User
        Authenticated user dependency.

    Returns
    -------
    BookDetails
        The book with all metadata and its editions.

    Raises
    ------
    HTTPException
        404 if the book is not found in database, 500 if a database error
        occurs.

    """
    try:
        return service.get_book_details(book_id)
    except BookNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found.",
        ) from None
    except DAOError:
        logger.exception("Database error while retrieving book %s", book_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred while retrieving book details.",
        ) from None
