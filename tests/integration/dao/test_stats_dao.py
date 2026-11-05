"""Integration tests for StatsDAO, run against the real database.

Each test is rolled back (see tests/integration/conftest.py),
so the database is left unchanged.
"""

from uuid import uuid4

import pytest
from psycopg2.extras import RealDictCursor

from src.dao.books_dao import BookDAO
from src.dao.library_dao import LibraryDAO
from src.dao.stats_dao import StatsDAO
from src.dao.users_dao import UserDAO
from src.models.books import BookCreate
from src.models.library import LibraryBookAdd
from src.models.users import UserCreate


def create_user(user_dao: UserDAO) -> int:
    """Insert a test user with a unique name and return its ID.

    :param user_dao: DAO used to insert the user
    :return: ID of the created user
    """
    name = f"stats_{uuid4().hex[:8]}"
    user = user_dao.create(
        UserCreate(
            username=name,
            email=f"{name}@ensai.fr",
            password_hash="fakehash",
        ),
    )
    return user.id_user


def add_book(
    book_dao: BookDAO,
    library_dao: LibraryDAO,
    id_user: int,
    state: str,
    category: str | None = None,
) -> int:
    """Create a book and add it to a user's library with a reading state.

    :param book_dao: DAO used to create the book
    :param library_dao: DAO used to add the book to the library
    :param id_user: ID of the user
    :param state: Reading state (READING, WANT_TO_READ or COMPLETED)
    :param category: Category of the book
    :return: ID of the created book
    """
    book = book_dao.create(BookCreate(title="Test book", category=category))
    library_dao.add_book(
        id_user,
        LibraryBookAdd(id_book=book.id_book, state=state),
    )
    return book.id_book


def add_review(
    cursor: RealDictCursor,
    book_dao: BookDAO,
    id_user: int,
    rating: int,
) -> None:
    """Create a book and insert a review of it with the given rating.

    :param cursor: Test cursor
    :param book_dao: DAO used to create the book
    :param id_user: ID of the author of the review
    :param rating: Rating of the review, from 1 to 5
    """
    book = book_dao.create(BookCreate(title="Reviewed book"))
    cursor.execute(
        "INSERT INTO reviews (id_user, id_book, rating) VALUES (%s, %s, %s)",
        (id_user, book.id_book, rating),
    )


@pytest.fixture
def stats_dao(cursor: RealDictCursor) -> StatsDAO:
    """Return a StatsDAO bound to the test cursor."""
    return StatsDAO(cursor)


@pytest.fixture
def library_dao(cursor: RealDictCursor) -> LibraryDAO:
    """Return a LibraryDAO bound to the test cursor."""
    return LibraryDAO(cursor)


@pytest.fixture
def id_user(user_dao: UserDAO) -> int:
    """Insert a test user in the database and return its ID."""
    return create_user(user_dao)


@pytest.fixture
def id_other_user(user_dao: UserDAO) -> int:
    """Insert a second test user in the database and return its ID."""
    return create_user(user_dao)


class TestCountFinishedBooks:
    """Tests for StatsDAO.count_finished_books."""

    def test_no_books(self, stats_dao: StatsDAO, id_user: int) -> None:
        """A user without books has finished 0 books."""
        assert stats_dao.count_finished_books(id_user) == 0

    def test_completed_only(
        self,
        stats_dao: StatsDAO,
        book_dao: BookDAO,
        library_dao: LibraryDAO,
        id_user: int,
    ) -> None:
        """Only the books with the COMPLETED state are counted."""
        states = ("COMPLETED", "COMPLETED", "READING", "WANT_TO_READ")
        for state in states:
            add_book(book_dao, library_dao, id_user, state)

        result = stats_dao.count_finished_books(id_user)

        assert result == states.count("COMPLETED")

    def test_other_user_not_counted(
        self,
        stats_dao: StatsDAO,
        book_dao: BookDAO,
        library_dao: LibraryDAO,
        id_user: int,
        id_other_user: int,
    ) -> None:
        """The books of another user are not counted."""
        add_book(book_dao, library_dao, id_other_user, "COMPLETED")

        assert stats_dao.count_finished_books(id_user) == 0


class TestCountGenres:
    """Tests for StatsDAO.count_genres."""

    def test_no_books(self, stats_dao: StatsDAO, id_user: int) -> None:
        """A user without books gets an empty list."""
        assert stats_dao.count_genres(id_user) == []

    def test_by_category_most_frequent_first(
        self,
        stats_dao: StatsDAO,
        book_dao: BookDAO,
        library_dao: LibraryDAO,
        id_user: int,
    ) -> None:
        """Books read or being read are counted by category, sorted."""
        add_book(book_dao, library_dao, id_user, "COMPLETED", "Fantasy")
        add_book(book_dao, library_dao, id_user, "COMPLETED", "Sci-Fi")
        add_book(book_dao, library_dao, id_user, "READING", "Sci-Fi")
        add_book(book_dao, library_dao, id_user, "READING")

        result = stats_dao.count_genres(id_user)

        assert [(g.category, g.count) for g in result] == [
            ("Sci-Fi", 2),
            ("Fantasy", 1),
            (None, 1),
        ]

    def test_want_to_read_ignored(
        self,
        stats_dao: StatsDAO,
        book_dao: BookDAO,
        library_dao: LibraryDAO,
        id_user: int,
    ) -> None:
        """Books the user only wants to read are not counted."""
        add_book(book_dao, library_dao, id_user, "WANT_TO_READ", "Fantasy")

        assert stats_dao.count_genres(id_user) == []

    def test_other_user_not_counted(
        self,
        stats_dao: StatsDAO,
        book_dao: BookDAO,
        library_dao: LibraryDAO,
        id_user: int,
        id_other_user: int,
    ) -> None:
        """The books of another user are not counted."""
        add_book(book_dao, library_dao, id_other_user, "READING", "Fantasy")

        assert stats_dao.count_genres(id_user) == []


class TestCountRatings:
    """Tests for StatsDAO.count_ratings."""

    def test_no_reviews(self, stats_dao: StatsDAO, id_user: int) -> None:
        """A user without reviews gets an empty dictionary."""
        assert stats_dao.count_ratings(id_user) == {}

    def test_by_rating(
        self,
        stats_dao: StatsDAO,
        cursor: RealDictCursor,
        book_dao: BookDAO,
        id_user: int,
    ) -> None:
        """Reviews are counted by rating; unused ratings are absent."""
        for rating in (4, 4, 5):
            add_review(cursor, book_dao, id_user, rating)

        assert stats_dao.count_ratings(id_user) == {4: 2, 5: 1}

    def test_other_user_not_counted(
        self,
        stats_dao: StatsDAO,
        cursor: RealDictCursor,
        book_dao: BookDAO,
        id_user: int,
        id_other_user: int,
    ) -> None:
        """The reviews of another user are not counted."""
        add_review(cursor, book_dao, id_other_user, 1)

        assert stats_dao.count_ratings(id_user) == {}
