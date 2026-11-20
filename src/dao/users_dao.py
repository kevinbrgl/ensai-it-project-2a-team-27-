"""Database access for accounts, preferences and moderation."""

from datetime import datetime

from psycopg2 import Error as DBError
from psycopg2.errors import UniqueViolation
from psycopg2.extras import RealDictCursor

from src.dao.follows_dao import FollowDAO
from src.models.users import (
    User,
    UserCreate,
    UserSettingsUpdate,
    UserUpdateFull,
)
from src.utils.exceptions import (
    DAOError,
    EmailAlreadyExistsError,
    UserAlreadyExistsError,
)


class UserDAO:
    """Manage user profiles, preferences, moderation, and follows.

    Attributes
    ----------
    cur : RealDictCursor
        PostgreSQL cursor that fetches rows as dictionaries.

    """

    def __init__(self, cursor: RealDictCursor) -> None:
        """Initialize UserDAO with a database cursor.

        Parameters
        ----------
        cursor : RealDictCursor
            Database cursor that yields rows as dictionaries.

        """
        self.cur = cursor
        self.follows = FollowDAO(cursor)

    def create(self, user_create: UserCreate) -> User:
        """Create a new user in the database.

        Parameters
        ----------
        user_create : UserCreate
            Username, email address, and password hash for the new user.

        Returns
        -------
        User
            The created User object.

        Raises
        ------
        UserAlreadyExistsError
            If the username already exists.
        EmailAlreadyExistsError
            If the email already exists.
        DAOError
            If the insertion fails or a database error occurs.

        """
        try:
            self.cur.execute(
                """
                INSERT INTO users (username, email, password_hash)
                VALUES (%(username)s, %(email)s, %(password_hash)s)
                RETURNING *
                """,
                user_create.model_dump(),
            )
            row = self.cur.fetchone()
        except UniqueViolation as exc:
            if exc.diag.constraint_name == "users_email_key":
                raise EmailAlreadyExistsError(user_create.email) from exc
            raise UserAlreadyExistsError(user_create.username) from exc
        except DBError as exc:
            raise DAOError from exc

        if row is None:
            msg = "User registration failed"
            raise DAOError(msg)
        return User(**row)

    def read(self, user_id: int) -> User | None:
        """Read a user by their ID.

        Parameters
        ----------
        user_id : int
            ID of the user to read.

        Returns
        -------
        User | None
            The matching user, or None if absent.

        Raises
        ------
        DAOError
            If a database error occurs.

        """
        try:
            self.cur.execute(
                """
                SELECT id_user, username, email, password_hash,
                       bio, profile_picture, theme, profile_visibility,
                       is_admin, is_banned, suspended_until
                FROM users
                WHERE id_user = %s
                """,
                (user_id,),
            )
            row = self.cur.fetchone()
        except DBError as exc:
            raise DAOError from exc
        return User(**row) if row else None

    def read_by_username(self, username: str) -> User | None:
        """Read a user by their username.

        Parameters
        ----------
        username : str
            Username of the user to read.

        Returns
        -------
        User | None
            The matching user, or None if absent.

        Raises
        ------
        DAOError
            If a database error occurs.

        """
        try:
            self.cur.execute(
                """
                SELECT id_user, username, email, password_hash,
                       bio, profile_picture, theme, profile_visibility,
                       is_admin, is_banned, suspended_until
                FROM users
                WHERE username = %s
                """,
                (username,),
            )
            row = self.cur.fetchone()
        except DBError as exc:
            raise DAOError from exc
        return User(**row) if row else None

    def read_by_email(self, email: str) -> User | None:
        """Find a user by their email address.

        Parameters
        ----------
        email : str
            Email of the user to read.

        Returns
        -------
        User | None
            The matching user, or None if absent.

        Raises
        ------
        DAOError
            If a database error occurs.

        """
        try:
            self.cur.execute(
                """
                SELECT id_user, username, email, password_hash,
                       bio, profile_picture, theme, profile_visibility,
                       is_admin, is_banned, suspended_until
                FROM users
                WHERE email = %s
                """,
                (email,),
            )
            row = self.cur.fetchone()
        except DBError as exc:
            raise DAOError from exc
        return User(**row) if row else None

    def search_by_username(
        self,
        username: str,
        limit: int = 10,
    ) -> list[User]:
        """Find users by a case-insensitive username substring.

        Parameters
        ----------
        username : str
            Substring to search in usernames.
        limit : int, optional
            Maximum number of users to return. Defaults to 10.

        Returns
        -------
        list[User]
            List of matching User objects ordered by username.

        Raises
        ------
        DAOError
            If a database error occurs.

        """
        try:
            self.cur.execute(
                """
                SELECT id_user, username, email, password_hash,
                       bio, profile_picture
                FROM users
                WHERE username ILIKE %s
                ORDER BY username ASC
                LIMIT %s
                """,
                (f"%{username}%", limit),
            )
            rows = self.cur.fetchall()
        except DBError as exc:
            raise DAOError from exc
        return [User(**row) for row in rows]

    def add_follow(self, follower_id: int, following_id: int) -> None:
        """Follow a reader using the current user transaction."""
        self.follows.add_follow(follower_id, following_id)

    def remove_follow(self, follower_id: int, following_id: int) -> None:
        """Remove an existing follow relationship."""
        self.follows.remove_follow(follower_id, following_id)

    def is_following(self, follower_id: int, following_id: int) -> bool:
        """Check whether the first reader follows the second."""
        return self.follows.is_following(follower_id, following_id)

    def get_followers(self, user_id: int) -> list[User]:
        """List the reader's followers, most recent first."""
        return self.follows.get_followers(user_id)

    def get_following(self, user_id: int) -> list[User]:
        """List the readers this user follows, most recent first."""
        return self.follows.get_following(user_id)

    def update(self, user_id: int, user_in: UserUpdateFull) -> User | None:
        """Update a user by their ID.

        Parameters
        ----------
        user_id : int
            ID of the user to update.
        user_in : UserUpdateFull
            Fields to update on the user record.

        Returns
        -------
        User | None
            The updated user, or None if the ID is unknown.

        Raises
        ------
        ValueError
            If all supplied fields are None or no fields were supplied.
        UserAlreadyExistsError
            If the new username is already used.
        EmailAlreadyExistsError
            If the new email is already used.
        DAOError
            If a database error occurs.

        """
        data = user_in.model_dump(exclude_unset=True)

        if all(v is None for v in data.values()):
            msg = "Nothing to update."
            raise ValueError(msg)

        set_clause = ", ".join(f"{key} = %s" for key in data)
        values = [*data.values(), user_id]

        try:
            self.cur.execute(
                f"""
                UPDATE users
                SET {set_clause}
                WHERE id_user = %s
                RETURNING *
                """,  # ruff: ignore[hardcoded-sql-expression]
                values,
            )
            row = self.cur.fetchone()
        except UniqueViolation as exc:
            if exc.diag.constraint_name == "users_email_key":
                raise EmailAlreadyExistsError(str(user_in.email)) from exc
            raise UserAlreadyExistsError(str(user_in.username)) from exc
        except DBError as exc:
            raise DAOError from exc
        return User(**row) if row else None

    def update_settings(
        self,
        user_id: int,
        settings_in: UserSettingsUpdate,
    ) -> User | None:
        """Update a user's theme, profile visibility, or both.

        A setting supplied as None keeps its current value.

        Parameters
        ----------
        user_id : int
            ID of the user.
        settings_in : UserSettingsUpdate
            Theme and profile visibility values to apply.

        Returns
        -------
        User | None
            The user with updated settings, or None if the ID is unknown.

        Raises
        ------
        DAOError
            If a database error occurs.

        """
        try:
            self.cur.execute(
                """
                UPDATE users
                SET theme = COALESCE(%s, theme),
                    profile_visibility = COALESCE(%s, profile_visibility)
                WHERE id_user = %s
                RETURNING *
                """,
                (
                    settings_in.theme,
                    settings_in.profile_visibility,
                    user_id,
                ),
            )
            row = self.cur.fetchone()
        except DBError as exc:
            raise DAOError from exc
        return User(**row) if row else None

    def set_suspended_until(
        self,
        user_id: int,
        until: datetime | None,
    ) -> User | None:
        """Set or clear a user suspension.

        Parameters
        ----------
        user_id : int
            ID of the user.
        until : datetime | None
            Date and time the suspension ends, or None to lift it.

        Returns
        -------
        User | None
            The user with an updated suspension, or None if the ID is unknown.

        Raises
        ------
        DAOError
            If a database error occurs.

        """
        try:
            self.cur.execute(
                """
                UPDATE users
                SET suspended_until = %s
                WHERE id_user = %s
                RETURNING *
                """,
                (until, user_id),
            )
            row = self.cur.fetchone()
        except DBError as exc:
            raise DAOError from exc
        return User(**row) if row else None

    def set_banned(self, user_id: int, *, banned: bool) -> User | None:
        """Ban or unban a user.

        Parameters
        ----------
        user_id : int
            ID of the user.
        banned : bool
            True to ban the user or False to lift the ban.

        Returns
        -------
        User | None
            The user with an updated ban status, or None if the ID is unknown.

        Raises
        ------
        DAOError
            If a database error occurs.

        """
        try:
            self.cur.execute(
                """
                UPDATE users
                SET is_banned = %s
                WHERE id_user = %s
                RETURNING *
                """,
                (banned, user_id),
            )
            row = self.cur.fetchone()
        except DBError as exc:
            raise DAOError from exc
        return User(**row) if row else None
