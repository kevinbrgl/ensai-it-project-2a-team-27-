"""Routes for user operations in the FastAPI application.

Provides endpoints for profile reading, search, follow, unfollow,
followers, following, quests, settings, and updates.
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
    StatsServiceDep,
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
from src.models.stats import UserStats
from src.models.users import UserMe, UserSettingsUpdate
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


@router.get("/me", response_model=UserRead, summary="👤 Get my profile")
def read_self(current_user: CurrentUser) -> User:
    """Return the **public profile** of your own account.

    🔒 Authentication required

    **Returns:** your ID, username, email, bio and profile picture.

    **Good to know:** the password is **never** returned. For your
    theme and visibility, use the settings route.
    \f
    :param current_user: The current authenticated user
    :return: The user information
    """
    return current_user


@router.get(
    "/me/settings",
    response_model=UserMe,
    summary="⚙️ Get my settings",
)
def read_my_settings(current_user: CurrentUser) -> User:
    """Return your profile together with your **private settings**.

    🔒 Authentication required

    **Returns, on top of your profile:**

    - 🎨 `theme`: `day` or `night`
    - 👁️ `profile_visibility`: `public` or `private`
    - 🛡️ `is_admin`: whether your account is an administrator

    **Example response:**

    ```json
    {
      "username": "alice",
      "email": "alice@example.com",
      "id_user": 1,
      "bio": null,
      "profile_picture": null,
      "theme": "night",
      "profile_visibility": "public",
      "is_admin": false
    }
    ```
    \f
    :param current_user: The current authenticated user
    :return: The user information and settings
    """
    return current_user


@router.patch(
    "/me/settings",
    response_model=UserMe,
    summary="⚙️ Update my settings",
    responses={
        400: {"description": "Nothing to update"},
        404: {"description": "User not found"},
        500: {"description": "Database error"},
    },
)
def update_my_settings(
    service: UserServiceDep,
    current_user: CurrentUser,
    settings_in: UserSettingsUpdate,
) -> User:
    """Update the **theme** and the **profile visibility** of your account.

    🔒 Authentication required

    **Behaviour:** only the fields you send are changed, the others
    keep their current value.

    **Available settings:**

    - 🎨 `theme`: `day` or `night`
    - 👁️ `profile_visibility`: `public` or `private`

    **Use cases:**

    - Switch the app to night mode
    - Mark your profile as private

    **Example request:**

    ```json
    {
      "theme": "night"
    }
    ```
    \f
    :param service: User service dependency
    :param current_user: The current authenticated user
    :param settings_in: New settings
    :raises HTTPException: 400 if there is nothing to update,
        404 if the user is not found, 500 on database error
    :return: The updated user, with their settings
    """
    try:
        return service.update_settings(current_user.id_user, settings_in)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nothing to update.",
        ) from None
    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        ) from None
    except DAOError:
        logger.exception(
            "Failed to update settings of user %s",
            current_user.id_user,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not update the settings.",
        ) from None


@router.get(
    "/me/quests",
    status_code=status.HTTP_200_OK,
    summary="🏆 Get my quests",
    responses={500: {"description": "Database error"}},
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
    """List **your quests** with your progress on each of them.

    🔒 Authentication required

    **Filter:** `status` selects the quests to return.

    - 📋 `all` (default): every quest
    - ⏳ `active`: quests **not completed** yet
    - ✅ `completed`: quests you **finished**

    **Returns, for each quest:** its category, your `current` value,
    the `target` to reach, the `progress_percentage` and the
    `reward_xp`.

    **Good to know:** progress is computed from your activity: books
    finished, categories explored, users followed and favorites.
    \f
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
    summary="🔍 Search users",
    responses={500: {"description": "Database error"}},
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
    """Find users whose **username contains** the text you type.

    🔒 Authentication required

    **Parameters:**

    - 🔤 `username`: text to look for, 1 to 30 characters
    - 🔢 `limit`: number of users to return, from 1 to 50 (default 10)

    **Behaviour:** the search **ignores upper and lower case**, and
    the results are sorted by username.

    **Use case:** find a friend in order to follow them.
    \f
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
    summary="➕ Follow a user",
    responses={
        400: {"description": "You cannot follow yourself"},
        404: {"description": "User not found"},
        409: {"description": "Already following this user"},
        500: {"description": "Database error"},
    },
)
def follow_user(
    service: UserServiceDep,
    current_user: CurrentUser,
    user_id: int,
) -> None:
    """Start **following** another user.

    🔒 Authentication required

    **Rules:**

    - You cannot follow **yourself**
    - You cannot follow the same user **twice**

    **Good to know:** following a user lets you see their **reading
    statistics**.

    **Response:** `204 No Content`, with an empty body.
    \f
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
    summary="➖ Unfollow a user",
    responses={
        400: {"description": "You cannot unfollow yourself"},
        404: {"description": "User not found, or not followed"},
        500: {"description": "Database error"},
    },
)
def unfollow_user(
    service: UserServiceDep,
    current_user: CurrentUser,
    user_id: int,
) -> None:
    """Stop **following** a user.

    🔒 Authentication required

    **Rule:** you must **currently follow** this user.

    **Good to know:** you lose access to their **reading
    statistics**.

    **Response:** `204 No Content`, with an empty body.
    \f
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
    summary="👥 List the followers of a user",
    responses={
        404: {"description": "User not found"},
        500: {"description": "Database error"},
    },
)
def get_followers(
    service: UserServiceDep,
    _current_user: CurrentUser,
    user_id: int,
) -> list[User]:
    """List the users who **follow** a given user.

    🔒 Authentication required

    **Behaviour:** the **most recent** followers come first.

    **Good to know:** use your own user ID to see **your**
    followers. The list is **empty** when nobody follows the user.
    \f
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
    summary="👥 List the users followed by a user",
    responses={
        404: {"description": "User not found"},
        500: {"description": "Database error"},
    },
)
def get_following(
    service: UserServiceDep,
    _current_user: CurrentUser,
    user_id: int,
) -> list[User]:
    """List the users that a given user **is following**.

    🔒 Authentication required

    **Behaviour:** the **most recently followed** users come first.

    **Good to know:** use your own user ID to see who **you**
    follow. The list is **empty** when the user follows nobody.
    \f
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


@router.patch(
    "/me",
    response_model=UserRead,
    summary="✏️ Update my profile",
    responses={
        400: {"description": "Nothing to update"},
        404: {"description": "User not found"},
        409: {"description": "Username or email already used"},
    },
)
def update_self(
    cursor: CursorDep,
    current_user: CurrentUser,
    user_in: UserUpdate,
) -> User:
    """Update the **profile** of your account.

    🔒 Authentication required

    **Behaviour:** only the fields you send are changed, the others
    keep their current value.

    **Available fields:**

    - 👤 `username`: 3 to 30 characters, must be **unique**
    - 📧 `email`: a valid address, must be **unique**
    - 📝 `bio`: a short text about you
    - 🖼️ `profile_picture`: link to your picture

    **Example request:**

    ```json
    {
      "bio": "Fantasy and science fiction reader."
    }
    ```
    \f
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


@router.put(
    "/me/password",
    response_model=UserRead,
    summary="🔑 Change my password",
    responses={
        400: {"description": "New password is the same as the current one"},
        403: {"description": "Wrong current password"},
        404: {"description": "User not found"},
    },
)
def update_self_password(
    cursor: CursorDep,
    current_user: CurrentUser,
    user_in: UserUpdatePassword,
) -> User:
    """Change the **password** of your account.

    🔒 Authentication required

    **Fields:**

    - 🔐 `current_password`: your password today, to prove it is you
    - 🔑 `new_password`: 8 to 72 characters

    **Rule:** the new password must be **different** from the
    current one.

    **Example request:**

    ```json
    {
      "current_password": "my-old-password",
      "new_password": "my-new-password"
    }
    ```
    \f
    :param cursor: Database cursor dependency
    :param current_user: The current authenticated user
    :param user_in: Password update data
    :raises HTTPException: 400 if the new password is the same as the
        current one, 403 if the current password is wrong,
        404 if the user is not found
    :return: The updated User object
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


@router.get(
    "/{user_id}/library",
    summary="📚 See the library of a user",
    responses={
        404: {"description": "User not found"},
        500: {"description": "Database error"},
    },
)
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
    """List the books of **another user's library**.

    🔒 Authentication required

    **Filter:** `status` keeps only the books in one reading status
    (`WANT_TO_READ`, `READING` or `COMPLETED`). Without it, **all**
    the books are returned.

    **Good to know:** every logged-in user can see the library of
    **any user**, even without following them.
    \f
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


@router.get(
    "/{user_id}/playlists",
    summary="🎵 See the playlists of a user",
    responses={
        404: {"description": "User not found"},
        500: {"description": "Database error"},
    },
)
def get_user_playlists(
    user_service: UserServiceDep,
    playlist_service: PlaylistServiceDep,
    _current_user: CurrentUser,
    user_id: int,
) -> list[PlaylistRead]:
    """List the **playlists of another user**, in creation order.

    🔒 Authentication required

    **Returns:** the ID and the name of each playlist, without its
    books.

    **Good to know:** every logged-in user can see the playlists of
    **any user**, even without following them.
    \f
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


@router.get(
    "/me/stats",
    summary="📊 Get my reading statistics",
    responses={500: {"description": "Database error"}},
)
def read_my_stats(
    service: StatsServiceDep,
    current_user: CurrentUser,
) -> UserStats:
    """Return **your reading statistics**.

    🔒 Authentication required

    **Returns:**

    - ✅ `books_finished`: number of books you **completed**
    - 🏷️ `genres`: number of books of your library **per category**
    - ⭐ `ratings`: number of your reviews **per rating**

    **Example response:**

    ```json
    {
      "books_finished": 12,
      "genres": [
        {"category": "Fantasy", "count": 7},
        {"category": "Science Fiction", "count": 5}
      ],
      "ratings": [
        {"rating": 4, "count": 3},
        {"rating": 5, "count": 6}
      ]
    }
    ```
    \f
    :param service: Statistics service dependency
    :param current_user: The authenticated user
    :raises HTTPException: 500 on database error
    :return: The user's statistics
    """
    try:
        return service.get_stats(current_user.id_user)
    except DAOError:
        logger.exception(
            "Failed to compute the stats of user %s",
            current_user.id_user,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not compute the statistics.",
        ) from None


@router.get(
    "/{user_id}/stats",
    summary="📊 See the reading statistics of a friend",
    responses={
        403: {"description": "You must follow this user"},
        404: {"description": "User not found"},
        500: {"description": "Database error"},
    },
)
def get_user_stats(
    user_id: int,
    current_user: CurrentUser,
    user_service: UserServiceDep,
    stats_service: StatsServiceDep,
) -> UserStats:
    """Return the **reading statistics** of a user you follow.

    🔒 Authentication required, **followers only**

    **Rule:** you must **follow** this user, otherwise the access is
    refused.

    **Returns:**

    - ✅ `books_finished`: number of books they **completed**
    - 🏷️ `genres`: number of books of their library **per category**
    - ⭐ `ratings`: number of their reviews **per rating**
    \f
    :param user_id: ID of the user whose stats are being requested
    :param current_user: The authenticated user making the request
    :param user_service: The user service to check if the target user exists
    :param stats_service: The stats service to retrieve reading statistics
    :raises HTTPException: If the user is not found, not followed,
     or on DB error
    :return: The target user's reading statistics
    """
    try:
        # 1. Vérifier que l'utilisateur cible existe
        user_service.read(user_id=user_id)

        # 2. Vérifier que l'utilisateur courant suit bien l'utilisateur cible
        following = user_service.get_following(current_user.id_user)
        is_following = any(user.id_user == user_id for user in following)

        if not is_following:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You must follow this user to view their stats.",
            )

        # 3. Récupérer et renvoyer les statistiques
        return stats_service.get_stats(id_user=user_id)

    except UserNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        ) from exc
    except DAOError as exc:
        logger.exception("Failed to retrieve stats for user %s", user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve statistics.",
        ) from exc
