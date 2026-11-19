"""Database access for users' book libraries."""

from datetime import date

from psycopg2 import Error as DBError
from psycopg2.errors import ForeignKeyViolation, UniqueViolation
from psycopg2.extras import RealDictCursor

from src.models.library import (
    LibraryBookAdd,
    LibraryBookDetails,
    LibraryBookRead,
)
from src.utils.exceptions import (
    BookAlreadyInLibraryError,
    BookNotFoundError,
    BookNotInLibraryError,
    DAOError,
)


class LibraryDAO:
    """Manage reading activity and favorites in user libraries."""

    def __init__(self, cursor: RealDictCursor) -> None:
        """Initialize LibraryDAO with a database cursor.

        Parameters
        ----------
        cursor : RealDictCursor
            Database cursor that yields rows as dictionaries.

        """
        self.cur = cursor

    def add_book(
        self,
        id_user: int,
        book_in: LibraryBookAdd,
    ) -> LibraryBookRead:
        """Add a book to a user's library with a reading state.

        Parameters
        ----------
        id_user : int
            ID of the user.
        book_in : LibraryBookAdd
            Book ID and state to add.

        Returns
        -------
        LibraryBookRead
            The new library entry, including its initial reading state.

        Raises
        ------
        BookAlreadyInLibraryError
            If the user already added this book.
        BookNotFoundError
            If the database rejects a missing user or book reference.
        DAOError
            If the insertion fails or a database error occurs.

        """
        try:
            self.cur.execute(
                """
                INSERT INTO user_book_activities (id_user, id_book, state)
                VALUES (%s, %s, %s)
                RETURNING *
                """,
                (id_user, book_in.id_book, book_in.state),
            )
            row = self.cur.fetchone()

        except UniqueViolation:
            raise BookAlreadyInLibraryError(book_in.id_book) from None
        except ForeignKeyViolation:
            raise BookNotFoundError(book_in.id_book) from None
        except DBError as exc:
            raise DAOError from exc

        if row is None:
            msg = "Adding book to library failed"
            raise DAOError(msg)
        return LibraryBookRead(**row)

    def read(self, id_user: int, id_book: int) -> LibraryBookRead | None:
        """Find a book's entry in a user's library.

        Parameters
        ----------
        id_user : int
            ID of the user.
        id_book : int
            ID of the book.

        Returns
        -------
        LibraryBookRead | None
            The library entry, or None if absent from the user's library.

        Raises
        ------
        DAOError
            If a database error occurs.

        """
        try:
            self.cur.execute(
                """
                SELECT id_user, id_book, state, is_liked, is_favorite,
                       started_at, finished_at
                FROM user_book_activities
                WHERE id_user = %s AND id_book = %s
                """,
                (id_user, id_book),
            )
            row = self.cur.fetchone()

        except DBError as exc:
            raise DAOError from exc

        return LibraryBookRead(**row) if row else None

    def remove_book(self, id_user: int, id_book: int) -> None:
        """Remove a book from a user's library.

        Parameters
        ----------
        id_user : int
            ID of the user.
        id_book : int
            ID of the book to remove.

        Raises
        ------
        BookNotInLibraryError
            If the book is absent from the library.
        DAOError
            If a database error occurs.

        """
        try:
            self.cur.execute(
                """
                DELETE FROM user_book_activities
                WHERE id_user = %s AND id_book = %s
                RETURNING id_book
                """,
                (id_user, id_book),
            )
            row = self.cur.fetchone()

        except DBError as exc:
            raise DAOError from exc

        if row is None:
            raise BookNotInLibraryError(id_book)

    def toggle_like(self, id_user: int, id_book: int) -> LibraryBookRead:
        """Toggle the like flag on a book in a user's library.

        Parameters
        ----------
        id_user : int
            ID of the user.
        id_book : int
            ID of the book to like or unlike.

        Returns
        -------
        LibraryBookRead
            The library entry with its updated like flag.

        Raises
        ------
        BookNotInLibraryError
            If the book is absent from the library.
        DAOError
            If a database error occurs.

        """
        try:
            self.cur.execute(
                """
                UPDATE user_book_activities
                SET is_liked = NOT is_liked
                WHERE id_user = %s AND id_book = %s
                RETURNING *
                """,
                (id_user, id_book),
            )
            row = self.cur.fetchone()

        except DBError as exc:
            raise DAOError from exc

        if row is None:
            raise BookNotInLibraryError(id_book)
        return LibraryBookRead(**row)

    def toggle_favorite(
        self,
        id_user: int,
        id_book: int,
    ) -> LibraryBookRead:
        """Toggle the favorite flag on a book in a user's library.

        Parameters
        ----------
        id_user : int
            ID of the user.
        id_book : int
            ID of the book to add to or remove from favorites.

        Returns
        -------
        LibraryBookRead
            The library entry with its updated favorite flag.

        Raises
        ------
        BookNotInLibraryError
            If the book is absent from the library.
        DAOError
            If a database error occurs.

        """
        try:
            self.cur.execute(
                """
                UPDATE user_book_activities
                SET is_favorite = NOT is_favorite
                WHERE id_user = %s AND id_book = %s
                RETURNING *
                """,
                (id_user, id_book),
            )
            row = self.cur.fetchone()

        except DBError as exc:
            raise DAOError from exc

        if row is None:
            raise BookNotInLibraryError(id_book)
        return LibraryBookRead(**row)

    def update_status(
        self,
        id_user: int,
        id_book: int,
        state: str,
    ) -> LibraryBookRead:
        """Update the reading state of a book in a user's library.

        Parameters
        ----------
        id_user : int
            ID of the user.
        id_book : int
            ID of the book to update.
        state : str
            The new reading state.

        Returns
        -------
        LibraryBookRead
            The library entry with its updated reading state.

        Raises
        ------
        BookNotInLibraryError
            If the book is absent from the library.
        DAOError
            If a database error occurs.

        """
        try:
            self.cur.execute(
                """
                UPDATE user_book_activities
                SET state = %s
                WHERE id_user = %s AND id_book = %s
                RETURNING *
                """,
                (state, id_user, id_book),
            )
            row = self.cur.fetchone()

        except DBError as exc:
            raise DAOError from exc

        if row is None:
            raise BookNotInLibraryError(id_book)
        return LibraryBookRead(**row)

    def update_dates(
        self,
        id_user: int,
        id_book: int,
        started_at: date | None,
        finished_at: date | None,
    ) -> LibraryBookRead:
        """Set the reading dates of a book in a user's library.

        The update writes both dates. Pass the stored date to preserve it
        or pass None to clear it.

        Parameters
        ----------
        id_user : int
            ID of the user.
        id_book : int
            ID of the book to update.
        started_at : date | None
            Date the user started the book, or None to clear it.
        finished_at : date | None
            Date the user finished the book, or None to clear it.

        Returns
        -------
        LibraryBookRead
            The library entry with its updated reading dates.

        Raises
        ------
        BookNotInLibraryError
            If the book is absent from the library.
        DAOError
            If a database error occurs.

        """
        try:
            self.cur.execute(
                """
                UPDATE user_book_activities
                SET started_at = %s, finished_at = %s
                WHERE id_user = %s AND id_book = %s
                RETURNING *
                """,
                (started_at, finished_at, id_user, id_book),
            )
            row = self.cur.fetchone()

        except DBError as exc:
            raise DAOError from exc

        if row is None:
            raise BookNotInLibraryError(id_book)
        return LibraryBookRead(**row)

    def find_favorites_by_user_id(
        self,
        id_user: int,
    ) -> list[LibraryBookDetails]:
        """List a user's favorite books with their details.

        Parameters
        ----------
        id_user : int
            ID of the user.

        Returns
        -------
        list[LibraryBookDetails]
            Library entries and book details ordered by book ID.

        Raises
        ------
        DAOError
            If a database error occurs.

        """
        try:
            self.cur.execute(
                """
                SELECT uba.id_user, uba.id_book, uba.state,
                       uba.is_liked, uba.is_favorite,
                       uba.started_at, uba.finished_at,
                       b.title, b.author, b.category, b.publish_date,
                       b.description, b.cover_image
                FROM user_book_activities AS uba
                JOIN books AS b ON b.id_book = uba.id_book
                WHERE uba.id_user = %s AND uba.is_favorite = TRUE
                ORDER BY uba.id_book
                """,
                (id_user,),
            )
            rows = self.cur.fetchall()

        except DBError as exc:
            raise DAOError from exc

        return [LibraryBookDetails(**row) for row in rows]

    def find_books_by_user_id(
        self,
        id_user: int,
        status: str | None = None,
    ) -> list[LibraryBookDetails]:
        """List a user's books, optionally filtered by reading state.

        Parameters
        ----------
        id_user : int
            ID of the user.
        status : str | None, optional
            Reading state to match. Defaults to None to include all states.

        Returns
        -------
        list[LibraryBookDetails]
            Matching library entries and book details ordered by book ID.

        Raises
        ------
        DAOError
            If a database error occurs.

        """
        query = """
            SELECT uba.id_user, uba.id_book, uba.state,
                   uba.is_liked, uba.is_favorite,
                   uba.started_at, uba.finished_at,
                   b.title, b.author, b.category, b.publish_date,
                   b.description, b.cover_image
            FROM user_book_activities AS uba
            JOIN books AS b ON b.id_book = uba.id_book
            WHERE uba.id_user = %s
        """
        params: list[int | str] = [id_user]

        if status is not None:
            query += " AND uba.state = %s"
            params.append(status)

        query += " ORDER BY uba.id_book"

        try:
            self.cur.execute(query, tuple(params))
            rows = self.cur.fetchall()
        except DBError as exc:
            raise DAOError from exc

        return [LibraryBookDetails(**row) for row in rows]
