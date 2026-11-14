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
    summary="➕ Create a playlist",
    responses={
        409: {"description": "A playlist with this name already exists"},
        500: {"description": "Database error"},
    },
)
def create_playlist(
    service: PlaylistServiceDep,
    current_user: CurrentUser,
    playlist_in: PlaylistCreate,
) -> PlaylistRead:
    """Create a new **playlist** to group books together.

    🔒 Authentication required

    **Rules:**

    - 🏷️ `name`: 1 to 100 characters
    - You cannot have **two playlists with the same name**

    **Behaviour:** the playlist is created **empty**.

    **Example request:**

    ```json
    {
      "name": "Summer reads"
    }
    ```
    \f
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


@router.get(
    "",
    summary="🎵 List my playlists",
    responses={500: {"description": "Database error"}},
)
def list_playlists(
    service: PlaylistServiceDep,
    current_user: CurrentUser,
) -> list[PlaylistRead]:
    """List **your playlists**, in creation order.

    🔒 Authentication required

    **Returns:** the ID and the name of each playlist, without its
    books. Open one playlist to see its books.

    **Good to know:** the list is **empty** when you have no playlist
    yet.
    \f
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


@router.patch(
    "/{id_playlist}",
    summary="✏️ Rename a playlist",
    responses={
        404: {"description": "Playlist not found"},
        409: {"description": "A playlist with this name already exists"},
        500: {"description": "Database error"},
    },
)
def rename_playlist(
    service: PlaylistServiceDep,
    current_user: CurrentUser,
    id_playlist: int,
    playlist_in: PlaylistUpdate,
) -> PlaylistRead:
    """Change the **name** of one of your playlists.

    🔒 Authentication required

    **Rules:**

    - 🏷️ `name`: 1 to 100 characters
    - The new name must not be used by **another of your playlists**

    **Good to know:** you can only rename **your own** playlists. The
    books of the playlist are not changed.

    **Example request:**

    ```json
    {
      "name": "Winter reads"
    }
    ```
    \f
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
    summary="🗑️ Delete a playlist",
    responses={
        404: {"description": "Playlist not found"},
        500: {"description": "Database error"},
    },
)
def delete_playlist(
    service: PlaylistServiceDep,
    current_user: CurrentUser,
    id_playlist: int,
) -> None:
    """Delete one of **your playlists**.

    🔒 Authentication required

    **Behaviour:** only the playlist is deleted. Its books stay in
    the catalog and in your library.

    **Good to know:** you can only delete **your own** playlists.

    **Response:** `204 No Content`, with an empty body.
    \f
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
    summary="➕ Add a book to a playlist",
    responses={
        404: {"description": "Playlist or book not found"},
        409: {"description": "Book already in the playlist"},
        500: {"description": "Database error"},
    },
)
def add_book_to_playlist(
    service: PlaylistServiceDep,
    current_user: CurrentUser,
    id_playlist: int,
    book_in: PlaylistBookAdd,
) -> PlaylistBookRead:
    """Add a **book** to one of your playlists.

    🔒 Authentication required

    **Rules:**

    - 📖 `id_book`: database ID of a book of the **local catalog**
    - A book can only be in the same playlist **once**

    **Good to know:** you can only fill **your own** playlists.

    **Example request:**

    ```json
    {
      "id_book": 12
    }
    ```
    \f
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


@router.get(
    "/{id_playlist}",
    summary="🎵 Get a playlist with its books",
    responses={
        404: {"description": "Playlist not found"},
        500: {"description": "Database error"},
    },
)
def get_playlist(
    service: PlaylistServiceDep,
    current_user: CurrentUser,
    id_playlist: int,
) -> PlaylistDetails:
    """Return one of **your playlists**, with the details of its books.

    🔒 Authentication required

    **Returns:** the name of the playlist and the full list of its
    books (title, author, category, cover image...).

    **Good to know:** a playlist that belongs to **another user** is
    answered as **not found**.
    \f
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
    summary="🗑️ Remove a book from a playlist",
    responses={
        404: {"description": "Playlist not found or book not in it"},
        500: {"description": "Database error"},
    },
)
def remove_book_from_playlist(
    service: PlaylistServiceDep,
    current_user: CurrentUser,
    id_playlist: int,
    id_book: int,
) -> None:
    """Remove a **book** from one of your playlists.

    🔒 Authentication required

    **Behaviour:** the book only leaves the playlist. It stays in the
    catalog and in your library.

    **Response:** `204 No Content`, with an empty body.
    \f
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
