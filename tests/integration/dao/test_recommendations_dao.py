"""Integration tests for RecommendationDAO, run against the real database.

Each test is rolled back (see tests/integration/conftest.py),
so the database is left unchanged.
"""

from dataclasses import dataclass
from uuid import uuid4

import pytest
from psycopg2.extras import RealDictCursor

from src.dao.books_dao import BookDAO
from src.dao.library_dao import LibraryDAO
from src.dao.recommendations_dao import RecommendationDAO
from src.dao.users_dao import UserDAO
from src.models.books import Book, BookCreate
from src.models.library import LibraryBookAdd
from src.models.users import UserCreate


def create_user(user_dao: UserDAO) -> int:
    """Insert a test user with a unique name and return its ID."""
    name = f"reco_{uuid4().hex[:8]}"
    user = user_dao.create(
        UserCreate(
            username=name,
            email=f"{name}@ensai.fr",
            password_hash="fakehash",
        ),
    )
    return user.id_user


def unique_category() -> str:
    """Return a category that no other book uses."""
    return f"Genre {uuid4().hex[:10]}"


def unique_key() -> str:
    """Return an Open Library key that no other book uses."""
    return f"/works/OL{uuid4().hex[:10]}W"


def create_book(
    book_dao: BookDAO,
    category: str | None = None,
    key: str | None = None,
    title: str = "Test book",
) -> Book:
    """Insert a book and return it."""
    return book_dao.create(
        BookCreate(title=title, category=category, id_book_api=key),
    )


def add_to_library(
    library_dao: LibraryDAO,
    id_user: int,
    id_book: int,
    state: str = "COMPLETED",
) -> None:
    """Add a book to a user's library."""
    library_dao.add_book(id_user, LibraryBookAdd(id_book=id_book, state=state))


def add_review(
    cursor: RealDictCursor,
    id_user: int,
    id_book: int,
    rating: int,
) -> None:
    """Insert a review."""
    cursor.execute(
        "INSERT INTO reviews (id_user, id_book, rating) VALUES (%s, %s, %s)",
        (id_user, id_book, rating),
    )


@pytest.fixture
def rec_dao(cursor: RealDictCursor) -> RecommendationDAO:
    """Return a RecommendationDAO bound to the test cursor."""
    return RecommendationDAO(cursor)


@pytest.fixture
def library_dao(cursor: RealDictCursor) -> LibraryDAO:
    """Return a LibraryDAO bound to the test cursor."""
    return LibraryDAO(cursor)


@dataclass
class Daos:
    """DAOs used together in the top rated tests."""

    rec: RecommendationDAO
    book: BookDAO
    library: LibraryDAO


@pytest.fixture
def daos(
    rec_dao: RecommendationDAO,
    book_dao: BookDAO,
    library_dao: LibraryDAO,
) -> Daos:
    """Return the recommendation, book and library DAOs."""
    return Daos(rec=rec_dao, book=book_dao, library=library_dao)


@pytest.fixture
def id_user(user_dao: UserDAO) -> int:
    """Insert a test user and return its ID."""
    return create_user(user_dao)


@pytest.fixture
def id_other_user(user_dao: UserDAO) -> int:
    """Insert a second test user and return its ID."""
    return create_user(user_dao)


class TestCountRatedGenres:
    """Tests for RecommendationDAO.count_rated_genres."""

    def test_no_reviews(
        self,
        rec_dao: RecommendationDAO,
        id_user: int,
    ) -> None:
        """A user without reviews gets an empty list."""
        assert rec_dao.count_rated_genres(id_user, 4) == []

    def test_only_high_ratings_counted(
        self,
        rec_dao: RecommendationDAO,
        cursor: RealDictCursor,
        book_dao: BookDAO,
        id_user: int,
    ) -> None:
        """Books rated below min_rating are ignored."""
        liked, disliked = unique_category(), unique_category()
        for rating in (5, 4):
            book = create_book(book_dao, liked)
            add_review(cursor, id_user, book.id_book, rating)
        book = create_book(book_dao, disliked)
        add_review(cursor, id_user, book.id_book, 3)

        result = rec_dao.count_rated_genres(id_user, 4)

        assert [(g.category, g.count) for g in result] == [(liked, 2)]

    def test_min_rating_parameter(
        self,
        rec_dao: RecommendationDAO,
        cursor: RealDictCursor,
        book_dao: BookDAO,
        id_user: int,
    ) -> None:
        """The threshold comes from min_rating."""
        category = unique_category()
        book = create_book(book_dao, category)
        add_review(cursor, id_user, book.id_book, 3)

        result = rec_dao.count_rated_genres(id_user, 3)

        assert [(g.category, g.count) for g in result] == [(category, 1)]

    def test_most_frequent_first(
        self,
        rec_dao: RecommendationDAO,
        cursor: RealDictCursor,
        book_dao: BookDAO,
        id_user: int,
    ) -> None:
        """Categories are sorted by count, most frequent first."""
        rare, frequent = unique_category(), unique_category()
        for category in (rare, frequent, frequent):
            book = create_book(book_dao, category)
            add_review(cursor, id_user, book.id_book, 5)

        result = rec_dao.count_rated_genres(id_user, 4)

        assert [(g.category, g.count) for g in result] == [
            (frequent, 2),
            (rare, 1),
        ]

    def test_ignores_null_and_blank_categories(
        self,
        rec_dao: RecommendationDAO,
        cursor: RealDictCursor,
        book_dao: BookDAO,
        id_user: int,
    ) -> None:
        """Books without category are not counted."""
        for category in (None, "   "):
            book = create_book(book_dao, category)
            add_review(cursor, id_user, book.id_book, 5)

        assert rec_dao.count_rated_genres(id_user, 4) == []

    def test_other_user_not_counted(
        self,
        rec_dao: RecommendationDAO,
        cursor: RealDictCursor,
        book_dao: BookDAO,
        id_user: int,
        id_other_user: int,
    ) -> None:
        """The reviews of another user are not counted."""
        book = create_book(book_dao, unique_category())
        add_review(cursor, id_other_user, book.id_book, 5)

        assert rec_dao.count_rated_genres(id_user, 4) == []


class TestFindLibraryApiKeys:
    """Tests for RecommendationDAO.find_library_api_keys."""

    def test_empty_library(
        self,
        rec_dao: RecommendationDAO,
        id_user: int,
    ) -> None:
        """An empty library gives an empty set."""
        assert rec_dao.find_library_api_keys(id_user) == set()

    def test_keys_of_every_state(
        self,
        rec_dao: RecommendationDAO,
        book_dao: BookDAO,
        library_dao: LibraryDAO,
        id_user: int,
    ) -> None:
        """Books of every reading state are returned."""
        keys = set()
        for state in ("READING", "WANT_TO_READ", "COMPLETED"):
            key = unique_key()
            keys.add(key)
            book = create_book(book_dao, key=key)
            add_to_library(library_dao, id_user, book.id_book, state)

        assert rec_dao.find_library_api_keys(id_user) == keys

    def test_books_without_key_ignored(
        self,
        rec_dao: RecommendationDAO,
        book_dao: BookDAO,
        library_dao: LibraryDAO,
        id_user: int,
    ) -> None:
        """Library books without key are not returned."""
        book = create_book(book_dao)
        add_to_library(library_dao, id_user, book.id_book)

        assert rec_dao.find_library_api_keys(id_user) == set()

    def test_other_user_not_returned(
        self,
        rec_dao: RecommendationDAO,
        book_dao: BookDAO,
        library_dao: LibraryDAO,
        id_user: int,
        id_other_user: int,
    ) -> None:
        """The library of another user is not returned."""
        book = create_book(book_dao, key=unique_key())
        add_to_library(library_dao, id_other_user, book.id_book)

        assert rec_dao.find_library_api_keys(id_user) == set()


class TestGetAverageRatings:
    """Tests for RecommendationDAO.get_average_ratings."""

    def test_empty_list(self, rec_dao: RecommendationDAO) -> None:
        """No book ID gives an empty dictionary."""
        assert rec_dao.get_average_ratings([]) == {}

    def test_average_rounded(
        self,
        rec_dao: RecommendationDAO,
        cursor: RealDictCursor,
        book_dao: BookDAO,
        user_dao: UserDAO,
    ) -> None:
        """The average is rounded to 2 decimals."""
        book = create_book(book_dao)
        for rating in (5, 4, 4):
            add_review(cursor, create_user(user_dao), book.id_book, rating)

        result = rec_dao.get_average_ratings([book.id_book])

        assert result == {book.id_book: 4.33}

    def test_several_books_and_unreviewed(
        self,
        rec_dao: RecommendationDAO,
        cursor: RealDictCursor,
        book_dao: BookDAO,
        id_user: int,
    ) -> None:
        """Every reviewed book is returned; unreviewed books are absent."""
        first, second, unreviewed = (create_book(book_dao) for _ in range(3))
        add_review(cursor, id_user, first.id_book, 5)
        add_review(cursor, id_user, second.id_book, 2)

        result = rec_dao.get_average_ratings(
            [first.id_book, second.id_book, unreviewed.id_book],
        )

        assert result == {first.id_book: 5.0, second.id_book: 2.0}


class TestFindTopRatedBooks:
    """Tests for RecommendationDAO.find_top_rated_books."""

    def test_best_average_first(
        self,
        rec_dao: RecommendationDAO,
        cursor: RealDictCursor,
        book_dao: BookDAO,
        id_user: int,
        id_other_user: int,
    ) -> None:
        """Books are sorted by average rating, best first."""
        category = unique_category()
        low = create_book(book_dao, category, title="Low")
        high = create_book(book_dao, category, title="High")
        add_review(cursor, id_other_user, low.id_book, 2)
        add_review(cursor, id_other_user, high.id_book, 5)

        result = rec_dao.find_top_rated_books(id_user, 10, category)

        assert [(b.id_book, avg) for b, avg in result] == [
            (high.id_book, 5.0),
            (low.id_book, 2.0),
        ]

    def test_tie_broken_by_review_count(
        self,
        rec_dao: RecommendationDAO,
        cursor: RealDictCursor,
        book_dao: BookDAO,
        user_dao: UserDAO,
        id_user: int,
    ) -> None:
        """With the same average, the most reviewed book comes first."""
        category = unique_category()
        once = create_book(book_dao, category)
        twice = create_book(book_dao, category)
        add_review(cursor, create_user(user_dao), once.id_book, 4)
        for _ in range(2):
            add_review(cursor, create_user(user_dao), twice.id_book, 4)

        result = rec_dao.find_top_rated_books(id_user, 10, category)

        assert [b.id_book for b, _ in result] == [twice.id_book, once.id_book]

    def test_excludes_user_library(
        self,
        daos: Daos,
        cursor: RealDictCursor,
        id_user: int,
        id_other_user: int,
    ) -> None:
        """Books in the user's library are not returned."""
        category = unique_category()
        owned = create_book(daos.book, category)
        other = create_book(daos.book, category)
        add_review(cursor, id_other_user, owned.id_book, 5)
        add_review(cursor, id_other_user, other.id_book, 3)
        add_to_library(daos.library, id_user, owned.id_book, "WANT_TO_READ")

        result = daos.rec.find_top_rated_books(id_user, 10, category)

        assert [b.id_book for b, _ in result] == [other.id_book]

    def test_other_user_library_not_excluded(
        self,
        daos: Daos,
        cursor: RealDictCursor,
        id_user: int,
        id_other_user: int,
    ) -> None:
        """Only the requesting user's library is excluded."""
        category = unique_category()
        book = create_book(daos.book, category)
        add_review(cursor, id_other_user, book.id_book, 5)
        add_to_library(daos.library, id_other_user, book.id_book)

        result = daos.rec.find_top_rated_books(id_user, 10, category)

        assert [b.id_book for b, _ in result] == [book.id_book]

    def test_unreviewed_books_absent(
        self,
        rec_dao: RecommendationDAO,
        book_dao: BookDAO,
        id_user: int,
    ) -> None:
        """Books without reviews are never returned."""
        category = unique_category()
        create_book(book_dao, category)

        assert rec_dao.find_top_rated_books(id_user, 10, category) == []

    def test_limit(
        self,
        rec_dao: RecommendationDAO,
        cursor: RealDictCursor,
        book_dao: BookDAO,
        id_user: int,
        id_other_user: int,
    ) -> None:
        """No more than limit books are returned."""
        category = unique_category()
        for rating in (5, 4, 3):
            book = create_book(book_dao, category)
            add_review(cursor, id_other_user, book.id_book, rating)

        result = rec_dao.find_top_rated_books(id_user, 2, category)

        assert [avg for _, avg in result] == [5.0, 4.0]

    def test_category_filter_partial_case_insensitive(
        self,
        rec_dao: RecommendationDAO,
        cursor: RealDictCursor,
        book_dao: BookDAO,
        id_user: int,
        id_other_user: int,
    ) -> None:
        """The category filter is a case-insensitive substring match."""
        category = unique_category()
        matching = create_book(book_dao, category)
        other = create_book(book_dao, unique_category())
        add_review(cursor, id_other_user, matching.id_book, 4)
        add_review(cursor, id_other_user, other.id_book, 5)

        result = rec_dao.find_top_rated_books(
            id_user,
            10,
            category.upper()[2:],
        )

        assert [b.id_book for b, _ in result] == [matching.id_book]

    def test_without_category(
        self,
        rec_dao: RecommendationDAO,
        cursor: RealDictCursor,
        book_dao: BookDAO,
        id_user: int,
        id_other_user: int,
    ) -> None:
        """Without a category filter, every reviewed book is a candidate."""
        book = create_book(book_dao, unique_category(), key=unique_key())
        add_review(cursor, id_other_user, book.id_book, 5)

        result = rec_dao.find_top_rated_books(id_user, 100000)

        found = [b for b, _ in result if b.id_book == book.id_book]
        assert found == [book]
