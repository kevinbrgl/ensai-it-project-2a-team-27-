"""Data Access Object for user operations.

This module provides CRUD operations for users in the database.
All database errors are wrapped in DAOError, UserAlreadyExistsError
or EmailAlreadyExistsError.
"""

from psycopg2 import Error as DBError
from psycopg2.errors import UniqueViolation
from psycopg2.extras import RealDictCursor

from src.models.users import User, UserCreate, UserUpdateFull
from src.utils.exceptions import (
    DAOError,
    EmailAlreadyExistsError,
    UserAlreadyExistsError,
)


class UserDAO:
    """DAO class for user CRUD operations.

    :attr cur: Database cursor (RealDictCursor)
    """

    def __init__(self, cursor: RealDictCursor) -> None:
        """Initialize UserDAO with a database cursor.

        :param cursor: Database cursor
        """
        self.cur = cursor

    def create(self, user_create: UserCreate) -> User:
        """Create a new user in the database.

        :param user_create: Data for user creation
        :raises UserAlreadyExistsError: If the username already exists
        :raises EmailAlreadyExistsError: If the email already exists
        :raises DAOError: If the insertion fails or a DB error occurs
        :return: The created User object
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

        :param user_id: ID of the user to read
        :raises DAOError: If a DB error occurs
        :return: The User object or None if not found
        """
        try:
            self.cur.execute(
                """
                SELECT id_user, username, email, password_hash,
                       bio, profile_picture
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

        :param username: Username of the user to read
        :raises DAOError: If a DB error occurs
        :return: The User object or None if not found
        """
        try:
            self.cur.execute(
                """
                SELECT id_user, username, email, password_hash,
                       bio, profile_picture
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
        """Read a user by their email.

        :param email: Email of the user to read
        :raises DAOError: If a DB error occurs
        :return: The User object or None if not found
        """
        try:
            self.cur.execute(
                """
                SELECT id_user, username, email, password_hash,
                       bio, profile_picture
                FROM users
                WHERE email = %s
                """,
                (email,),
            )
            row = self.cur.fetchone()
        except DBError as exc:
            raise DAOError from exc
        return User(**row) if row else None

    def update(self, user_id: int, user_in: UserUpdateFull) -> User | None:
        """Update a user by their ID.

        :param user_id: ID of the user to update
        :param user_in: Data for user update
        :raises ValueError: If there is nothing to update
        :raises UserAlreadyExistsError: If the new username is already used
        :raises EmailAlreadyExistsError: If the new email is already used
        :raises DAOError: If a DB error occurs
        :return: The updated User object or None if not found
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
