"""Data Access Object for playlist operations."""

from psycopg2 import Error as DBError
from psycopg2.errors import ForeignKeyViolation, UniqueViolation
from psycopg2.extras import RealDictCursor

from src.models.books import Book
from src.models.playlists import (
    PlaylistBookRead,
    PlaylistCreate,
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

    def read(self, id_user: int, id_playlist: int) -> PlaylistRead | None:
        """Read a playlist owned by a user.

        :param id_user: ID of the owner of the playlist
        :param id_playlist: ID of the playlist to read
        :raises DAOError: If a DB error occurs
        :return: The playlist, or None if it does not exist or belongs to
            another user
        """
        try:
            self.cur.execute(
                """
                SELECT id_playlist, id_user, name
                FROM playlists
                WHERE id_playlist = %s AND id_user = %s
                """,
                (id_playlist, id_user),
            )
            row = self.cur.fetchone()

        except DBError as exc:
            raise DAOError from exc

        return PlaylistRead(**row) if row else None

    def add_book(self, id_playlist: int, id_book: int) -> PlaylistBookRead:
        """Add a book to a playlist.

        :param id_playlist: ID of the playlist
        :param id_book: ID of the book to add
        :raises BookAlreadyInPlaylistError: If the book is already in the
            playlist
        :raises BookNotFoundError: If the book is not in the local database
        :raises DAOError: If the insertion fails or a DB error occurs
        :return: The added playlist entry
        """
        try:
            self.cur.execute(
                """
                INSERT INTO playlist_books (id_playlist, id_book)
                VALUES (%s, %s)
                RETURNING id_playlist, id_book
                """,
                (id_playlist, id_book),
            )
            row = self.cur.fetchone()

        except UniqueViolation:
            raise BookAlreadyInPlaylistError(id_book) from None
        except ForeignKeyViolation:
            raise BookNotFoundError(id_book) from None
        except DBError as exc:
            raise DAOError from exc

        if row is None:
            msg = "Adding book to playlist failed"
            raise DAOError(msg)
        return PlaylistBookRead(**row)

    def find_books(self, id_playlist: int) -> list[Book]:
        """List the books of a playlist, with their details.

        :param id_playlist: ID of the playlist
        :raises DAOError: If a DB error occurs
        :return: The books sorted by title, or an empty list
        """
        try:
            self.cur.execute(
                """
                SELECT b.id_book, b.id_book_api, b.title, b.author,
                       b.category, b.publish_date, b.description,
                       b.cover_image
                FROM playlist_books AS pb
                JOIN books AS b ON b.id_book = pb.id_book
                WHERE pb.id_playlist = %s
                ORDER BY b.title, b.id_book
                """,
                (id_playlist,),
            )
            rows = self.cur.fetchall()

        except DBError as exc:
            raise DAOError from exc

        return [Book(**row) for row in rows]

    def remove_book(self, id_playlist: int, id_book: int) -> None:
        """Remove a book from a playlist.

        :param id_playlist: ID of the playlist
        :param id_book: ID of the book to remove
        :raises BookNotInPlaylistError: If the book is not in the playlist
        :raises DAOError: If a DB error occurs
        """
        try:
            self.cur.execute(
                """
                DELETE FROM playlist_books
                WHERE id_playlist = %s AND id_book = %s
                RETURNING id_book
                """,
                (id_playlist, id_book),
            )
            row = self.cur.fetchone()

        except DBError as exc:
            raise DAOError from exc

        if row is None:
            raise BookNotInPlaylistError(id_book)
