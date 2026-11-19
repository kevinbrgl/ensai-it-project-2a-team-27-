"""Database access for user metrics used by quests.

Provides aggregated reading, library, and social metrics for users.
All database errors are wrapped in DAOError.
"""

from typing import Any

from psycopg2 import Error as DBError
from psycopg2.extras import RealDictCursor

from src.models.quests import QuestUserStats
from src.utils.exceptions import DAOError

ACTIVITY_QUERY = """
    SELECT
        COUNT(*) AS library_size,
        COUNT(*) FILTER (WHERE uba.state = 'COMPLETED') AS completed_books,
        COUNT(*) FILTER (WHERE uba.state = 'READING') AS reading_books,
        COUNT(*) FILTER (
            WHERE uba.state = 'WANT_TO_READ'
        ) AS want_to_read_books,
        COUNT(*) FILTER (WHERE uba.is_favorite = TRUE) AS favorite_books,
        COUNT(*) FILTER (WHERE uba.is_liked = TRUE) AS liked_books,
        COALESCE(SUM(b.num_pages) FILTER (
            WHERE uba.state = 'COMPLETED'
              AND b.num_pages IS NOT NULL
        ), 0) AS pages_read,
        COUNT(DISTINCT b.category) FILTER (
            WHERE b.category IS NOT NULL
              AND TRIM(b.category) <> ''
        ) AS distinct_categories,
        COUNT(DISTINCT LOWER(TRIM(b.author))) FILTER (
            WHERE uba.state = 'COMPLETED'
              AND b.author IS NOT NULL
              AND TRIM(b.author) <> ''
        ) AS distinct_authors,
        COUNT(*) FILTER (
            WHERE uba.state = 'COMPLETED'
              AND uba.finished_at IS NOT NULL
        ) AS dated_books
    FROM user_book_activities uba
    LEFT JOIN books b ON uba.id_book = b.id_book
    WHERE uba.id_user = %(user_id)s;
"""

SOCIAL_QUERY = """
    SELECT
        (
            SELECT COUNT(*)
            FROM user_follows
            WHERE follower_id = %(user_id)s
        ) AS following_count,
        (
            SELECT COUNT(*)
            FROM user_follows
            WHERE following_id = %(user_id)s
        ) AS followers_count,
        (
            SELECT COUNT(*)
            FROM user_follows f
            JOIN user_follows back
              ON back.follower_id = f.following_id
             AND back.following_id = f.follower_id
            WHERE f.follower_id = %(user_id)s
        ) AS mutual_follows,
        (
            SELECT COUNT(*)
            FROM reviews
            WHERE id_user = %(user_id)s
        ) AS reviews_count,
        (
            SELECT COUNT(*)
            FROM playlists
            WHERE id_user = %(user_id)s
        ) AS playlists_count,
        (
            SELECT COUNT(*)
            FROM playlist_books pb
            JOIN playlists p ON p.id_playlist = pb.id_playlist
            WHERE p.id_user = %(user_id)s
        ) AS playlist_books,
        (
            SELECT
                (CASE WHEN TRIM(COALESCE(bio, '')) <> '' THEN 1 ELSE 0 END)
                + (CASE WHEN TRIM(COALESCE(profile_picture, '')) <> ''
                        THEN 1 ELSE 0 END)
            FROM users
            WHERE id_user = %(user_id)s
        ) AS profile_fields;
"""


def _count(row: dict[str, Any], key: str) -> int:
    """Read a metric from a result row, treating NULL as zero."""
    return int(row.get(key) or 0)


class QuestDAO:
    """Query the reading and social metrics used by quests.

    Attributes
    ----------
    cur : RealDictCursor
        PostgreSQL cursor that fetches rows as dictionaries.

    """

    def __init__(self, cur: RealDictCursor) -> None:
        """Initialize the QuestDAO with a database cursor.

        Parameters
        ----------
        cur : RealDictCursor
            Database cursor that yields rows as dictionaries.

        """
        self.cur = cur

    def get_user_stats(self, user_id: int) -> QuestUserStats:
        """Retrieve aggregated quest metrics for a user.

        Parameters
        ----------
        user_id : int
            ID of the user whose metrics to compute.

        Returns
        -------
        QuestUserStats
            Library, reading, review, playlist, follow, and profile metrics.

        Raises
        ------
        DAOError
            If a database error occurs.

        """
        params = {"user_id": user_id}
        try:
            self.cur.execute(ACTIVITY_QUERY, params)
            activity_row: dict[str, Any] = self.cur.fetchone() or {}

            self.cur.execute(SOCIAL_QUERY, params)
            social_row: dict[str, Any] = self.cur.fetchone() or {}

        except DBError as exc:
            raise DAOError from exc

        row = {**activity_row, **social_row}
        return QuestUserStats(
            **{key: _count(row, key) for key in QuestUserStats.model_fields},
        )
