"""Routes for playlist operations in the FastAPI application."""

import logging

from fastapi import APIRouter, HTTPException, status

from src.api.deps import CurrentUser, PlaylistServiceDep
from src.models.playlists import (
    PlaylistBookAdd,
    PlaylistBookRead,
    PlaylistCreate,
    PlaylistDetails,
    PlaylistRead,
    PlaylistUpdate,
)
from src.utils.exceptions import (
    BookAlreadyInPlaylistError,
    BookNotFoundError,
    BookNotInPlaylistError,
    DAOError,
    PlaylistAlreadyExistsError,
    PlaylistNotFoundError,
)

router = APIRouter(prefix="/playlists", tags=["Playlists"])
logger = logging.getLogger(__name__)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
)
def create_playlist(
    service: PlaylistServiceDep,
    current_user: CurrentUser,
    playlist_in: PlaylistCreate,
) -> PlaylistRead:
    """Create a playlist for the authenticated user.

    :param service: Playlist service dependency
    :param current_user: The authenticated user
    :param playlist_in: Name of the playlist to create
    :raises HTTPException: 409 if the user already has a playlist with this
        name, 500 on database error
    :return: The created playlist
    """
    try:
        return service.create_playlist(current_user.id_user, playlist_in)

    except PlaylistAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A playlist with this name already exists.",
        ) from None

    except DAOError:
        logger.exception(
            "Failed to create playlist for user %s",
            current_user.id_user,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create the playlist.",
        ) from None


@router.get("")
def list_playlists(
    service: PlaylistServiceDep,
    current_user: CurrentUser,
) -> list[PlaylistRead]:
    """List the playlists of the authenticated user.

    Returns an empty list when the user has no playlists.

    :param service: Playlist service dependency
    :param current_user: The authenticated user
    :raises HTTPException: 500 on database error
    :return: The playlists, in creation order
    """
    try:
        return service.list_playlists(current_user.id_user)

    except DAOError:
        logger.exception(
            "Failed to list playlists of user %s",
            current_user.id_user,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not list the playlists.",
        ) from None


@router.patch("/{id_playlist}")
def rename_playlist(
    service: PlaylistServiceDep,
    current_user: CurrentUser,
    id_playlist: int,
    playlist_in: PlaylistUpdate,
) -> PlaylistRead:
    """Rename one of the authenticated user's playlists.

    :param service: Playlist service dependency
    :param current_user: The authenticated user
    :param id_playlist: ID of the playlist to rename
    :param playlist_in: New name of the playlist
    :raises HTTPException: 404 if the playlist is not found or belongs to
        another user, 409 if the new name is already used, 500 on database
        error
    :return: The renamed playlist
    """
    try:
        return service.rename_playlist(
            current_user.id_user,
            id_playlist,
            playlist_in,
        )

    except PlaylistNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Playlist not found.",
        ) from None

    except PlaylistAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A playlist with this name already exists.",
        ) from None

    except DAOError:
        logger.exception(
            "Failed to rename playlist %s of user %s",
            id_playlist,
            current_user.id_user,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not rename the playlist.",
        ) from None


@router.delete(
    "/{id_playlist}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_playlist(
    service: PlaylistServiceDep,
    current_user: CurrentUser,
    id_playlist: int,
) -> None:
    """Delete one of the authenticated user's playlists.

    Returns 204 No Content with an empty body when the playlist is deleted.

    :param service: Playlist service dependency
    :param current_user: The authenticated user
    :param id_playlist: ID of the playlist to delete
    :raises HTTPException: 404 if the playlist is not found or belongs to
        another user, 500 on database error
    """
    try:
        service.delete_playlist(current_user.id_user, id_playlist)

    except PlaylistNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Playlist not found.",
        ) from None

    except DAOError:
        logger.exception(
            "Failed to delete playlist %s of user %s",
            id_playlist,
            current_user.id_user,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not delete the playlist.",
        ) from None


@router.post(
    "/{id_playlist}/books",
    status_code=status.HTTP_201_CREATED,
)
def add_book_to_playlist(
    service: PlaylistServiceDep,
    current_user: CurrentUser,
    id_playlist: int,
    book_in: PlaylistBookAdd,
) -> PlaylistBookRead:
    """Add a book to one of the authenticated user's playlists.

    :param service: Playlist service dependency
    :param current_user: The authenticated user
    :param id_playlist: ID of the playlist
    :param book_in: ID of the book to add
    :raises HTTPException: 404 if the playlist or the book is not found,
        409 if the book is already in the playlist, 500 on database error
    :return: The added playlist entry
    """
    try:
        return service.add_book_to_playlist(
            current_user.id_user,
            id_playlist,
            book_in,
        )

    except PlaylistNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Playlist not found.",
        ) from None

    except BookNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found in the local catalog.",
        ) from None

    except BookAlreadyInPlaylistError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Book is already in the playlist.",
        ) from None

    except DAOError:
        logger.exception(
            "Failed to add book %s to playlist %s of user %s",
            book_in.id_book,
            id_playlist,
            current_user.id_user,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not add the book to the playlist.",
        ) from None


@router.get("/{id_playlist}")
def get_playlist(
    service: PlaylistServiceDep,
    current_user: CurrentUser,
    id_playlist: int,
) -> PlaylistDetails:
    """Return one of the authenticated user's playlists, with its books.

    :param service: Playlist service dependency
    :param current_user: The authenticated user
    :param id_playlist: ID of the playlist
    :raises HTTPException: 404 if the playlist is not found or belongs to
        another user, 500 on database error
    :return: The playlist and the details of its books
    """
    try:
        return service.get_playlist(current_user.id_user, id_playlist)

    except PlaylistNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Playlist not found.",
        ) from None

    except DAOError:
        logger.exception(
            "Failed to read playlist %s of user %s",
            id_playlist,
            current_user.id_user,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not read the playlist.",
        ) from None


@router.delete(
    "/{id_playlist}/books/{id_book}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_book_from_playlist(
    service: PlaylistServiceDep,
    current_user: CurrentUser,
    id_playlist: int,
    id_book: int,
) -> None:
    """Remove a book from one of the authenticated user's playlists.

    Returns 204 No Content with an empty body when the book is removed.

    :param service: Playlist service dependency
    :param current_user: The authenticated user
    :param id_playlist: ID of the playlist
    :param id_book: ID of the book to remove
    :raises HTTPException: 404 if the playlist is not found or the book is
        not in it, 500 on database error
    """
    try:
        service.remove_book_from_playlist(
            current_user.id_user,
            id_playlist,
            id_book,
        )

    except PlaylistNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Playlist not found.",
        ) from None

    except BookNotInPlaylistError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book is not in the playlist.",
        ) from None

    except DAOError:
        logger.exception(
            "Failed to remove book %s from playlist %s of user %s",
            id_book,
            id_playlist,
            current_user.id_user,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not remove the book from the playlist.",
        ) from None
