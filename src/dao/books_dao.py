"""Data Access Object for book operations.

This module provides database operations for books in PostgreSQL.
All database errors are wrapped in DAOError.
"""

from psycopg2 import Error as DBError
from psycopg2.extras import RealDictCursor

from src.models.books import Book, BookCreate
from src.utils.exceptions import DAOError


class BookDAO:
    """DAO class for book database operations.

    :attr cur: Database cursor (RealDictCursor)
    """

    def __init__(self, cursor: RealDictCursor) -> None:
        """Initialize BookDAO with a database cursor.

        :param cursor: Database cursor
        """
        self.cur = cursor

    def create(self, book_create: BookCreate) -> Book:
        """Create a new book in the database.

        :param book_create: Data for book creation
        :raises DAOError: If the insertion fails or a DB error occurs
        :return: The created Book object
        """
        try:
            self.cur.execute(
                """
                INSERT INTO books (
                    id_book_api, title, author, category,
                    publish_date, description, cover_image
                )
                VALUES (
                    %(id_book_api)s, %(title)s, %(author)s, %(category)s,
                    %(publish_date)s, %(description)s, %(cover_image)s
                )
                RETURNING *
                """,
                book_create.model_dump(),
            )
            row = self.cur.fetchone()
        except DBError as exc:
            raise DAOError from exc

        if row is None:
            msg = "Book creation failed."
            raise DAOError(msg)
        return Book(**row)

    def upsert(self, book_create: BookCreate) -> Book:
        """Insert or update a book by its external API ID.

        :param book_create: Data for book upsert
        :raises DAOError: If a DB error occurs
        :return: The inserted or updated Book object
        """
        if not book_create.id_book_api:
            return self.create(book_create)

        try:
            self.cur.execute(
                """
                INSERT INTO books (
                    id_book_api, title, author, category,
                    publish_date, description, cover_image
                )
                VALUES (
                    %(id_book_api)s, %(title)s, %(author)s, %(category)s,
                    %(publish_date)s, %(description)s, %(cover_image)s
                )
                ON CONFLICT (id_book_api) DO UPDATE SET
                    title = EXCLUDED.title,
                    author = COALESCE(EXCLUDED.author, books.author),
                    category = COALESCE(EXCLUDED.category, books.category),
                    publish_date = COALESCE(
                        EXCLUDED.publish_date, books.publish_date
                    ),
                    description = COALESCE(
                        EXCLUDED.description, books.description
                    ),
                    cover_image = COALESCE(
                        EXCLUDED.cover_image, books.cover_image
                    )
                RETURNING *
                """,
                book_create.model_dump(),
            )
            row = self.cur.fetchone()
        except DBError as exc:
            raise DAOError from exc

        if row is None:
            msg = "Book upsert failed."
            raise DAOError(msg)
        return Book(**row)

    def read(self, book_id: int) -> Book | None:
        """Read a book by its internal ID.

        :param book_id: Internal ID of the book
        :raises DAOError: If a DB error occurs
        :return: The Book object or None if not found
        """
        try:
            self.cur.execute(
                """
                SELECT id_book, id_book_api, title, author,
                       category, publish_date, description, cover_image
                FROM books
                WHERE id_book = %s
                """,
                (book_id,),
            )
            row = self.cur.fetchone()
        except DBError as exc:
            raise DAOError from exc
        return Book(**row) if row else None

    def read_by_api_id(self, id_book_api: str) -> Book | None:
        """Read a book by its external API ID.

        :param id_book_api: External API identifier (e.g. Open Library key)
        :raises DAOError: If a DB error occurs
        :return: The Book object or None if not found
        """
        try:
            self.cur.execute(
                """
                SELECT id_book, id_book_api, title, author,
                       category, publish_date, description, cover_image
                FROM books
                WHERE id_book_api = %s
                """,
                (id_book_api,),
            )
            row = self.cur.fetchone()
        except DBError as exc:
            raise DAOError from exc
        return Book(**row) if row else None

    def find_by_author(self, author: str) -> list[Book]:
        """Find books by author.

        :param author: Name or partial name of the author
        :raises DAOError: If a DB error occurs
        :return: List of matching books
        """
        try:
            self.cur.execute(
                """
                SELECT id_book, id_book_api, title, author,
                       category, publish_date, description, cover_image
                FROM books
                WHERE author ILIKE %s
                """,
                (f"%{author}%",),
            )
            rows = self.cur.fetchall()
        except DBError as exc:
            raise DAOError from exc
        return [Book(**row) for row in rows]

    def find_by_category(self, category: str) -> list[Book]:
        """Find books by category.

        :param category: Category name
        :raises DAOError: If a DB error occurs
        :return: List of matching books
        """
        try:
            self.cur.execute(
                """
                SELECT id_book, id_book_api, title, author,
                       category, publish_date, description, cover_image
                FROM books
                WHERE category ILIKE %s
                """,
                (f"%{category}%",),
            )
            rows = self.cur.fetchall()
        except DBError as exc:
            raise DAOError from exc
        return [Book(**row) for row in rows]
