"""Routes for library operations in the FastAPI application."""

import logging
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from src.api.deps import CurrentUser, LibraryServiceDep
from src.models.library import (
    LibraryBookAdd,
    LibraryBookDetails,
    LibraryBookRead,
    LibraryBookUpdateDates,
    LibraryBookUpdateStatus,
)
from src.utils.exceptions import (
    BookAlreadyInLibraryError,
    BookNotFoundError,
    BookNotInLibraryError,
    DAOError,
    InvalidReadingDatesError,
)

router = APIRouter(prefix="/library", tags=["Library"])
logger = logging.getLogger(__name__)


@router.post(
    "/books",
    status_code=status.HTTP_201_CREATED,
    summary="➕ Add a book to my library",
    responses={
        404: {"description": "Book not found in the local catalog"},
        409: {"description": "Book already in the library"},
        500: {"description": "Database error"},
    },
)
def add_book(
    service: LibraryServiceDep,
    current_user: CurrentUser,
    book_in: LibraryBookAdd,
) -> LibraryBookRead:
    """Add a book to **your library** with a reading status.

    🔒 Authentication required

    **Fields:**

    - 📖 `id_book`: database ID of the book (find it with the search)
    - 🚦 `state`: `WANT_TO_READ`, `READING`, `COMPLETED` or `ABANDONED`

    **Behavior:** the book starts **not liked** and **not favorite**.
    A book can only be in your library **once**.

    **Example request:**

    ```json
    {
      "id_book": 12,
      "state": "WANT_TO_READ"
    }
    ```
    \f

    Parameters
    ----------
    service : LibraryService
        Library service dependency.
    current_user : User
        The authenticated user.
    book_in : LibraryBookAdd
        Catalog book ID and initial reading status.

    Returns
    -------
    LibraryBookRead
        The newly created reading activity.

    Raises
    ------
    HTTPException
        404 if the book does not exist in the catalog, 409 if it is already in
        the user's library, or 500 on a database error.

    """
    try:
        return service.add_book_to_library(current_user.id_user, book_in)

    except BookAlreadyInLibraryError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Book is already in the library.",
        ) from None

    except BookNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found in the local catalog.",
        ) from None

    except DAOError:
        logger.exception(
            "Failed to add book %s to library of user %s",
            book_in.id_book,
            current_user.id_user,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not add book to library.",
        ) from None


@router.delete(
    "/books/{id_book}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="🗑️ Remove a book from my library",
    responses={
        404: {"description": "Book is not in the library"},
        500: {"description": "Database error"},
    },
)
def remove_book(
    service: LibraryServiceDep,
    current_user: CurrentUser,
    id_book: int,
) -> None:
    """Remove a book from **your library**.

    🔒 Authentication required

    **Behavior:** its reading status, like and favorite flag are
    **lost**. The book itself stays in the catalog.

    **Response:** `204 No Content`, with an empty body.
    \f

    Parameters
    ----------
    service : LibraryService
        Library service dependency.
    current_user : User
        The authenticated user.
    id_book : int
        ID of the book to remove.

    Raises
    ------
    HTTPException
        404 if not in library, 500 on database error.

    """
    try:
        service.remove_book_from_library(current_user.id_user, id_book)

    except BookNotInLibraryError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book is not in the library.",
        ) from None

    except DAOError:
        logger.exception(
            "Failed to remove book %s from library of user %s",
            id_book,
            current_user.id_user,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not remove book from library.",
        ) from None


@router.post(
    "/books/{id_book}/like",
    summary="❤️ Like or unlike a book",
    responses={
        404: {"description": "Book is not in the library"},
        500: {"description": "Database error"},
    },
)
def toggle_like(
    service: LibraryServiceDep,
    current_user: CurrentUser,
    id_book: int,
) -> LibraryBookRead:
    """Switch the **like** on a book of your library.

    🔒 Authentication required

    **Behavior:** this route is a **toggle**.

    - Book not liked → it becomes **liked**
    - Book already liked → the like is **removed**

    **Good to know:** the book must already be **in your library**.
    The new value is returned in `is_liked`.
    \f

    Parameters
    ----------
    service : LibraryService
        Library service dependency.
    current_user : User
        The authenticated user.
    id_book : int
        ID of the book to like or unlike.

    Returns
    -------
    LibraryBookRead
        Reading activity with the updated like flag.

    Raises
    ------
    HTTPException
        404 if not in library, 500 on database error.

    """
    try:
        return service.toggle_like(current_user.id_user, id_book)

    except BookNotInLibraryError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book is not in the library.",
        ) from None

    except DAOError:
        logger.exception(
            "Failed to toggle like on book %s for user %s",
            id_book,
            current_user.id_user,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not update the like.",
        ) from None


@router.post(
    "/books/{id_book}/favorite",
    summary="⭐ Add or remove a favorite",
    responses={
        404: {"description": "Book is not in the library"},
        500: {"description": "Database error"},
    },
)
def toggle_favorite(
    service: LibraryServiceDep,
    current_user: CurrentUser,
    id_book: int,
) -> LibraryBookRead:
    """Switch the **favorite** flag on a book of your library.

    🔒 Authentication required

    **Behavior:** this route is a **toggle**.

    - Book not in favorites → it is **added** to your favorites
    - Book already in favorites → it is **removed** from them

    **Good to know:** the book must already be **in your library**.
    The new value is returned in `is_favorite`.
    \f

    Parameters
    ----------
    service : LibraryService
        Library service dependency.
    current_user : User
        The authenticated user.
    id_book : int
        ID of the book to add to or remove from favorites.

    Returns
    -------
    LibraryBookRead
        Reading activity with the updated favorite flag.

    Raises
    ------
    HTTPException
        404 if not in library, 500 on database error.

    """
    try:
        return service.toggle_favorite(current_user.id_user, id_book)

    except BookNotInLibraryError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book is not in the library.",
        ) from None

    except DAOError:
        logger.exception(
            "Failed to toggle favorite on book %s for user %s",
            id_book,
            current_user.id_user,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not update the favorite.",
        ) from None


@router.patch(
    "/books/{id_book}/status",
    summary="🚦 Change the reading status of a book",
    responses={
        404: {"description": "Book is not in the library"},
        500: {"description": "Database error"},
    },
)
def update_book_status(
    service: LibraryServiceDep,
    current_user: CurrentUser,
    id_book: int,
    status_in: LibraryBookUpdateStatus,
) -> LibraryBookRead:
    """Change the **reading status** of a book of your library.

    🔒 Authentication required

    **Available statuses:**

    - 🔖 `WANT_TO_READ`: on your reading list
    - 📖 `READING`: you are reading it
    - ✅ `COMPLETED`: you finished it
    - 🚫 `ABANDONED`: you stopped reading it

    **Good to know:** finished books count in your **statistics** and
    your **quests**.

    **Example request:**

    ```json
    {
      "state": "COMPLETED"
    }
    ```
    \f

    Parameters
    ----------
    service : LibraryService
        Library service dependency.
    current_user : User
        The authenticated user.
    id_book : int
        ID of the book to update.
    status_in : LibraryBookUpdateStatus
        Request containing the new reading status.

    Returns
    -------
    LibraryBookRead
        The updated reading activity.

    Raises
    ------
    HTTPException
        404 if not in library, 500 on database error.

    """
    try:
        return service.update_book_status(
            current_user.id_user,
            id_book,
            status_in.state,
        )

    except BookNotInLibraryError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book is not in the library.",
        ) from None

    except DAOError:
        logger.exception(
            "Failed to update status of book %s for user %s",
            id_book,
            current_user.id_user,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not update the book status.",
        ) from None


@router.patch(
    "/books/{id_book}/dates",
    summary="📅 Set the reading dates of a book",
    responses={
        400: {"description": "Nothing to update, or end before start"},
        404: {"description": "Book is not in the library"},
        500: {"description": "Database error"},
    },
)
def update_book_dates(
    service: LibraryServiceDep,
    current_user: CurrentUser,
    id_book: int,
    dates_in: LibraryBookUpdateDates,
) -> LibraryBookRead:
    """Set the **start** and **end dates** of a book of your library.

    🔒 Authentication required

    **Fields:**

    - 🟢 `started_at`: the day you started the book (`YYYY-MM-DD`)
    - 🏁 `finished_at`: the day you finished it (`YYYY-MM-DD`)

    **Behavior:** only the fields you send are changed, the others
    keep their current value. Send `null` to **erase** a date.

    **Rule:** the end date cannot be **before** the start date. When
    you send only one date, it is compared with the stored one.

    **Example request:**

    ```json
    {
      "started_at": "2026-01-05",
      "finished_at": "2026-01-20"
    }
    ```
    \f

    Parameters
    ----------
    service : LibraryService
        Library service dependency.
    current_user : User
        The authenticated user.
    id_book : int
        ID of the book to update.
    dates_in : LibraryBookUpdateDates
        Reading dates to set or clear.

    Returns
    -------
    LibraryBookRead
        The updated reading activity.

    Raises
    ------
    HTTPException
        400 if there is nothing to update or if the end date is before the
        start date, 404 if not in library, 500 on database error.

    """
    try:
        return service.update_book_dates(
            current_user.id_user,
            id_book,
            dates_in,
        )

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nothing to update.",
        ) from None

    except InvalidReadingDatesError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The end date cannot be before the start date.",
        ) from None

    except BookNotInLibraryError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book is not in the library.",
        ) from None

    except DAOError:
        logger.exception(
            "Failed to update dates of book %s for user %s",
            id_book,
            current_user.id_user,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not update the reading dates.",
        ) from None


@router.get(
    "/books",
    summary="📚 List the books of my library",
    responses={500: {"description": "Database error"}},
)
def list_books(
    service: LibraryServiceDep,
    current_user: CurrentUser,
    status_filter: Annotated[
        str | None,
        Query(
            alias="status",
            pattern="^(READING|WANT_TO_READ|COMPLETED|ABANDONED)$",
            description="Filter by reading state",
        ),
    ] = None,
) -> list[LibraryBookDetails]:
    """List the books of **your library**, with their details.

    🔒 Authentication required

    **Filter:** `status` keeps only the books in one reading status
    (`WANT_TO_READ`, `READING`, `COMPLETED` or `ABANDONED`). Without
    it, **all** your books are returned.

    **Returns:** for each book, its details plus your reading status,
    like, favorite flag and reading dates.

    **Good to know:** the list is **empty** when no book matches.
    \f

    Parameters
    ----------
    service : LibraryService
        Library service dependency.
    current_user : User
        The authenticated user.
    status_filter : str | None, optional
        Reading status to filter by.

    Returns
    -------
    list[LibraryBookDetails]
        The list of library books.

    Raises
    ------
    HTTPException
        500 on database error.

    """
    try:
        return service.list_books(current_user.id_user, status_filter)

    except DAOError:
        logger.exception(
            "Failed to list books of user %s",
            current_user.id_user,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not list the library books.",
        ) from None


@router.get(
    "/favorites",
    summary="⭐ List my favorite books",
    responses={500: {"description": "Database error"}},
)
def list_favorites(
    service: LibraryServiceDep,
    current_user: CurrentUser,
) -> list[LibraryBookDetails]:
    """List the **favorite books** of your library.

    🔒 Authentication required

    **Returns:** the books you marked as favorite, with their details
    and reading dates.

    **Good to know:** the list is **empty** when you have no favorite
    yet.
    \f

    Parameters
    ----------
    service : LibraryService
        Library service dependency.
    current_user : User
        The authenticated user.

    Returns
    -------
    list[LibraryBookDetails]
        The favorite books, sorted by book ID.

    Raises
    ------
    HTTPException
        500 on database error.

    """
    try:
        return service.list_favorites(current_user.id_user)

    except DAOError:
        logger.exception(
            "Failed to list favorites of user %s",
            current_user.id_user,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not list the favorites.",
        ) from None
