"""Integration tests for AchievementDAO against real database (.env).

All modifications are rolled back after each test.
"""

from uuid import uuid4

import pytest
from psycopg2.extras import RealDictCursor

from src.dao.achievements_dao import AchievementDAO
from src.dao.books_dao import BookDAO
from src.dao.users_dao import UserDAO
from src.models import BookCreate, User, UserCreate

PASSWORD_HASH = "$2b$12$fakehashfakehashfakehash"
EXPECTED_COMPLETED_BOOKS = 2
EXPECTED_PAGES_READ = 350
EXPECTED_DISTINCT_GENRES = 2
BOOK1_PAGES = 200
BOOK2_PAGES = 150
REVIEW_RATING = 5


@pytest.fixture
def achievement_dao(cursor: RealDictCursor) -> AchievementDAO:
    """Return an AchievementDAO bound to the test cursor."""
    return AchievementDAO(cursor)


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
            username=f"it_alice_ach_{suffix}",
            email=f"alice_ach_{suffix}@ensai.fr",
            password_hash=PASSWORD_HASH,
        ),
    )


@pytest.fixture
def user_bob(user_dao: UserDAO) -> User:
    """Create test user Bob."""
    suffix = uuid4().hex[:8]
    return user_dao.create(
        UserCreate(
            username=f"it_bob_ach_{suffix}",
            email=f"bob_ach_{suffix}@ensai.fr",
            password_hash=PASSWORD_HASH,
        ),
    )


class TestAchievementDAO:
    """Integration tests for AchievementDAO.get_user_stats."""

    def test_empty_user_stats(
        self,
        achievement_dao: AchievementDAO,
        user_alice: User,
    ) -> None:
        """User with no activity has all zeros in stats."""
        stats = achievement_dao.get_user_stats(user_alice.id_user)

        assert stats.completed_books == 0
        assert stats.pages_read == 0
        assert stats.distinct_genres == 0
        assert stats.reviews_count == 0
        assert stats.favorites_count == 0
        assert stats.following_count == 0
        assert stats.followers_count == 0
        assert stats.playlists_count == 0

    def test_populated_user_stats(
        self,
        cursor: RealDictCursor,
        achievement_dao: AchievementDAO,
        book_dao: BookDAO,
        user_alice: User,
        user_bob: User,
    ) -> None:
        """User with complete activity returns accurate aggregated stats."""
        suffix = uuid4().hex[:8]
        book1 = book_dao.create(
            BookCreate(
                id_book_api=f"api_ach1_{suffix}",
                title="Book One",
                category="Science-Fiction",
                num_pages=BOOK1_PAGES,
            ),
        )
        book2 = book_dao.create(
            BookCreate(
                id_book_api=f"api_ach2_{suffix}",
                title="Book Two",
                category="Fantasy",
                num_pages=BOOK2_PAGES,
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

        # Alice review on book 1
        cursor.execute(
            """
            INSERT INTO reviews (id_user, id_book, rating, comment)
            VALUES (%s, %s, %s, %s);
            """,
            (user_alice.id_user, book1.id_book, REVIEW_RATING, "Great!"),
        )

        # Alice follows Bob
        cursor.execute(
            """
            INSERT INTO user_follows (follower_id, following_id)
            VALUES (%s, %s);
            """,
            (user_alice.id_user, user_bob.id_user),
        )

        # Alice created a playlist
        cursor.execute(
            """
            INSERT INTO playlists (id_user, name)
            VALUES (%s, %s);
            """,
            (user_alice.id_user, f"SciFi_{suffix}"),
        )

        stats = achievement_dao.get_user_stats(user_alice.id_user)

        assert stats.completed_books == EXPECTED_COMPLETED_BOOKS
        assert stats.pages_read == EXPECTED_PAGES_READ
        assert stats.distinct_genres == EXPECTED_DISTINCT_GENRES
        assert stats.favorites_count == 1
        assert stats.reviews_count == 1
        assert stats.following_count == 1
        assert stats.followers_count == 0
        assert stats.playlists_count == 1
