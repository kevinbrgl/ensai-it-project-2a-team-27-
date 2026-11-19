"""Integration tests for GenreWheelDAO against real database (.env).

All modifications are rolled back after each test.
"""

from uuid import uuid4

import pytest
from psycopg2.extras import RealDictCursor

from src.dao.books_dao import BookDAO
from src.dao.genre_wheel_dao import GenreWheelDAO
from src.dao.users_dao import UserDAO
from src.models import BookCreate, User, UserCreate

PASSWORD_HASH = "$2b$12$fakehashfakehashfakehash"
EXPECTED_BOOK_COUNT = 2
BOOK_PAGES = 300
RATING_FIVE = 5


@pytest.fixture
def genre_wheel_dao(cursor: RealDictCursor) -> GenreWheelDAO:
    """Return a GenreWheelDAO bound to the test cursor."""
    return GenreWheelDAO(cursor)


@pytest.fixture
def book_dao(cursor: RealDictCursor) -> BookDAO:
    """Return a BookDAO bound to the test cursor."""
    return BookDAO(cursor)


@pytest.fixture
def user_alice(user_dao: UserDAO) -> User:
    """Create test user Alice."""
    suffix = uuid4().hex[:8]
    return user_dao.create(
        UserCreate(
            username=f"it_alice_wheel_{suffix}",
            email=f"alice_wheel_{suffix}@ensai.fr",
            password_hash=PASSWORD_HASH,
        ),
    )


class TestGenreWheelDAO:
    """Integration tests for GenreWheelDAO.get_user_completed_books."""

    def test_empty_user_returns_empty_list(
        self,
        genre_wheel_dao: GenreWheelDAO,
        user_alice: User,
    ) -> None:
        """User with no reading activity returns an empty list."""
        books = genre_wheel_dao.get_user_completed_books(user_alice.id_user)
        assert books == []

    def test_populated_user_returns_completed_books(
        self,
        cursor: RealDictCursor,
        genre_wheel_dao: GenreWheelDAO,
        book_dao: BookDAO,
        user_alice: User,
    ) -> None:
        """User with completed books returns categories, favorites, ratings."""
        suffix = uuid4().hex[:8]
        book1 = book_dao.create(
            BookCreate(
                id_book_api=f"api_wheel1_{suffix}",
                title="Book One",
                category="Romance",
                num_pages=BOOK_PAGES,
            ),
        )
        book2 = book_dao.create(
            BookCreate(
                id_book_api=f"api_wheel2_{suffix}",
                title="Book Two",
                category="Science-Fiction",
                num_pages=BOOK_PAGES,
            ),
        )

        # Alice completed book 1 (favorite = True)
        cursor.execute(
            """
            INSERT INTO user_book_activities
                (id_user, id_book, state, is_favorite)
            VALUES (%s, %s, 'COMPLETED', TRUE);
            """,
            (user_alice.id_user, book1.id_book),
        )
        # Alice completed book 2 (favorite = False)
        cursor.execute(
            """
            INSERT INTO user_book_activities
                (id_user, id_book, state, is_favorite)
            VALUES (%s, %s, 'COMPLETED', FALSE);
            """,
            (user_alice.id_user, book2.id_book),
        )

        # Review on book 1
        cursor.execute(
            """
            INSERT INTO reviews (id_user, id_book, rating, comment)
            VALUES (%s, %s, %s, %s);
            """,
            (user_alice.id_user, book1.id_book, RATING_FIVE, "Superbe !"),
        )

        books = genre_wheel_dao.get_user_completed_books(user_alice.id_user)

        assert len(books) == EXPECTED_BOOK_COUNT
        romance_entry = next(b for b in books if b["category"] == "Romance")
        assert romance_entry["is_favorite"] is True
        assert romance_entry["rating"] == RATING_FIVE

        sf_entry = next(b for b in books if b["category"] == "Science-Fiction")
        assert sf_entry["is_favorite"] is False
        assert sf_entry["rating"] is None
