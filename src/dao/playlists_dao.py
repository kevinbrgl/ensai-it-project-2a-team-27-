"""Database access for playlists and their books."""

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
    """Manage playlists and the books they contain."""

    def __init__(self, cursor: RealDictCursor) -> None:
        """Initialize PlaylistDAO with a database cursor.

        Parameters
        ----------
        cursor : RealDictCursor
            Database cursor that yields rows as dictionaries.

        """
        self.cur = cursor

    def create(
        self,
        id_user: int,
        playlist_in: PlaylistCreate,
    ) -> PlaylistRead:
        """Create a playlist for a user.

        Parameters
        ----------
        id_user : int
            ID of the owner of the playlist.
        playlist_in : PlaylistCreate
            Name of the playlist.

        Returns
        -------
        PlaylistRead
            The created playlist.

        Raises
        ------
        PlaylistAlreadyExistsError
            If the user already has a playlist with this name.
        DAOError
            If the insertion fails or a database error occurs.

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

        Parameters
        ----------
        id_user : int
            ID of the owner of the playlists.

        Returns
        -------
        list[PlaylistRead]
            The playlists ordered by playlist ID.

        Raises
        ------
        DAOError
            If a database error occurs.

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

        Parameters
        ----------
        id_user : int
            ID of the owner of the playlist.
        id_playlist : int
            ID of the playlist to rename.
        playlist_in : PlaylistUpdate
            New name of the playlist.

        Returns
        -------
        PlaylistRead
            The renamed playlist.

        Raises
        ------
        PlaylistNotFoundError
            If no playlist with this ID belongs to the user.
        PlaylistAlreadyExistsError
            If the user already has a playlist with the new name.
        DAOError
            If a database error occurs.

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

        Parameters
        ----------
        id_user : int
            ID of the owner of the playlist.
        id_playlist : int
            ID of the playlist to delete.

        Raises
        ------
        PlaylistNotFoundError
            If no playlist with this ID belongs to the user.
        DAOError
            If a database error occurs.

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

        Parameters
        ----------
        id_user : int
            ID of the owner of the playlist.
        id_playlist : int
            ID of the playlist to read.

        Returns
        -------
        PlaylistRead | None
            The playlist owned by the user, or None if no such playlist exists.

        Raises
        ------
        DAOError
            If a database error occurs.

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

        Parameters
        ----------
        id_playlist : int
            ID of the playlist.
        id_book : int
            ID of the book to add.

        Returns
        -------
        PlaylistBookRead
            The added playlist entry.

        Raises
        ------
        BookAlreadyInPlaylistError
            If the book is already in the playlist.
        BookNotFoundError
            If the database rejects a missing playlist or book reference.
        DAOError
            If the insertion fails or a database error occurs.

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
        """List a playlist's books with their details.

        Parameters
        ----------
        id_playlist : int
            ID of the playlist.

        Returns
        -------
        list[Book]
            The books ordered by title, then by book ID.

        Raises
        ------
        DAOError
            If a database error occurs.

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

        Parameters
        ----------
        id_playlist : int
            ID of the playlist.
        id_book : int
            ID of the book to remove.

        Raises
        ------
        BookNotInPlaylistError
            If the book is absent from the playlist.
        DAOError
            If a database error occurs.

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
