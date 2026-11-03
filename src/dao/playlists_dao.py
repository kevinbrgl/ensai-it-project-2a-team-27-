"""Data Access Object for playlist operations."""

from psycopg2 import Error as DBError
from psycopg2.errors import UniqueViolation
from psycopg2.extras import RealDictCursor

from src.models.playlists import PlaylistCreate, PlaylistRead, PlaylistUpdate
from src.utils.exceptions import (
    DAOError,
    PlaylistAlreadyExistsError,
    PlaylistNotFoundError,
)


class PlaylistDAO:
    """DAO class for playlist operations."""

    def __init__(self, cursor: RealDictCursor) -> None:
        """Initialize PlaylistDAO with a database cursor.

        :param cursor: Database cursor
        """
        self.cur = cursor

    def create(
        self,
        id_user: int,
        playlist_in: PlaylistCreate,
    ) -> PlaylistRead:
        """Create a playlist for a user.

        :param id_user: ID of the owner of the playlist
        :param playlist_in: Name of the playlist
        :raises PlaylistAlreadyExistsError: If the user already has a
            playlist with this name
        :raises DAOError: If the insertion fails or a DB error occurs
        :return: The created playlist
        """
        try:
            self.cur.execute(
                """
                INSERT INTO playlists (id_user, name)
                VALUES (%s, %s)
                RETURNING id_playlist, id_user, name
                """,
                (id_user, playlist_in.name),
            )
            row = self.cur.fetchone()

        except UniqueViolation:
            raise PlaylistAlreadyExistsError(playlist_in.name) from None
        except DBError as exc:
            raise DAOError from exc

        if row is None:
            msg = "Playlist creation failed"
            raise DAOError(msg)
        return PlaylistRead(**row)

    def find_by_user_id(self, id_user: int) -> list[PlaylistRead]:
        """List the playlists of a user.

        :param id_user: ID of the owner of the playlists
        :raises DAOError: If a DB error occurs
        :return: The playlists in creation order, or an empty list
        """
        try:
            self.cur.execute(
                """
                SELECT id_playlist, id_user, name
                FROM playlists
                WHERE id_user = %s
                ORDER BY id_playlist
                """,
                (id_user,),
            )
            rows = self.cur.fetchall()

        except DBError as exc:
            raise DAOError from exc

        return [PlaylistRead(**row) for row in rows]

    def rename(
        self,
        id_user: int,
        id_playlist: int,
        playlist_in: PlaylistUpdate,
    ) -> PlaylistRead:
        """Rename a playlist owned by a user.

        :param id_user: ID of the owner of the playlist
        :param id_playlist: ID of the playlist to rename
        :param playlist_in: New name of the playlist
        :raises PlaylistNotFoundError: If the playlist does not exist or
            belongs to another user
        :raises PlaylistAlreadyExistsError: If the user already has a
            playlist with the new name
        :raises DAOError: If a DB error occurs
        :return: The renamed playlist
        """
        try:
            self.cur.execute(
                """
                UPDATE playlists
                SET name = %s
                WHERE id_playlist = %s AND id_user = %s
                RETURNING id_playlist, id_user, name
                """,
                (playlist_in.name, id_playlist, id_user),
            )
            row = self.cur.fetchone()

        except UniqueViolation:
            raise PlaylistAlreadyExistsError(playlist_in.name) from None
        except DBError as exc:
            raise DAOError from exc

        if row is None:
            raise PlaylistNotFoundError(id_playlist)
        return PlaylistRead(**row)

    def delete(self, id_user: int, id_playlist: int) -> None:
        """Delete a playlist owned by a user.

        :param id_user: ID of the owner of the playlist
        :param id_playlist: ID of the playlist to delete
        :raises PlaylistNotFoundError: If the playlist does not exist or
            belongs to another user
        :raises DAOError: If a DB error occurs
        """
        try:
            self.cur.execute(
                """
                DELETE FROM playlists
                WHERE id_playlist = %s AND id_user = %s
                RETURNING id_playlist
                """,
                (id_playlist, id_user),
            )
            row = self.cur.fetchone()

        except DBError as exc:
            raise DAOError from exc

        if row is None:
            raise PlaylistNotFoundError(id_playlist)
