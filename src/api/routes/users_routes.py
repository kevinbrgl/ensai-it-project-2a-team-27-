"""Routes for user operations in the FastAPI application.

Provides endpoints for profile reading, search, follow, unfollow,
followers, following, quests, and updates.
Registration is handled in auth_routes.py.
"""

import logging
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, status

from src.api.deps import (
    CurrentUser,
    CursorDep,
    LibraryServiceDep,
    PlaylistServiceDep,
    QuestServiceDep,
    UserServiceDep,
)
from src.dao.users_dao import UserDAO
from src.models import (
    Quest,
    User,
    UserRead,
    UserUpdate,
    UserUpdatePassword,
)
from src.models.library import LibraryBookDetails
from src.models.playlists import PlaylistRead
from src.services.users_service import UserService
from src.utils.exceptions import (
    AlreadyFollowingError,
    DAOError,
    EmailAlreadyExistsError,
    IncorrectPasswordError,
    NotFollowingError,
    SamePasswordError,
    SelfFollowError,
    SelfUnfollowError,
    UserAlreadyExistsError,
    UserNotFoundError,
)

router = APIRouter(prefix="/users", tags=["Users"])
logger = logging.getLogger(__name__)


@router.get("/me", response_model=UserRead)
def read_self(current_user: CurrentUser) -> User:
    """Read the current users's information.

    :param current_user: The current authenticated user
    :return: The user information
    """
    return current_user


@router.get(
    "/me/quests",
    status_code=status.HTTP_200_OK,
)
def get_my_quests(
    service: QuestServiceDep,
    current_user: CurrentUser,
    status_filter: Annotated[
        Literal["all", "active", "completed"],
        Query(
            alias="status",
            description=(
                "Filter by quest status ('all', 'active', 'completed')"
            ),
        ),
    ] = "all",
) -> list[Quest]:
    """Retrieve active quests and their progress for the authenticated user.

    Route is protected and requires authentication.

    :param service: Quest service dependency
    :param current_user: Authenticated user making the request
    :param status_filter: Filter to retrieve 'all', 'active', or 'completed'
    :raises HTTPException: 500 on database error
    :return: List of Quest objects with calculated progress
    """
    try:
        return service.get_quests(
            user_id=current_user.id_user,
            status_filter=status_filter,
        )
    except DAOError:
        logger.exception(
            "Failed to retrieve quests for user %s",
            current_user.id_user,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve quests.",
        ) from None


@router.get(
    "/search",
    response_model=list[UserRead],
    status_code=status.HTTP_200_OK,
)
def search_users(
    service: UserServiceDep,
    _current_user: CurrentUser,
    username: Annotated[
        str,
        Query(
            min_length=1,
            max_length=30,
            description="Username search query",
        ),
    ],
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=50,
            description="Maximum number of users to return",
        ),
    ] = 10,
) -> list[User]:
    """Search for users by username substring.

    Route is protected and requires authentication.

    :param service: User service dependency
    :param _current_user: The authenticated user making the request
    :param username: Username query string
    :param limit: Maximum number of users to return
    :raises HTTPException: 500 on database error
    :return: List of matching users
    """
    try:
        return service.search_users(username=username, limit=limit)
    except DAOError:
        logger.exception("Failed to search users with query: %s", username)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not search users.",
        ) from None


@router.post(
    "/{user_id}/follow",
    status_code=status.HTTP_204_NO_CONTENT,
)
def follow_user(
    service: UserServiceDep,
    current_user: CurrentUser,
    user_id: int,
) -> None:
    """Follow another user.

    Route is protected and requires authentication.

    :param service: User service dependency
    :param current_user: Authenticated user making the request (follower)
    :param user_id: ID of the user to follow (following)
    :raises HTTPException: 400 if user attempts to follow themselves,
        404 if target user is not found,
        409 if already following,
        500 on database error
    """
    try:
        service.follow_user(
            follower_id=current_user.id_user,
            following_id=user_id,
        )
    except SelfFollowError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Users cannot follow themselves.",
        ) from None
    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        ) from None
    except AlreadyFollowingError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Already following this user.",
        ) from None
    except DAOError:
        logger.exception(
            "Failed to follow user %s for follower %s",
            user_id,
            current_user.id_user,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not follow user.",
        ) from None


@router.delete(
    "/{user_id}/follow",
    status_code=status.HTTP_204_NO_CONTENT,
)
def unfollow_user(
    service: UserServiceDep,
    current_user: CurrentUser,
    user_id: int,
) -> None:
    """Unfollow another user.

    Route is protected and requires authentication.

    :param service: User service dependency
    :param current_user: Authenticated user making the request (follower)
    :param user_id: ID of the user to unfollow (following)
    :raises HTTPException: 400 if user attempts to unfollow themselves,
        404 if target user is not found or not currently followed,
        500 on database error
    """
    try:
        service.unfollow_user(
            follower_id=current_user.id_user,
            following_id=user_id,
        )
    except SelfUnfollowError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Users cannot unfollow themselves.",
        ) from None
    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        ) from None
    except NotFollowingError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not following this user.",
        ) from None
    except DAOError:
        logger.exception(
            "Failed to unfollow user %s for follower %s",
            user_id,
            current_user.id_user,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not unfollow user.",
        ) from None


@router.get(
    "/{user_id}/followers",
    response_model=list[UserRead],
    status_code=status.HTTP_200_OK,
)
def get_followers(
    service: UserServiceDep,
    _current_user: CurrentUser,
    user_id: int,
) -> list[User]:
    """List a user's followers.

    Route is protected and requires authentication.

    :param service: User service dependency
    :param _current_user: Authenticated user making the request
    :param user_id: ID of the user whose followers to retrieve
    :raises HTTPException: 404 if the user is not found,
        500 on database error
    :return: List of followers
    """
    try:
        return service.get_followers(user_id)
    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        ) from None
    except DAOError:
        logger.exception("Failed to get followers for user %s", user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve followers.",
        ) from None


@router.get(
    "/{user_id}/following",
    response_model=list[UserRead],
    status_code=status.HTTP_200_OK,
)
def get_following(
    service: UserServiceDep,
    _current_user: CurrentUser,
    user_id: int,
) -> list[User]:
    """List the users followed by a user.

    Route is protected and requires authentication.

    :param service: User service dependency
    :param _current_user: Authenticated user making the request
    :param user_id: ID of the user whose followed users to retrieve
    :raises HTTPException: 404 if the user is not found,
        500 on database error
    :return: List of followed users
    """
    try:
        return service.get_following(user_id)
    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        ) from None
    except DAOError:
        logger.exception("Failed to get following for user %s", user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve followed users.",
        ) from None


@router.patch("/me", response_model=UserRead)
def update_self(
    cursor: CursorDep,
    current_user: CurrentUser,
    user_in: UserUpdate,
) -> User:
    """Update the current user's information.

    :param cursor: Database cursor dependency
    :param current_user: The current authenticated user
    :param user_in: User update data
    :raises HTTPException: 400 if there is nothing to update,
        404 if the user is not found,
        409 if the new username or email is already used
    :return: The updated User object
    """
    try:
        return UserService(UserDAO(cursor)).update(
            current_user.id_user,
            user_in,
        )

    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        ) from None
    except UserAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already used.",
        ) from None
    except EmailAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already used.",
        ) from None
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nothing to update.",
        ) from None


@router.put("/me/password", response_model=UserRead)
def update_self_password(
    cursor: CursorDep,
    current_user: CurrentUser,
    user_in: UserUpdatePassword,
) -> User:
    """Update the current user's password.

    :param cursor: Database cursor dependency
    :param current_user: The current authenticated user
    :param user_in: Password update data
    :raises HTTPException: 400 if the new password is the same as the
     current one, 403 if the current password is wrong,
     404 if the user is not found    :return: The updated User object
    """
    try:
        return UserService(
            UserDAO(cursor),
        ).update_password(current_user, user_in)
    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        ) from None
    except SamePasswordError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The new password must be different from the current one.",
        ) from None
    except IncorrectPasswordError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Wrong password provided",
        ) from None


@router.get("/{user_id}/library")
def get_user_library(
    user_service: UserServiceDep,
    library_service: LibraryServiceDep,
    _current_user: CurrentUser,
    user_id: int,
    status_filter: Annotated[
        str | None,
        Query(
            alias="status",
            pattern="^(READING|WANT_TO_READ|COMPLETED)$",
            description="Filter by reading state",
        ),
    ] = None,
) -> list[LibraryBookDetails]:
    """List the books in another user's library.

    Every authenticated user can see the library of any user.

    :param user_service: User service dependency
    :param library_service: Library service dependency
    :param _current_user: Authenticated user making the request
    :param user_id: ID of the user whose library to retrieve
    :param status_filter: Optional reading state to filter by
    :raises HTTPException: 404 if the user is not found,
        500 on database error
    :return: The books of the user's library
    """
    try:
        user_service.read(user_id)
        return library_service.list_books(user_id, status_filter)
    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        ) from None
    except DAOError:
        logger.exception("Failed to get the library of user %s", user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve the library.",
        ) from None


@router.get("/{user_id}/playlists")
def get_user_playlists(
    user_service: UserServiceDep,
    playlist_service: PlaylistServiceDep,
    _current_user: CurrentUser,
    user_id: int,
) -> list[PlaylistRead]:
    """List another user's playlists.

    Every authenticated user can see the playlists of any user.

    :param user_service: User service dependency
    :param playlist_service: Playlist service dependency
    :param _current_user: Authenticated user making the request
    :param user_id: ID of the user whose playlists to retrieve
    :raises HTTPException: 404 if the user is not found,
        500 on database error
    :return: The user's playlists, in creation order
    """
    try:
        user_service.read(user_id)
        return playlist_service.list_playlists(user_id)
    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        ) from None
    except DAOError:
        logger.exception("Failed to get the playlists of user %s", user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve the playlists.",
        ) from None
