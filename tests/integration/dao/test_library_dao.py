"""Integration tests for LibraryDAO, run against the real database.

Each test is rolled back (see tests/integration/conftest.py),
so the database is left unchanged.
"""

import pytest
from psycopg2.extras import RealDictCursor

from src.dao.library_dao import LibraryDAO
from src.dao.users_dao import UserDAO
from src.models.library import LibraryBookAdd
from src.models.users import UserCreate
from src.utils.exceptions import (
    BookAlreadyInLibraryError,
    BookNotFoundError,
)


@pytest.fixture
def library_dao(cursor: RealDictCursor) -> LibraryDAO:
    """Return a LibraryDAO bound to the test cursor."""
    return LibraryDAO(cursor)


@pytest.fixture
def id_user(cursor: RealDictCursor) -> int:
    """Insert a test user in the database and return its ID."""
    user = UserDAO(cursor).create(
        UserCreate(
            username="bookworm",
            email="bookworm@ensai.fr",
            password_hash="fakehash",
        ),
    )
    return user.id_user


@pytest.fixture
def id_book(cursor: RealDictCursor) -> int:
    """Insert a test book in the database and return its ID."""
    cursor.execute(
        """
        INSERT INTO books (id_book_api, title)
        VALUES ('openlib_123', 'The Hobbit')
        RETURNING id_book
        """,
    )
    row = cursor.fetchone()
    assert row is not None
    return row["id_book"]


class TestAddBook:
    """Tests for LibraryDAO.add_book."""

    def test_ok(
        self,
        library_dao: LibraryDAO,
        id_user: int,
        id_book: int,
    ) -> None:
        """The book is added to the user's library with the correct state."""
        book_in = LibraryBookAdd(id_book=id_book, state="READING")

        result = library_dao.add_book(id_user, book_in)

        assert result.id_user == id_user
        assert result.id_book == id_book
        assert result.state == "READING"
        assert result.is_liked is False
        assert result.is_favorite is False

    def test_duplicate(
        self,
        library_dao: LibraryDAO,
        id_user: int,
        id_book: int,
    ) -> None:
        """Adding the same book twice raises BookAlreadyInLibraryError."""
        book_in = LibraryBookAdd(id_book=id_book, state="READING")
        library_dao.add_book(id_user, book_in)

        # La deuxième insertion doit échouer
        with pytest.raises(BookAlreadyInLibraryError):
            library_dao.add_book(id_user, book_in)

    def test_book_not_found(
        self,
        library_dao: LibraryDAO,
        id_user: int,
    ) -> None:
        """Adding an unknown book ID raises BookNotFoundError."""
        book_in = LibraryBookAdd(id_book=999_999, state="READING")

        with pytest.raises(BookNotFoundError):
            library_dao.add_book(id_user, book_in)
