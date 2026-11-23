"""Routes for user operations in the FastAPI application.

Provides endpoints for profile reading, search, follow, unfollow,
followers, following, quests, achievements, genre wheel, settings, and updates.
Registration is handled in auth_routes.py.
"""

import logging
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, status

from src.api.deps import (
    AchievementServiceDep,
    CurrentUser,
    GenreWheelServiceDep,
    LibraryServiceDep,
    PlaylistServiceDep,
    QuestServiceDep,
    StatsServiceDep,
    UserServiceDep,
)
from src.models import (
    Achievement,
    GenreWheel,
    Quest,
    User,
    UserRead,
    UserUpdate,
    UserUpdatePassword,
)
from src.models.library import LibraryBookDetails
from src.models.playlists import PlaylistRead
from src.models.stats import UserStats
from src.models.users import (
    UserMe,
    UserPublic,
    UserSearchParams,
    UserSearchResult,
    UserSettingsUpdate,
)
from src.services.users_service import UserService
from src.utils.exceptions import (
    AlreadyFollowingError,
    DAOError,
    EmailAlreadyExistsError,
    IncorrectPasswordError,
    NotFollowingError,
    PrivateProfileError,
    SamePasswordError,
    SelfFollowError,
    SelfUnfollowError,
    UserAlreadyExistsError,
    UserNotFoundError,
)

router = APIRouter(prefix="/users", tags=["Users"])
logger = logging.getLogger(__name__)

PRIVATE_PROFILE = "This profile is private."


@router.get("/me", response_model=UserRead, summary="👤 Get my profile")
def read_self(current_user: CurrentUser) -> User:
    """Return the **public profile** of your own account.

    🔒 Authentication required

    **Returns:** your ID, username, email, bio and profile picture.

    **Good to know:** the password is **never** returned. For your
    theme and visibility, use the settings route.
    \f

    Parameters
    ----------
    current_user : User
        The current authenticated user.

    Returns
    -------
    User
        Account data for the authenticated user.

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

    Parameters
    ----------
    current_user : User
        The current authenticated user.

    Returns
    -------
    User
        The user information and settings.

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

    Parameters
    ----------
    service : UserService
        User service dependency.
    current_user : User
        The current authenticated user.
    settings_in : UserSettingsUpdate
        Theme and profile visibility to update.

    Returns
    -------
    User
        The updated user, with their settings.

    Raises
    ------
    HTTPException
        400 if there is nothing to update, 404 if the user is not found, 500 on
        database error.

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

    Parameters
    ----------
    service : QuestService
        Quest service dependency.
    current_user : User
        Authenticated user making the request.
    status_filter : {'all', 'active', 'completed'}, optional
        Completion status to filter by. Defaults to 'all'.

    Returns
    -------
    list[Quest]
        Quests with their calculated progress.

    Raises
    ------
    HTTPException
        500 on database error.

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
    "/me/achievements",
    status_code=status.HTTP_200_OK,
    summary="🏅 Get my achievements",
    responses={500: {"description": "Database error"}},
)
def get_my_achievements(
    service: AchievementServiceDep,
    current_user: CurrentUser,
    status_filter: Annotated[
        Literal["all", "unlocked", "locked"],
        Query(
            alias="status",
            description=("Filter achievements ('all', 'unlocked', 'locked')"),
        ),
    ] = "all",
) -> list[Achievement]:
    """List **your achievements** and trophies (unlocked and locked).

    🔒 Authentication required

    **Filter:** `status` selects which achievements to return.

    - 📋 `all` (default): every milestone (unlocked and locked)
    - 🏆 `unlocked`: achievements you have **unlocked**
    - 🔒 `locked`: achievements **not yet reached**

    **Returns, for each achievement:** category, tier (Bronze, Silver, Gold,
    Platinum), visual icon, current progress, target, and unlock status.
    \f

    Parameters
    ----------
    service : AchievementService
        Achievement service dependency.
    current_user : User
        Authenticated user making the request.
    status_filter : {'all', 'unlocked', 'locked'}, optional
        Unlock status to filter by. Defaults to 'all'.

    Returns
    -------
    list[Achievement]
        Achievements with their progress and unlock status.

    Raises
    ------
    HTTPException
        500 on database error.

    """
    try:
        return service.get_achievements(
            user_id=current_user.id_user,
            status_filter=status_filter,
        )
    except DAOError:
        logger.exception(
            "Failed to retrieve achievements for user %s",
            current_user.id_user,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve achievements.",
        ) from None


def _reader_previews(
    matches: list[User], viewer_id: int, wheel_service: GenreWheelServiceDep,
    *, include: bool,
) -> list[UserSearchResult]:
    """Attach genre wheels visible to the viewer when requested."""
    wheels = {}
    if include:
        visible_ids = [
            user.id_user for user in matches
            if UserService.is_profile_visible(user, viewer_id)
        ]
        wheels = wheel_service.get_genre_wheels(visible_ids)
    results = [
        UserSearchResult.model_validate(user, from_attributes=True)
        for user in matches
    ]
    for profile in results:
        if profile.id_user in wheels:
            profile.genre_wheel = wheels[profile.id_user]
    return results


@router.get(
    "/search",
    response_model_exclude_unset=True,
    status_code=status.HTTP_200_OK,
    summary="🔍 Search users",
    responses={500: {"description": "Database error"}},
)
def search_users(
    service: UserServiceDep,
    current_user: CurrentUser,
    wheel_service: GenreWheelServiceDep,
    query: Annotated[UserSearchParams, Query()],
) -> list[UserSearchResult]:
    """Find users whose **username contains** the text you type.

    🔒 Authentication required

    **Parameters:**

    - 🔤 `username`: text to look for, 1 to 30 characters
    - 🔢 `limit`: number of users to return, from 1 to 50 (default 10)
    - 🎨 `include_genre_wheel`: include the wheels visible to you

    **Behaviour:** the search **ignores upper and lower case**, and
    the results are sorted by username.

    **Use case:** find a friend in order to follow them.
    \f

    Parameters
    ----------
    service : UserService
        User service dependency.
    current_user : User
        The authenticated user making the request.
    wheel_service : GenreWheelService
        Loads visible readers' wheels in one batch.
    query : UserSearchParams
        Username substring, result limit and wheel preview selection.

    Returns
    -------
    list[UserSearchResult]
        Public profiles with any requested, visible wheels.

    Raises
    ------
    HTTPException
        500 on database error.

    """
    try:
        matches = service.search_users(
            username=query.username, limit=query.limit,
        )
        return _reader_previews(
            matches, current_user.id_user, wheel_service,
            include=query.include_genre_wheel,
        )
    except DAOError:
        logger.exception(
            "Failed to search users with query: %s", query.username,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not search users.",
        ) from None


# Declared after /me and /search, so that it does not shadow them.
@router.get(
    "/{user_id}",
    response_model=UserPublic,
    status_code=status.HTTP_200_OK,
    summary="👤 See the profile of a user",
    responses={
        404: {"description": "User not found"},
        500: {"description": "Database error"},
    },
)
def read_user(
    service: UserServiceDep,
    _current_user: CurrentUser,
    user_id: int,
) -> User:
    """Return the **public profile** of any user.

    🔒 Authentication required

    **Returns:** their ID, username, bio, profile picture and profile
    visibility (`public` or `private`).

    **Good to know:** the email address, the password and the other
    settings are **never** returned. A private profile still shows
    this card, so the user can be found and followed.
    \f

    Parameters
    ----------
    service : UserService
        User service dependency.
    _current_user : User
        Authenticated user making the request.
    user_id : int
        ID of the user whose profile to retrieve.

    Returns
    -------
    User
        Account data for the requested user.

    Raises
    ------
    HTTPException
        404 if the user is not found, 500 on database error.

    """
    try:
        return service.read(user_id)
    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        ) from None
    except DAOError:
        logger.exception("Failed to read the profile of user %s", user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve the user.",
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

    Parameters
    ----------
    service : UserService
        User service dependency.
    current_user : User
        Authenticated user starting the follow.
    user_id : int
        ID of the user to follow (following).

    Raises
    ------
    HTTPException
        400 if user attempts to follow themselves, 404 if target user is not
        found, 409 if already following, 500 on database error.

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

    Parameters
    ----------
    service : UserService
        User service dependency.
    current_user : User
        Authenticated user ending the follow.
    user_id : int
        ID of the user to unfollow (following).

    Raises
    ------
    HTTPException
        400 if user attempts to unfollow themselves, 404 if target user is not
        found or not currently followed, 500 on database error.

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
    response_model_exclude_unset=True,
    status_code=status.HTTP_200_OK,
    summary="👥 List the followers of a user",
    responses={
        404: {"description": "User not found"},
        500: {"description": "Database error"},
    },
)
def get_followers(
    service: UserServiceDep,
    current_user: CurrentUser,
    user_id: int,
    wheel_service: GenreWheelServiceDep,
    *,
    include_genre_wheel: bool = False,
) -> list[UserSearchResult]:
    """List the users who **follow** a given user.

    🔒 Authentication required

    **Behaviour:** the **most recent** followers come first.

    **Good to know:** use your own user ID to see **your**
    followers. The list is **empty** when nobody follows the user.
    \f

    Parameters
    ----------
    service : UserService
        User service dependency.
    wheel_service : GenreWheelService
        Loads visible genre wheels.
    include_genre_wheel : bool
        Include genre wheels in the list.
    current_user : User
        Authenticated user making the request.
    user_id : int
        ID of the user whose followers to retrieve.

    Returns
    -------
    list[UserSearchResult]
        List of followers.

    Raises
    ------
    HTTPException
        404 if the user is not found, 500 on database error.

    """
    try:
        return _reader_previews(
            service.get_followers(user_id),
            current_user.id_user,
            wheel_service,
            include=include_genre_wheel,
        )
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
    response_model_exclude_unset=True,
    status_code=status.HTTP_200_OK,
    summary="👥 List the users followed by a user",
    responses={
        404: {"description": "User not found"},
        500: {"description": "Database error"},
    },
)
def get_following(
    service: UserServiceDep,
    current_user: CurrentUser,
    user_id: int,
    wheel_service: GenreWheelServiceDep,
    *,
    include_genre_wheel: bool = False,
) -> list[UserSearchResult]:
    """List the users that a given user **is following**.

    🔒 Authentication required

    **Behaviour:** the **most recently followed** users come first.

    **Good to know:** use your own user ID to see who **you**
    follow. The list is **empty** when the user follows nobody.
    \f

    Parameters
    ----------
    service : UserService
        User service dependency.
    wheel_service : GenreWheelService
        Loads visible genre wheels.
    include_genre_wheel : bool
        Include genre wheels in the list.
    current_user : User
        Authenticated user making the request.
    user_id : int
        ID of the user whose followed users to retrieve.

    Returns
    -------
    list[UserSearchResult]
        List of followed users.

    Raises
    ------
    HTTPException
        404 if the user is not found, 500 on database error.

    """
    try:
        return _reader_previews(
            service.get_following(user_id),
            current_user.id_user,
            wheel_service,
            include=include_genre_wheel,
        )
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
        500: {"description": "Database error"},
    },
)
def update_self(
    service: UserServiceDep,
    current_user: CurrentUser,
    user_in: UserUpdate,
) -> User:
    """Update the **profile** of your account.

    🔒 Authentication required

    **Behaviour:** only the fields you send are changed, the others
    keep their current value.

    **Available fields:**

    - 👤 `username`: 3 to 30 characters, must be **unique**
    - 📧 `email`: a valid address of at most 100 characters, must be
      **unique**
    - 📝 `bio`: a short text about you
    - 🖼️ `profile_picture`: link to your picture, at most 255 characters

    `username` and `email` cannot be set to `null`.

    **Example request:**

    ```json
    {
      "bio": "Fantasy and science fiction reader."
    }
    ```
    \f

    Parameters
    ----------
    service : UserService
        User service dependency.
    current_user : User
        The current authenticated user.
    user_in : UserUpdate
        Profile fields to update.

    Returns
    -------
    User
        Account data with the requested profile changes.

    Raises
    ------
    HTTPException
        400 if there is nothing to update, 404 if the user is not found, 409 if
        the new username or email is already used, 500 on database error.

    """
    try:
        return service.update(current_user.id_user, user_in)
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
    except DAOError:
        logger.exception(
            "Failed to update the profile of user %s",
            current_user.id_user,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not update the profile.",
        ) from None


@router.put(
    "/me/password",
    response_model=UserRead,
    summary="🔑 Change my password",
    responses={
        400: {"description": "New password is the same as the current one"},
        403: {"description": "Wrong current password"},
        404: {"description": "User not found"},
        500: {"description": "Database error"},
    },
)
def update_self_password(
    service: UserServiceDep,
    current_user: CurrentUser,
    user_in: UserUpdatePassword,
) -> User:
    """Change the **password** of your account.

    🔒 Authentication required

    **Fields:**

    - 🔐 `current_password`: your password today, to prove it is you
    - 🔑 `new_password`: 8 to 72 characters, and at most 72 bytes
      (accented letters and emoji count as several bytes)

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

    Parameters
    ----------
    service : UserService
        User service dependency.
    current_user : User
        The current authenticated user.
    user_in : UserUpdatePassword
        Current password and requested new password.

    Returns
    -------
    User
        Account data after the password change.

    Raises
    ------
    HTTPException
        400 if the new password is the same as the current one, 403 if the
        current password is wrong, 404 if the user is not found, 500 on
        database error.

    """
    try:
        return service.update_password(current_user, user_in)
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
    except DAOError:
        logger.exception(
            "Failed to change the password of user %s",
            current_user.id_user,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not change the password.",
        ) from None


@router.get(
    "/{user_id}/library",
    summary="📚 See the library of a user",
    responses={
        403: {"description": "This profile is private"},
        404: {"description": "User not found"},
        500: {"description": "Database error"},
    },
)
def get_user_library(
    user_service: UserServiceDep,
    library_service: LibraryServiceDep,
    current_user: CurrentUser,
    user_id: int,
    status_filter: Annotated[
        str | None,
        Query(
            alias="status",
            pattern="^(READING|WANT_TO_READ|COMPLETED|ABANDONED)$",
            description="Filter by reading state",
        ),
    ] = None,
) -> list[LibraryBookDetails]:
    """List the books of **another user's library**.

    🔒 Authentication required

    **Filter:** `status` keeps only the books in one reading status
    (`WANT_TO_READ`, `READING`, `COMPLETED` or `ABANDONED`). Without
    it, **all** the books are returned.

    **Returns:** for each book, its details plus the reading status,
    like, favorite flag and reading dates of the user.

    **Good to know:** every logged-in user can see the library of
    **any public profile**, even without following them. A **private**
    profile only shows its library to its owner.
    \f

    Parameters
    ----------
    user_service : UserService
        User service dependency.
    library_service : LibraryService
        Library service dependency.
    current_user : User
        Authenticated user making the request.
    user_id : int
        ID of the user whose library to retrieve.
    status_filter : str | None, optional
        Reading status to filter by.

    Returns
    -------
    list[LibraryBookDetails]
        The books of the user's library.

    Raises
    ------
    HTTPException
        403 if the profile is private, 404 if the user is not found, 500 on
        database error.

    """
    try:
        target = user_service.read(user_id)
        UserService.ensure_profile_visible(target, current_user.id_user)
        return library_service.list_books(user_id, status_filter)
    except PrivateProfileError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=PRIVATE_PROFILE,
        ) from None
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
        403: {"description": "This profile is private"},
        404: {"description": "User not found"},
        500: {"description": "Database error"},
    },
)
def get_user_playlists(
    user_service: UserServiceDep,
    playlist_service: PlaylistServiceDep,
    current_user: CurrentUser,
    user_id: int,
) -> list[PlaylistRead]:
    """List the **playlists of another user**, in creation order.

    🔒 Authentication required

    **Returns:** the ID and the name of each playlist, without its
    books.

    **Good to know:** every logged-in user can see the playlists of
    **any public profile**, even without following them. A **private**
    profile only shows its playlists to its owner.
    \f

    Parameters
    ----------
    user_service : UserService
        User service dependency.
    playlist_service : PlaylistService
        Playlist service dependency.
    current_user : User
        Authenticated user making the request.
    user_id : int
        ID of the user whose playlists to retrieve.

    Returns
    -------
    list[PlaylistRead]
        The user's playlists, in creation order.

    Raises
    ------
    HTTPException
        403 if the profile is private, 404 if the user is not found, 500 on
        database error.

    """
    try:
        target = user_service.read(user_id)
        UserService.ensure_profile_visible(target, current_user.id_user)
        return playlist_service.list_playlists(user_id)
    except PrivateProfileError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=PRIVATE_PROFILE,
        ) from None
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
    - 📄 `pages_read`: total pages of the books you **completed**
      (a book without a page count counts as 0)
    - 🏷️ `genres`: number of books of your library **per category**
    - ⭐ `ratings`: number of your reviews **per rating**

    **Example response:**

    ```json
    {
      "books_finished": 12,
      "pages_read": 4310,
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

    Parameters
    ----------
    service : StatsService
        Statistics service dependency.
    current_user : User
        The authenticated user.

    Returns
    -------
    UserStats
        The user's statistics.

    Raises
    ------
    HTTPException
        500 on database error.

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
        403: {
            "description": "You must follow this user, or the profile "
            "is private",
        },
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
    refused. A **private** profile never shares its statistics.

    **Returns:**

    - ✅ `books_finished`: number of books they **completed**
    - 📄 `pages_read`: total pages of the books they **completed**
    - 🏷️ `genres`: number of books of their library **per category**
    - ⭐ `ratings`: number of their reviews **per rating**
    \f

    Parameters
    ----------
    user_id : int
        ID of the user whose stats are being requested.
    current_user : User
        The authenticated user making the request.
    user_service : UserService
        Service used to check user existence and follow status.
    stats_service : StatsService
        Service used to retrieve reading statistics.

    Returns
    -------
    UserStats
        The target user's reading statistics.

    Raises
    ------
    HTTPException
        403 if the profile is private or the authenticated user does not
        follow the requested user, 404 if the requested user does not exist,
        or 500 on a database error.

    """
    try:
        target = user_service.read(user_id=user_id)
        UserService.ensure_profile_visible(target, current_user.id_user)

        is_following = any(
            user.id_user == user_id
            for user in user_service.get_following(current_user.id_user)
        )
        if not is_following:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You must follow this user to view their stats.",
            )

        return stats_service.get_stats(id_user=user_id)
    except PrivateProfileError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=PRIVATE_PROFILE,
        ) from None
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


@router.get(
    "/{user_id}/genre-wheel",
    status_code=status.HTTP_200_OK,
    summary="🎨 Get the avatar genre color wheel of a user",
    responses={
        403: {"description": "This profile is private"},
        404: {"description": "User not found"},
        500: {"description": "Database error"},
    },
)
def get_user_genre_wheel(
    user_id: int,
    current_user: CurrentUser,
    user_service: UserServiceDep,
    wheel_service: GenreWheelServiceDep,
) -> GenreWheel:
    """Return the **genre color wheel** data for a user's avatar ring.

    🔒 Authentication required

    Computes weighted proportions for each genre based on completed reads,
    review ratings, and favorite markers. Returns an empty grey state
    when the user has not completed any book yet. A **private** profile
    only shows its wheel to its owner.

    **Returns:**

    - 🎨 `segments`: Ordered list of genres with hex colors and percentages
    - ⚪ `is_empty`: True if no significant reading history is available
    - 🔲 `empty_color`: Neutral fallback color code (#9CA3AF)
    - 📚 `total_books`: Total completed books considered
    \f

    Parameters
    ----------
    user_id : int
        ID of the user whose wheel is requested.
    current_user : User
        Authenticated user making the request.
    user_service : UserService
        Service used to check that the requested user exists.
    wheel_service : GenreWheelService
        Service that calculates the user's genre proportions.

    Returns
    -------
    GenreWheel
        Weighted genre segments and the empty-state color.

    Raises
    ------
    HTTPException
        403 if the profile is private, 404 if user not found, 500 on database
        error.

    """
    try:
        target = user_service.read(user_id=user_id)
        UserService.ensure_profile_visible(target, current_user.id_user)
        return wheel_service.get_genre_wheel(user_id=user_id)
    except PrivateProfileError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=PRIVATE_PROFILE,
        ) from None
    except UserNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        ) from exc
    except DAOError:
        logger.exception(
            "Failed to compute genre wheel for user %s",
            user_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve genre wheel.",
        ) from None
