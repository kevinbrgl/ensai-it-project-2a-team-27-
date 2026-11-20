"""Database access for follow relationships between readers."""

from psycopg2 import Error as DBError
from psycopg2.errors import (
    CheckViolation,
    ForeignKeyViolation,
    UniqueViolation,
)
from psycopg2.extras import RealDictCursor

from src.models.users import User
from src.utils.exceptions import (
    AlreadyFollowingError,
    DAOError,
    NotFollowingError,
    SelfFollowError,
    SelfUnfollowError,
    UserNotFoundError,
)


class FollowDAO:
    """Manage follow relationships using the current request transaction."""

    def __init__(self, cursor: RealDictCursor) -> None:
        """Use the cursor shared with the account queries for this request."""
        self.cur = cursor

    def add_follow(self, follower_id: int, following_id: int) -> None:
        """Add a follow relationship between two users.

        Parameters
        ----------
        follower_id : int
            ID of the follower.
        following_id : int
            ID of the user being followed.

        Raises
        ------
        SelfFollowError
            If a user tries to follow themselves.
        UserNotFoundError
            If either user reference is missing.
        AlreadyFollowingError
            If the follow relationship already exists.
        DAOError
            If a database error occurs.

        """
        if follower_id == following_id:
            raise SelfFollowError
        try:
            self.cur.execute(
                """
                INSERT INTO user_follows (follower_id, following_id)
                VALUES (%s, %s)
                """,
                (follower_id, following_id),
            )
        except UniqueViolation as exc:
            raise AlreadyFollowingError from exc
        except ForeignKeyViolation as exc:
            raise UserNotFoundError(user_id=following_id) from exc
        except CheckViolation as exc:
            raise SelfFollowError from exc
        except DBError as exc:
            raise DAOError from exc

    def remove_follow(self, follower_id: int, following_id: int) -> None:
        """Remove a follow relationship between two users.

        Parameters
        ----------
        follower_id : int
            ID of the follower.
        following_id : int
            ID of the user being unfollowed.

        Raises
        ------
        SelfUnfollowError
            If a user tries to unfollow themselves.
        NotFollowingError
            If the follow relationship is missing.
        DAOError
            If a database error occurs.

        """
        if follower_id == following_id:
            raise SelfUnfollowError
        try:
            self.cur.execute(
                """
                DELETE FROM user_follows
                WHERE follower_id = %s AND following_id = %s
                RETURNING follower_id
                """,
                (follower_id, following_id),
            )
            row = self.cur.fetchone()
        except DBError as exc:
            raise DAOError from exc

        if row is None:
            raise NotFollowingError

    def is_following(self, follower_id: int, following_id: int) -> bool:
        """Check if a user follows another user.

        Parameters
        ----------
        follower_id : int
            ID of the follower.
        following_id : int
            ID of the user being followed.

        Returns
        -------
        bool
            True if the relationship exists, False otherwise.

        Raises
        ------
        DAOError
            If a database error occurs.

        """
        try:
            self.cur.execute(
                """
                SELECT 1
                FROM user_follows
                WHERE follower_id = %s AND following_id = %s
                """,
                (follower_id, following_id),
            )
            return self.cur.fetchone() is not None
        except DBError as exc:
            raise DAOError from exc

    def get_followers(self, user_id: int) -> list[User]:
        """Retrieve all users following the specified user.

        Parameters
        ----------
        user_id : int
            ID of the user whose followers to retrieve.

        Returns
        -------
        list[User]
            Followers ordered by most recent follow, then by user ID.

        Raises
        ------
        DAOError
            If a database error occurs.

        """
        try:
            self.cur.execute(
                """
                SELECT u.id_user, u.username, u.email, u.password_hash,
                       u.bio, u.profile_picture
                FROM users u
                INNER JOIN user_follows uf ON u.id_user = uf.follower_id
                WHERE uf.following_id = %s
                ORDER BY uf.created_at DESC, u.id_user ASC;
                """,
                (user_id,),
            )
            rows = self.cur.fetchall()
        except DBError as exc:
            raise DAOError from exc
        return [User(**row) for row in rows]

    def get_following(self, user_id: int) -> list[User]:
        """Retrieve all users followed by the specified user.

        Parameters
        ----------
        user_id : int
            ID of the user whose followed users to retrieve.

        Returns
        -------
        list[User]
            Followed users ordered by most recent follow, then by user ID.

        Raises
        ------
        DAOError
            If a database error occurs.

        """
        try:
            self.cur.execute(
                """
                SELECT u.id_user, u.username, u.email, u.password_hash,
                       u.bio, u.profile_picture
                FROM users u
                INNER JOIN user_follows uf ON u.id_user = uf.following_id
                WHERE uf.follower_id = %s
                ORDER BY uf.created_at DESC, u.id_user ASC;
                """,
                (user_id,),
            )
            rows = self.cur.fetchall()
        except DBError as exc:
            raise DAOError from exc
        return [User(**row) for row in rows]
