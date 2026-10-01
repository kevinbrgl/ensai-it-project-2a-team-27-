

"""Data Access Object for user operations.

This module provides CRUD operations for users in the database.
All database errors are wrapped in DAOError or UserAlreadyExistsError.
"""
from psycopg2 import Error as DBError
from psycopg2.errors import UniqueViolation
from psycopg2.extras import RealDictCursor

from src.models import User, UserCreate, UserUpdateFull
from src.utils.exceptions import DAOError, UserAlreadyExistsError


class UserDAO:
    """DAO class for user CRUD operations.

    :attr cursor: Database cursor
    """

    def __init__(self, cursor: RealDictCursor) -> None:
        """Initialize UserDAO with a database cursor.

        :param cursor: Database cursor
        """
        self.cur = cursor

    def create(self, user_create: UserCreate) -> User:
        """Create a new user in the database.

        :param user_create: Data for user creation
        :raises DAOError: Raised if user creation fails or DB error occurs
        :raises UserAlreadyExistsError: Raised if username already exists
        :return: The created User object
        """
        try:
            self.cur.execute(
                """
                INSERT INTO users
                    (username, first_name, last_name, hashed_password)
                VALUES
                    (%(username)s, %(first_name)s, %(last_name)s,
                    %(hashed_password)s)
                RETURNING *
                """,
                user_create.model_dump(),
            )
            row = self.cur.fetchone()
            if row is None:
                msg = "User registration failed"
                raise DAOError(msg)
            return User(**row)
        except UniqueViolation as exc:
            raise UserAlreadyExistsError(user_create.username) from exc
        except DBError as exc:
            raise DAOError from exc

    def read(self, user_id: int) -> User | None:
        """Read a user by their ID.

        :param user_id: ID of the user to read
        :raises DAOError: Raised if DB error occurs
        :return: The User object or None if not found
        """
        try:
            self.cur.execute(
                """
                SELECT id, username, first_name, last_name, hashed_password
                FROM users
                WHERE id = %s
                """,
                (user_id,),
            )
            row = self.cur.fetchone()
            return User(**row) if row else None
        except DBError as exc:
            raise DAOError from exc

    def read_by_username(self, username: str) -> User | None:
        """Read a user by their username.

        :param username: Username of the user to read
        :raises DAOError: Raised if DB error occurs
        :return: The User object or None if not found
        """
        try:
            self.cur.execute(
                """
                SELECT id, username, first_name, last_name, hashed_password
                FROM users
                WHERE username = %s
                """,
                (username,),
            )
            row = self.cur.fetchone()
            return User(**row) if row else None
        except DBError as exc:
            raise DAOError from exc

    def update(self, user_id: int, user_in: UserUpdateFull) -> User | None:
        """Update a user by their ID.

        :param user_id: ID of the user to update
        :param user_in: Data for user update
        :raises ValueError: Raised if no data to update
        :raises DAOError: Raised if DB error occurs
        :return: The updated User object or None if not found
        """
        data = user_in.model_dump(exclude_unset=True)

        if all(v is None for v in data.values()):
            msg = "Nothing to update."
            raise ValueError(msg)

        set_clause = ", ".join(f"{key} = %s" for key in data)
        values = [*list(data.values()), user_id]

        try:
            self.cur.execute(
                f"""
                UPDATE users
                SET {set_clause}
                WHERE id = %s
                RETURNING *
                """,  # noqa: S608
                values,
            )
            row = self.cur.fetchone()
            return User(**row) if row else None

        except DBError as exc:
            raise DAOError from exc
