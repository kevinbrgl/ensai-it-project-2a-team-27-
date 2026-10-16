"""Routes for library operations in the FastAPI application."""

import logging

from fastapi import APIRouter, HTTPException, status

from src.api.deps import CurrentUser, LibraryServiceDep
from src.models.library import LibraryBookAdd, LibraryBookRead
from src.utils.exceptions import (
    BookAlreadyInLibraryError,
    BookNotFoundError,
    BookNotInLibraryError,
    DAOError,
)

router = APIRouter(prefix="/library", tags=["Library"])
logger = logging.getLogger(__name__)


@router.post(
    "/books",
    status_code=status.HTTP_201_CREATED,
)
def add_book(
    service: LibraryServiceDep,
    current_user: CurrentUser,
    book_in: LibraryBookAdd,
) -> LibraryBookRead:
    """Add a book to the authenticated user's library.

    :param service: Library service dependency
    :param current_user: The authenticated user
    :param book_in: Data for the book to add
    :raises HTTPException: 409 if already in library, 500 on database error
    :return: The newly created reading activity
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
)
def remove_book(
    service: LibraryServiceDep,
    current_user: CurrentUser,
    id_book: int,
) -> None:
    """Remove a book from the authenticated user's library.

    Returns 204 No Content with an empty body when the book is removed.

    :param service: Library service dependency
    :param current_user: The authenticated user
    :param id_book: ID of the book to remove
    :raises HTTPException: 404 if not in library, 500 on database error
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


@router.post("/books/{id_book}/like")
def toggle_like(
    service: LibraryServiceDep,
    current_user: CurrentUser,
    id_book: int,
) -> LibraryBookRead:
    """Toggle the like on a book in the authenticated user's library.

    :param service: Library service dependency
    :param current_user: The authenticated user
    :param id_book: ID of the book to like or unlike
    :raises HTTPException: 404 if not in library, 500 on database error
    :return: The updated reading activity
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
