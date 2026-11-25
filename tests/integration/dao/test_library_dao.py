"""Integration tests for LibraryDAO, run against the real database.

Each test is rolled back (see tests/integration/conftest.py),
so the database is left unchanged.
"""

from datetime import date

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

START = date(2026, 1, 5)
END = date(2026, 1, 20)


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
        assert result.started_at is None
        assert result.finished_at is None

    def test_abandoned(
        self,
        library_dao: LibraryDAO,
        id_user: int,
        id_book: int,
    ) -> None:
        """A book can be added with the ABANDONED state."""
        book_in = LibraryBookAdd(id_book=id_book, state="ABANDONED")

        result = library_dao.add_book(id_user, book_in)

        assert result.state == "ABANDONED"

    def test_duplicate(
        self,
        library_dao: LibraryDAO,
        id_user: int,
        id_book: int,
    ) -> None:
        """Adding the same book twice raises BookAlreadyInLibraryError."""
        book_in = LibraryBookAdd(id_book=id_book, state="READING")
        library_dao.add_book(id_user, book_in)

        # The second insert must fail
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


class TestRead:
    """Tests for LibraryDAO.read."""

    def test_found(
        self,
        library_dao: LibraryDAO,
        id_user: int,
        id_book: int,
    ) -> None:
        """A book of the library is returned with its activity data."""
        added = library_dao.add_book(
            id_user,
            LibraryBookAdd(id_book=id_book, state="READING"),
        )

        assert library_dao.read(id_user, id_book) == added

    def test_not_in_library(
        self,
        library_dao: LibraryDAO,
        id_user: int,
        id_book: int,
    ) -> None:
        """A book the user does not have gives None."""
        assert library_dao.read(id_user, id_book) is None

    def test_other_user_book_not_returned(
        self,
        library_dao: LibraryDAO,
        id_user: int,
        id_other_user: int,
        id_book: int,
    ) -> None:
        """A book of another user's library gives None."""
        library_dao.add_book(
            id_other_user,
            LibraryBookAdd(id_book=id_book, state="READING"),
        )

        assert library_dao.read(id_user, id_book) is None


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
        assert result[0].title == "The Hobbit"

    def test_favorite_has_reading_dates(
        self,
        library_dao: LibraryDAO,
        id_user: int,
        id_book: int,
    ) -> None:
        """The reading dates of a favorite book are listed."""
        library_dao.add_book(
            id_user,
            LibraryBookAdd(id_book=id_book, state="COMPLETED"),
        )
        library_dao.toggle_favorite(id_user, id_book)
        library_dao.update_dates(id_user, id_book, START, END)

        result = library_dao.find_favorites_by_user_id(id_user)

        assert result[0].started_at == START
        assert result[0].finished_at == END

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


class TestFindBooksByUserId:
    """Tests for LibraryDAO.find_books_by_user_id."""

    def test_empty_library(
        self,
        library_dao: LibraryDAO,
        id_user: int,
    ) -> None:
        """A user with no books gets an empty list."""
        assert library_dao.find_books_by_user_id(id_user) == []

    def test_no_filter_returns_all(
        self,
        library_dao: LibraryDAO,
        id_user: int,
        id_book: int,
        id_other_book: int,
    ) -> None:
        """Without status filter, all books are returned."""
        library_dao.add_book(
            id_user,
            LibraryBookAdd(id_book=id_book, state="READING"),
        )
        library_dao.add_book(
            id_user,
            LibraryBookAdd(id_book=id_other_book, state="COMPLETED"),
        )

        result = library_dao.find_books_by_user_id(id_user)

        assert [b.id_book for b in result] == sorted([id_book, id_other_book])

    def test_filter_returns_matching(
        self,
        library_dao: LibraryDAO,
        id_user: int,
        id_book: int,
        id_other_book: int,
    ) -> None:
        """With a status filter, only matching books are returned."""
        library_dao.add_book(
            id_user,
            LibraryBookAdd(id_book=id_book, state="READING"),
        )
        library_dao.add_book(
            id_user,
            LibraryBookAdd(id_book=id_other_book, state="COMPLETED"),
        )

        result = library_dao.find_books_by_user_id(id_user, status="READING")

        assert len(result) == 1
        assert result[0].id_book == id_book
        assert result[0].state == "READING"

    def test_filter_abandoned(
        self,
        library_dao: LibraryDAO,
        id_user: int,
        id_book: int,
        id_other_book: int,
    ) -> None:
        """The ABANDONED filter returns only the abandoned books."""
        library_dao.add_book(
            id_user,
            LibraryBookAdd(id_book=id_book, state="ABANDONED"),
        )
        library_dao.add_book(
            id_user,
            LibraryBookAdd(id_book=id_other_book, state="READING"),
        )

        result = library_dao.find_books_by_user_id(
            id_user,
            status="ABANDONED",
        )

        assert [b.id_book for b in result] == [id_book]

    def test_filter_no_match_returns_empty(
        self,
        library_dao: LibraryDAO,
        id_user: int,
        id_book: int,
    ) -> None:
        """If no books match the filter, an empty list is returned."""
        library_dao.add_book(
            id_user,
            LibraryBookAdd(id_book=id_book, state="COMPLETED"),
        )

        result = library_dao.find_books_by_user_id(
            id_user,
            status="WANT_TO_READ",
        )

        assert result == []

    def test_reading_dates_listed(
        self,
        library_dao: LibraryDAO,
        id_user: int,
        id_book: int,
        id_other_book: int,
    ) -> None:
        """Each book is listed with its own reading dates."""
        library_dao.add_book(
            id_user,
            LibraryBookAdd(id_book=id_book, state="COMPLETED"),
        )
        library_dao.add_book(
            id_user,
            LibraryBookAdd(id_book=id_other_book, state="WANT_TO_READ"),
        )
        library_dao.update_dates(id_user, id_book, START, END)

        result = library_dao.find_books_by_user_id(id_user)

        dates = {b.id_book: (b.started_at, b.finished_at) for b in result}
        assert dates == {id_book: (START, END), id_other_book: (None, None)}

    def test_other_user_books_not_listed(
        self,
        library_dao: LibraryDAO,
        id_user: int,
        id_other_user: int,
        id_book: int,
    ) -> None:
        """Books from another user's library are never returned."""
        library_dao.add_book(
            id_other_user,
            LibraryBookAdd(id_book=id_book, state="READING"),
        )

        assert library_dao.find_books_by_user_id(id_user) == []


class TestUpdateStatus:
    """Tests for LibraryDAO.update_status."""

    def test_update_status_success(
        self,
        library_dao: LibraryDAO,
        id_user: int,
        id_book: int,
    ) -> None:
        """A book in the library has its reading state updated."""
        library_dao.add_book(
            id_user,
            LibraryBookAdd(id_book=id_book, state="READING"),
        )

        result = library_dao.update_status(id_user, id_book, "COMPLETED")

        assert result.id_user == id_user
        assert result.id_book == id_book
        assert result.state == "COMPLETED"

    def test_update_status_abandoned(
        self,
        library_dao: LibraryDAO,
        id_user: int,
        id_book: int,
    ) -> None:
        """A book in the library can be marked as abandoned."""
        library_dao.add_book(
            id_user,
            LibraryBookAdd(id_book=id_book, state="READING"),
        )

        result = library_dao.update_status(id_user, id_book, "ABANDONED")

        assert result.state == "ABANDONED"

    def test_other_fields_unchanged(
        self,
        library_dao: LibraryDAO,
        id_user: int,
        id_book: int,
    ) -> None:
        """Updating the status does not alter likes or favorites."""
        library_dao.add_book(
            id_user,
            LibraryBookAdd(id_book=id_book, state="READING"),
        )
        library_dao.toggle_like(id_user, id_book)
        library_dao.toggle_favorite(id_user, id_book)

        result = library_dao.update_status(id_user, id_book, "COMPLETED")

        assert result.state == "COMPLETED"
        assert result.is_liked is True
        assert result.is_favorite is True

    def test_not_in_library(
        self,
        library_dao: LibraryDAO,
        id_user: int,
        id_book: int,
    ) -> None:
        """Updating a book the user does not have raises an error."""
        with pytest.raises(BookNotInLibraryError):
            library_dao.update_status(id_user, id_book, "COMPLETED")


class TestUpdateDates:
    """Tests for LibraryDAO.update_dates."""

    def test_update_dates_success(
        self,
        library_dao: LibraryDAO,
        id_user: int,
        id_book: int,
    ) -> None:
        """Both reading dates are stored and returned."""
        library_dao.add_book(
            id_user,
            LibraryBookAdd(id_book=id_book, state="COMPLETED"),
        )

        result = library_dao.update_dates(id_user, id_book, START, END)

        assert result.id_user == id_user
        assert result.id_book == id_book
        assert result.started_at == START
        assert result.finished_at == END
        assert library_dao.read(id_user, id_book) == result

    def test_none_erases_a_date(
        self,
        library_dao: LibraryDAO,
        id_user: int,
        id_book: int,
    ) -> None:
        """Passing None erases a stored date."""
        library_dao.add_book(
            id_user,
            LibraryBookAdd(id_book=id_book, state="READING"),
        )
        library_dao.update_dates(id_user, id_book, START, END)

        result = library_dao.update_dates(id_user, id_book, START, None)

        assert result.started_at == START
        assert result.finished_at is None

    def test_other_fields_unchanged(
        self,
        library_dao: LibraryDAO,
        id_user: int,
        id_book: int,
    ) -> None:
        """Updating the dates does not alter the state, like or favorite."""
        library_dao.add_book(
            id_user,
            LibraryBookAdd(id_book=id_book, state="READING"),
        )
        library_dao.toggle_like(id_user, id_book)

        result = library_dao.update_dates(id_user, id_book, START, None)

        assert result.state == "READING"
        assert result.is_liked is True
        assert result.is_favorite is False

    def test_not_in_library(
        self,
        library_dao: LibraryDAO,
        id_user: int,
        id_book: int,
    ) -> None:
        """Updating a book the user does not have raises an error."""
        with pytest.raises(BookNotInLibraryError):
            library_dao.update_dates(id_user, id_book, START, END)

    def test_other_user_dates_unchanged(
        self,
        library_dao: LibraryDAO,
        id_user: int,
        id_other_user: int,
        id_book: int,
    ) -> None:
        """The dates of another user's copy of the book are not changed."""
        for user in (id_user, id_other_user):
            library_dao.add_book(
                user,
                LibraryBookAdd(id_book=id_book, state="READING"),
            )

        library_dao.update_dates(id_user, id_book, START, END)

        other = library_dao.read(id_other_user, id_book)
        assert other is not None
        assert other.started_at is None
        assert other.finished_at is None
