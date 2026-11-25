"""Check the demo loader on an empty, transaction-local set of tables."""

from psycopg2.extras import RealDictCursor

from src.core.security import verify_password
from src.seed_demo import load_demo


def test_demo_can_be_loaded_twice(cursor: RealDictCursor) -> None:
    """A second load preserves reader edits and all sample relationships."""
    cursor.execute("SET LOCAL search_path TO pg_temp")
    load_demo(cursor)
    cursor.execute(
        "UPDATE reviews SET comment = 'My own review' WHERE rating = 4",
    )
    load_demo(cursor)

    cursor.execute(
        """
        SELECT (SELECT count(*) FROM users) AS readers,
               (SELECT count(*) FROM books) AS books,
               (SELECT count(*) FROM user_book_activities) AS activities,
               (SELECT count(*) FROM user_follows) AS follows,
               (SELECT count(*) FROM playlists) AS playlists,
               (SELECT count(*) FROM playlist_books) AS playlist_entries,
               (SELECT count(*) FROM reviews) AS reviews,
               (SELECT comment FROM reviews WHERE rating = 4) AS edited_review
        """,
    )
    assert cursor.fetchone() == {
        "readers": 2,
        "books": 4,
        "activities": 5,
        "follows": 1,
        "playlists": 1,
        "playlist_entries": 2,
        "reviews": 3,
        "edited_review": "My own review",
    }
    cursor.execute("SELECT password_hash FROM users")
    assert all(
        verify_password("ExLibrisDemo27", reader["password_hash"])
        for reader in cursor.fetchall()
    )
    cursor.execute("SELECT username FROM users WHERE is_admin")
    assert cursor.fetchall() == [{"username": "demo_jo"}]
