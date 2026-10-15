"""Data Access Object for library operations."""

from psycopg2 import Error as DBError
from psycopg2.errors import ForeignKeyViolation, UniqueViolation
from psycopg2.extras import RealDictCursor

from src.models.library import LibraryBookAdd, LibraryBookRead
from src.utils.exceptions import (
    BookAlreadyInLibraryError,
    BookNotFoundError,
    DAOError,
)


class LibraryDAO:
    """DAO class for user library operations."""

    def __init__(self, cursor: RealDictCursor) -> None:
        """Initialize LibraryDAO with a database cursor.

        :param cursor: Database cursor
        """
        self.cur = cursor

    def add_book(
        self, id_user: int, book_in: LibraryBookAdd,
    ) -> LibraryBookRead:
        """Add a book to a user's library with a reading state.

        :param id_user: ID of the user
        :param book_in: Book ID and state to add
        :raises BookAlreadyInLibraryError: If the user already added this book
        :raises BookNotFoundError: If the book is not in the local database
        :raises DAOError: If the insertion fails or a DB error occurs
        :return: The created Library activity object
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
