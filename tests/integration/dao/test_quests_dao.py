"""Integration tests for QuestDAO against real database (.env).

All modifications are rolled back after each test.
"""

from datetime import date
from uuid import uuid4

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


EXTENDED = {
    "library_size": 4,
    "completed_books": 2,
    "reading_books": 1,
    "want_to_read_books": 1,
    "favorite_books": 1,
    "liked_books": 2,
    "pages_read": 500,
    "distinct_categories": 2,
    "distinct_authors": 1,
    "dated_books": 2,
    "following_count": 1,
    "followers_count": 1,
    "mutual_follows": 1,
    "reviews_count": 1,
    "playlists_count": 2,
    "playlist_books": 3,
    "profile_fields": 2,
}


def test_extended_user_stats(
    cursor: RealDictCursor,
    quest_dao: QuestDAO,
    book_dao: BookDAO,
    user_dao: UserDAO,
    user_alice: User,
) -> None:
    """Every quest metric is computed from the matching activity."""
    suffix = uuid4().hex[:8]
    specs = [
        # author, category, pages, state, liked, favorite, finished
        ("Jane Austen", "Romance", 200, "COMPLETED", True, True, True),
        ("JANE AUSTEN", "Classics", 300, "COMPLETED", True, False, True),
        ("Someone Else", None, 999, "READING", False, False, False),
        (None, None, None, "WANT_TO_READ", False, False, False),
    ]
    books = []
    for index, (author, category, pages, state, liked, fav, done) in enumerate(
        specs,
    ):
        book = book_dao.create(
            BookCreate(
                id_book_api=f"api_q_x{index}_{suffix}",
                title=f"Book {index}",
                author=author,
                category=category,
                num_pages=pages,
            ),
        )
        books.append(book)
        cursor.execute(
            """
            INSERT INTO user_book_activities
                (id_user, id_book, state, is_liked, is_favorite, finished_at)
            VALUES (%s, %s, %s, %s, %s, %s);
            """,
            (
                user_alice.id_user,
                book.id_book,
                state,
                liked,
                fav,
                date(2026, 5, 1) if done else None,
            ),
        )

    bob = user_dao.create(
        UserCreate(
            username=f"it_bob_qx_{suffix}",
            email=f"bob_qx_{suffix}@ensai.fr",
            password_hash=PASSWORD_HASH,
        ),
    )
    user_dao.add_follow(user_alice.id_user, bob.id_user)
    user_dao.add_follow(bob.id_user, user_alice.id_user)

    cursor.execute(
        """
        INSERT INTO reviews (id_user, id_book, rating)
        VALUES (%s, %s, 4);
        """,
        (user_alice.id_user, books[0].id_book),
    )
    cursor.execute(
        """
        INSERT INTO playlists (id_user, name)
        VALUES (%s, %s), (%s, %s)
        RETURNING id_playlist;
        """,
        (user_alice.id_user, f"A_{suffix}", user_alice.id_user, f"B_{suffix}"),
    )
    first, second = (row["id_playlist"] for row in cursor.fetchall())
    cursor.execute(
        """
        INSERT INTO playlist_books (id_playlist, id_book)
        VALUES (%s, %s), (%s, %s), (%s, %s);
        """,
        (
            first,
            books[0].id_book,
            first,
            books[1].id_book,
            second,
            books[0].id_book,
        ),
    )
    cursor.execute(
        """
        UPDATE users
        SET bio = 'Reader.', profile_picture = 'https://example.com/a.png'
        WHERE id_user = %s;
        """,
        (user_alice.id_user,),
    )

    stats = quest_dao.get_user_stats(user_alice.id_user)

    assert stats.model_dump() == EXTENDED
