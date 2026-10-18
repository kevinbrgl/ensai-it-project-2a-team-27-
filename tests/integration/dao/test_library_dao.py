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
    BookNotInLibraryError,
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


@pytest.fixture
def id_other_book(cursor: RealDictCursor) -> int:
    """Insert a second test book in the database and return its ID."""
    cursor.execute(
        """
        INSERT INTO books (id_book_api, title)
        VALUES ('openlib_456', 'Dune')
        RETURNING id_book
        """,
    )
    row = cursor.fetchone()
    assert row is not None
    return row["id_book"]


@pytest.fixture
def id_other_user(cursor: RealDictCursor) -> int:
    """Insert a second test user in the database and return its ID."""
    user = UserDAO(cursor).create(
        UserCreate(
            username="bibliophile",
            email="bibliophile@ensai.fr",
            password_hash="fakehash",
        ),
    )
    return user.id_user


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


class TestRemoveBook:
    """Tests for LibraryDAO.remove_book."""

    def test_ok(
        self,
        cursor: RealDictCursor,
        library_dao: LibraryDAO,
        id_user: int,
        id_book: int,
    ) -> None:
        """The book is removed from the user's library."""
        library_dao.add_book(
            id_user,
            LibraryBookAdd(id_book=id_book, state="READING"),
        )

        library_dao.remove_book(id_user, id_book)

        cursor.execute(
            """
            SELECT * FROM user_book_activities
            WHERE id_user = %s AND id_book = %s
            """,
            (id_user, id_book),
        )
        assert cursor.fetchone() is None

    def test_not_in_library(
        self,
        library_dao: LibraryDAO,
        id_user: int,
        id_book: int,
    ) -> None:
        """Removing a book the user does not have raises an error."""
        with pytest.raises(BookNotInLibraryError):
            library_dao.remove_book(id_user, id_book)


class TestToggleLike:
    """Tests for LibraryDAO.toggle_like."""

    def test_like(
        self,
        library_dao: LibraryDAO,
        id_user: int,
        id_book: int,
    ) -> None:
        """A book that is not liked becomes liked."""
        library_dao.add_book(
            id_user,
            LibraryBookAdd(id_book=id_book, state="READING"),
        )

        result = library_dao.toggle_like(id_user, id_book)

        assert result.id_user == id_user
        assert result.id_book == id_book
        assert result.is_liked is True

    def test_like_then_unlike(
        self,
        library_dao: LibraryDAO,
        id_user: int,
        id_book: int,
    ) -> None:
        """A second toggle removes the like."""
        library_dao.add_book(
            id_user,
            LibraryBookAdd(id_book=id_book, state="READING"),
        )
        library_dao.toggle_like(id_user, id_book)

        result = library_dao.toggle_like(id_user, id_book)

        assert result.is_liked is False

    def test_other_fields_unchanged(
        self,
        library_dao: LibraryDAO,
        id_user: int,
        id_book: int,
    ) -> None:
        """Toggling the like does not change the state or the favorite."""
        library_dao.add_book(
            id_user,
            LibraryBookAdd(id_book=id_book, state="COMPLETED"),
        )

        result = library_dao.toggle_like(id_user, id_book)

        assert result.state == "COMPLETED"
        assert result.is_favorite is False

    def test_not_in_library(
        self,
        library_dao: LibraryDAO,
        id_user: int,
        id_book: int,
    ) -> None:
        """Liking a book the user does not have raises an error."""
        with pytest.raises(BookNotInLibraryError):
            library_dao.toggle_like(id_user, id_book)


class TestToggleFavorite:
    """Tests for LibraryDAO.toggle_favorite."""

    def test_favorite(
        self,
        library_dao: LibraryDAO,
        id_user: int,
        id_book: int,
    ) -> None:
        """A book that is not a favorite becomes a favorite."""
        library_dao.add_book(
            id_user,
            LibraryBookAdd(id_book=id_book, state="READING"),
        )

        result = library_dao.toggle_favorite(id_user, id_book)

        assert result.id_user == id_user
        assert result.id_book == id_book
        assert result.is_favorite is True

    def test_favorite_then_unfavorite(
        self,
        library_dao: LibraryDAO,
        id_user: int,
        id_book: int,
    ) -> None:
        """A second toggle removes the favorite."""
        library_dao.add_book(
            id_user,
            LibraryBookAdd(id_book=id_book, state="READING"),
        )
        library_dao.toggle_favorite(id_user, id_book)

        result = library_dao.toggle_favorite(id_user, id_book)

        assert result.is_favorite is False

    def test_other_fields_unchanged(
        self,
        library_dao: LibraryDAO,
        id_user: int,
        id_book: int,
    ) -> None:
        """Toggling the favorite does not change the state or the like."""
        library_dao.add_book(
            id_user,
            LibraryBookAdd(id_book=id_book, state="COMPLETED"),
        )

        result = library_dao.toggle_favorite(id_user, id_book)

        assert result.state == "COMPLETED"
        assert result.is_liked is False

    def test_not_in_library(
        self,
        library_dao: LibraryDAO,
        id_user: int,
        id_book: int,
    ) -> None:
        """Adding to favorites a book the user does not have raises."""
        with pytest.raises(BookNotInLibraryError):
            library_dao.toggle_favorite(id_user, id_book)


class TestFindFavoritesByUserId:
    """Tests for LibraryDAO.find_favorites_by_user_id."""

    def test_empty_library(
        self,
        library_dao: LibraryDAO,
        id_user: int,
    ) -> None:
        """A user with no books has no favorites."""
        assert library_dao.find_favorites_by_user_id(id_user) == []

    def test_not_favorite(
        self,
        library_dao: LibraryDAO,
        id_user: int,
        id_book: int,
    ) -> None:
        """A book in the library but not in favorites is not listed."""
        library_dao.add_book(
            id_user,
            LibraryBookAdd(id_book=id_book, state="READING"),
        )

        assert library_dao.find_favorites_by_user_id(id_user) == []

    def test_favorite(
        self,
        library_dao: LibraryDAO,
        id_user: int,
        id_book: int,
    ) -> None:
        """A favorite book is listed with its activity data."""
        library_dao.add_book(
            id_user,
            LibraryBookAdd(id_book=id_book, state="READING"),
        )
        library_dao.toggle_favorite(id_user, id_book)

        result = library_dao.find_favorites_by_user_id(id_user)

        assert len(result) == 1
        assert result[0].id_user == id_user
        assert result[0].id_book == id_book
        assert result[0].state == "READING"
        assert result[0].is_favorite is True

    def test_only_favorites(
        self,
        library_dao: LibraryDAO,
        id_user: int,
        id_book: int,
        id_other_book: int,
    ) -> None:
        """Among several books, only the favorite one is listed."""
        library_dao.add_book(
            id_user,
            LibraryBookAdd(id_book=id_book, state="READING"),
        )
        library_dao.add_book(
            id_user,
            LibraryBookAdd(id_book=id_other_book, state="COMPLETED"),
        )
        library_dao.toggle_favorite(id_user, id_other_book)

        result = library_dao.find_favorites_by_user_id(id_user)

        assert [fav.id_book for fav in result] == [id_other_book]

    def test_sorted_by_book(
        self,
        library_dao: LibraryDAO,
        id_user: int,
        id_book: int,
        id_other_book: int,
    ) -> None:
        """Several favorites are listed, sorted by book ID."""
        for book in (id_other_book, id_book):
            library_dao.add_book(
                id_user,
                LibraryBookAdd(id_book=book, state="READING"),
            )
            library_dao.toggle_favorite(id_user, book)

        result = library_dao.find_favorites_by_user_id(id_user)

        assert [fav.id_book for fav in result] == sorted(
            [id_book, id_other_book],
        )

    def test_other_user_favorites_not_listed(
        self,
        library_dao: LibraryDAO,
        id_user: int,
        id_other_user: int,
        id_book: int,
    ) -> None:
        """The favorites of another user are never listed."""
        library_dao.add_book(
            id_other_user,
            LibraryBookAdd(id_book=id_book, state="READING"),
        )
        library_dao.toggle_favorite(id_other_user, id_book)

        assert library_dao.find_favorites_by_user_id(id_user) == []
