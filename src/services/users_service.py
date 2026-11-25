"""Service layer for user operations.

This module provides business logic for user-related operations.
Exceptions are raised for not found, duplicates, authentication,
social actions, password errors, or blocked accounts.
"""

from datetime import UTC, datetime, timedelta

from src.core.config import settings
from src.core.security import (
    create_access_token,
    get_password_hash,
    verify_password,
)
from src.dao.users_dao import UserDAO
from src.models.misc import Token
from src.models.users import (
    User,
    UserCreate,
    UserRegister,
    UserSettingsUpdate,
    UserUpdate,
    UserUpdateFull,
    UserUpdatePassword,
)
from src.utils.exceptions import (
    AccountBannedError,
    AccountSuspendedError,
    AuthError,
    EmailAlreadyExistsError,
    IncorrectPasswordError,
    PrivateProfileError,
    SamePasswordError,
    SelfFollowError,
    SelfUnfollowError,
    UserAlreadyExistsError,
    UserNotFoundError,
)


class UserService:
    """Manage accounts, authentication, and follow relationships.

    Attributes
    ----------
    dao : UserDAO
        Associated UserDAO object.

    """

    def __init__(self, user_dao: UserDAO) -> None:
        """Initialize UserService with a UserDAO.

        Parameters
        ----------
        user_dao : UserDAO
            DAO used to access users.

        """
        self.dao = user_dao

    def authenticate(self, username: str, password: str) -> User:
        """Authenticate a user by username and password.

        Parameters
        ----------
        username : str
            Username of the user.
        password : str
            Password of the user.

        Returns
        -------
        User
            The authenticated User object.

        Raises
        ------
        UserNotFoundError
            If the username does not exist.
        AuthError
            If the password is incorrect.

        """
        db_user = self.dao.read_by_username(username)
        if db_user is None:
            raise UserNotFoundError(username=username)
        if not verify_password(password, db_user.password_hash):
            raise AuthError
        return db_user

    def login(self, username: str, password: str) -> Token:
        """Authenticate a user and create an access token.

        Parameters
        ----------
        username : str
            Username of the user.
        password : str
            Plain password of the user.

        Returns
        -------
        Token
            Token containing the JWT and its type.

        Notes
        -----
        An unknown username raises ``UserNotFoundError`` and an incorrect
        password raises ``AuthError``. A banned account raises
        ``AccountBannedError``. A suspended account raises
        ``AccountSuspendedError``.

        """
        user = self.authenticate(username, password)
        self.ensure_active(user)
        access_token = create_access_token(
            user.id_user,
            expires_delta=timedelta(
                minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
            ),
        )
        return Token(
            access_token=access_token,
            token_type=settings.TOKEN_TYPE,
        )

    def register(self, user_in: UserRegister) -> User:
        """Register a new user.

        Parameters
        ----------
        user_in : UserRegister
            User registration data.

        Returns
        -------
        User
            The created User object.

        Raises
        ------
        UserAlreadyExistsError
            If the username is taken.
        EmailAlreadyExistsError
            If the email is taken.

        """
        if self.dao.read_by_username(user_in.username) is not None:
            raise UserAlreadyExistsError(user_in.username)
        if self.dao.read_by_email(user_in.email) is not None:
            raise EmailAlreadyExistsError(user_in.email)

        user_create = UserCreate(
            username=user_in.username,
            email=user_in.email,
            password_hash=get_password_hash(user_in.password),
        )
        return self.dao.create(user_create)

    def read(self, user_id: int) -> User:
        """Read a user by their ID.

        Parameters
        ----------
        user_id : int
            ID of the user to read.

        Returns
        -------
        User
            The User object.

        Raises
        ------
        UserNotFoundError
            If user is not found.

        """
        user = self.dao.read(user_id)
        if user is None:
            raise UserNotFoundError(user_id=user_id)
        return user

    def read_by_username(self, username: str) -> User:
        """Read a user by their username.

        Parameters
        ----------
        username : str
            Username of the user to read.

        Returns
        -------
        User
            The User object.

        Raises
        ------
        UserNotFoundError
            If user is not found.

        """
        user = self.dao.read_by_username(username)
        if user is None:
            raise UserNotFoundError(username=username)
        return user

    def search_users(self, username: str, limit: int = 10) -> list[User]:
        """Search users whose username matches the query.

        Parameters
        ----------
        username : str
            Query string to match.
        limit : int, optional
            Maximum number of users to return.

        Returns
        -------
        list[User]
            Matching users, or an empty list for a blank query or no matches.

        """
        query = username.strip()
        if not query:
            return []
        return self.dao.search_by_username(query, limit=limit)

    def follow_user(self, follower_id: int, following_id: int) -> None:
        """Follow another user.

        Parameters
        ----------
        follower_id : int
            ID of the follower.
        following_id : int
            ID of the user being followed.

        Raises
        ------
        SelfFollowError
            If a user attempts to follow themselves.
        UserNotFoundError
            If the target user does not exist.

        Notes
        -----
        An existing follow relationship raises ``AlreadyFollowingError``.

        """
        if follower_id == following_id:
            raise SelfFollowError
        if self.dao.read(following_id) is None:
            raise UserNotFoundError(user_id=following_id)
        self.dao.add_follow(follower_id, following_id)

    def unfollow_user(self, follower_id: int, following_id: int) -> None:
        """Unfollow another user.

        Parameters
        ----------
        follower_id : int
            ID of the follower.
        following_id : int
            ID of the user being unfollowed.

        Raises
        ------
        SelfUnfollowError
            If a user attempts to unfollow themselves.
        UserNotFoundError
            If the target user does not exist.

        Notes
        -----
        A missing follow relationship raises ``NotFollowingError``.

        """
        if follower_id == following_id:
            raise SelfUnfollowError
        if self.dao.read(following_id) is None:
            raise UserNotFoundError(user_id=following_id)
        self.dao.remove_follow(follower_id, following_id)

    def get_followers(self, user_id: int) -> list[User]:
        """Get the followers of a user.

        Parameters
        ----------
        user_id : int
            ID of the user whose followers to retrieve.

        Returns
        -------
        list[User]
            List of User objects who follow the user.

        Raises
        ------
        UserNotFoundError
            If the user does not exist.

        """
        if self.dao.read(user_id) is None:
            raise UserNotFoundError(user_id=user_id)
        return self.dao.get_followers(user_id)

    def get_following(self, user_id: int) -> list[User]:
        """Get the users followed by a user.

        Parameters
        ----------
        user_id : int
            ID of the user whose followed users to retrieve.

        Returns
        -------
        list[User]
            List of User objects followed by the user.

        Raises
        ------
        UserNotFoundError
            If the user does not exist.

        """
        if self.dao.read(user_id) is None:
            raise UserNotFoundError(user_id=user_id)
        return self.dao.get_following(user_id)

    def update_password(
        self,
        current_user: User,
        body: UserUpdatePassword,
    ) -> User:
        """Update a user's password.

        Parameters
        ----------
        current_user : User
            The logged-in user.
        body : UserUpdatePassword
            Password update data.

        Returns
        -------
        User
            The updated User object.

        Raises
        ------
        IncorrectPasswordError
            If current password is incorrect.
        SamePasswordError
            If new password is the same as old.
        UserNotFoundError
            If user is not found after update.

        """
        if not verify_password(
            body.current_password,
            current_user.password_hash,
        ):
            raise IncorrectPasswordError
        if body.current_password == body.new_password:
            raise SamePasswordError

        user = self.dao.update(
            current_user.id_user,
            UserUpdateFull(
                password_hash=get_password_hash(body.new_password),
            ),
        )
        if user is None:
            raise UserNotFoundError(user_id=current_user.id_user)
        return user

    def update(self, user_id: int, user_in: UserUpdate) -> User:
        """Update a user's information.

        Parameters
        ----------
        user_id : int
            ID of the user to update.
        user_in : UserUpdate
            User update data.

        Returns
        -------
        User
            The updated User object.

        Raises
        ------
        UserNotFoundError
            If user is not found after update.

        Notes
        -----
        An empty update raises ``ValueError``. A duplicate username raises
        ``UserAlreadyExistsError`` and a duplicate email address raises
        ``EmailAlreadyExistsError``.

        """
        user = self.dao.update(
            user_id,
            UserUpdateFull(**user_in.model_dump(exclude_unset=True)),
        )
        if user is None:
            raise UserNotFoundError(user_id=user_id)
        return user

    @staticmethod
    def ensure_active(user: User) -> None:
        """Check whether an account can be used.

        Parameters
        ----------
        user : User
            The user to check.

        Raises
        ------
        AccountBannedError
            If the account is banned.
        AccountSuspendedError
            If the suspension is still running.

        """
        if user.is_banned:
            raise AccountBannedError
        if (
            user.suspended_until is not None
            and user.suspended_until > datetime.now(UTC)
        ):
            raise AccountSuspendedError(user.suspended_until)

    @staticmethod
    def is_profile_visible(user: User, viewer_id: int) -> bool:
        """Return whether the viewer can see this reader's activity.

        Parameters
        ----------
        user : User
            Reader whose activity is requested.
        viewer_id : int
            Authenticated reader making the request.

        """
        return user.profile_visibility == "public" or user.id_user == viewer_id

    @staticmethod
    def ensure_profile_visible(user: User, viewer_id: int) -> None:
        """Check whether a viewer may see a user's library and activity.

        A private profile only shows its library, playlists, statistics and
        genre wheel to its owner. The username, bio and picture stay
        visible, so the user can still be found and followed.

        Parameters
        ----------
        user : User
            The user whose profile is being viewed.
        viewer_id : int
            ID of the authenticated user viewing the profile.

        Raises
        ------
        PrivateProfileError
            If the profile is private and the viewer is not its owner.

        """
        if not UserService.is_profile_visible(user, viewer_id):
            raise PrivateProfileError

    def update_settings(
        self,
        user_id: int,
        settings_in: UserSettingsUpdate,
    ) -> User:
        """Update a user's theme, profile visibility, or both.

        Parameters
        ----------
        user_id : int
            ID of the user.
        settings_in : UserSettingsUpdate
            New settings.

        Returns
        -------
        User
            The updated User object.

        Raises
        ------
        ValueError
            If no setting is given.
        UserNotFoundError
            If the user does not exist.

        """
        if (
            settings_in.theme is None
            and settings_in.profile_visibility is None
        ):
            msg = "Nothing to update."
            raise ValueError(msg)
        user = self.dao.update_settings(user_id, settings_in)
        if user is None:
            raise UserNotFoundError(user_id=user_id)
        return user
