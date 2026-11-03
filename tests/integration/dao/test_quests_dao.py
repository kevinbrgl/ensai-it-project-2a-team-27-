"""Integration tests for QuestDAO against real database (.env).

All modifications are rolled back after each test.
"""

import pytest
from psycopg2.extras import RealDictCursor

from src.dao.books_dao import BookDAO
from src.dao.quests_dao import QuestDAO
from src.dao.users_dao import UserDAO
from src.models import BookCreate, User, UserCreate

PASSWORD_HASH = "$2b$12$fakehashfakehashfakehash"
EXPECTED_CATEGORIES = 2


@pytest.fixture
def quest_dao(cursor: RealDictCursor) -> QuestDAO:
    """Return a QuestDAO bound to the test cursor."""
    return QuestDAO(cursor)


@pytest.fixture
def book_dao(cursor: RealDictCursor) -> BookDAO:
    """Return a BookDAO bound to the test cursor."""
    return BookDAO(cursor)


@pytest.fixture
def user_alice(user_dao: UserDAO) -> User:
    """Create test user Alice."""
    return user_dao.create(
        UserCreate(
            username="it_alice_quests",
            email="alice_quests@ensai.fr",
            password_hash=PASSWORD_HASH,
        ),
    )


class TestQuestDAO:
    """Integration tests for QuestDAO.get_user_stats."""

    def test_empty_user_stats(
        self,
        quest_dao: QuestDAO,
        user_alice: User,
    ) -> None:
        """User with no activity has all zeros in stats."""
        stats = quest_dao.get_user_stats(user_alice.id_user)

        assert stats.completed_books == 0
        assert stats.reading_books == 0
        assert stats.distinct_categories == 0
        assert stats.favorite_books == 0
        assert stats.following_count == 0

    def test_populated_user_stats(
        self,
        cursor: RealDictCursor,
        quest_dao: QuestDAO,
        book_dao: BookDAO,
        user_dao: UserDAO,
        user_alice: User,
    ) -> None:
        """User with books, activities, and follows returns accurate stats."""
        # Create books in different categories
        book1 = book_dao.create(
            BookCreate(
                id_book_api="api_q1",
                title="Book One",
                category="Science-Fiction",
            ),
        )
        book2 = book_dao.create(
            BookCreate(
                id_book_api="api_q2",
                title="Book Two",
                category="Fantasy",
            ),
        )

        # Insert activities for Alice
        # Book 1: COMPLETED, favorite = True
        cursor.execute(
            """
            INSERT INTO user_book_activities
                (id_user, id_book, state, is_favorite)
            VALUES (%s, %s, 'COMPLETED', TRUE);
            """,
            (user_alice.id_user, book1.id_book),
        )
        # Book 2: READING, favorite = False
        cursor.execute(
            """
            INSERT INTO user_book_activities
                (id_user, id_book, state, is_favorite)
            VALUES (%s, %s, 'READING', FALSE);
            """,
            (user_alice.id_user, book2.id_book),
        )

        # Create target user to follow
        bob = user_dao.create(
            UserCreate(
                username="it_bob_quests",
                email="bob_quests@ensai.fr",
                password_hash=PASSWORD_HASH,
            ),
        )
        user_dao.add_follow(user_alice.id_user, bob.id_user)

        # Retrieve stats
        stats = quest_dao.get_user_stats(user_alice.id_user)

        assert stats.completed_books == 1
        assert stats.reading_books == 1
        assert stats.distinct_categories == EXPECTED_CATEGORIES
        assert stats.favorite_books == 1
        assert stats.following_count == 1
