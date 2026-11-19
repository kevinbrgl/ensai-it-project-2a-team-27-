"""Database access for user achievement metrics.

Provides aggregated reading, community, social, and collection stats.
All database errors are caught and re-raised as DAOError.
"""

from typing import Any

from psycopg2 import Error as DBError
from psycopg2.extras import RealDictCursor

from src.models.achievements import AchievementUserStats
from src.utils.exceptions import DAOError

# Books first published before this date count as classics.
CLASSIC_CUTOFF = "1950-01-01"
# Minimum comment length, in characters, of a detailed review.
DETAILED_REVIEW_LENGTH = 200

ACTIVITY_QUERY = """
    SELECT
        COUNT(*) AS library_size,
        COUNT(*) FILTER (WHERE uba.state = 'COMPLETED') AS completed_books,
        COUNT(*) FILTER (WHERE uba.state = 'READING') AS reading_books,
        COUNT(*) FILTER (
            WHERE uba.state = 'WANT_TO_READ'
        ) AS want_to_read_books,
        COUNT(*) FILTER (WHERE uba.state = 'ABANDONED') AS abandoned_books,
        COALESCE(SUM(b.num_pages) FILTER (
            WHERE uba.state = 'COMPLETED'
              AND b.num_pages IS NOT NULL
        ), 0) AS pages_read,
        COALESCE(MAX(b.num_pages) FILTER (
            WHERE uba.state = 'COMPLETED'
        ), 0) AS longest_book_pages,
        COUNT(DISTINCT b.category) FILTER (
            WHERE b.category IS NOT NULL
              AND TRIM(b.category) <> ''
        ) AS distinct_genres,
        COUNT(DISTINCT LOWER(TRIM(b.author))) FILTER (
            WHERE uba.state = 'COMPLETED'
              AND b.author IS NOT NULL
              AND TRIM(b.author) <> ''
        ) AS distinct_authors,
        COUNT(*) FILTER (
            WHERE uba.state = 'COMPLETED'
              AND b.publish_date < %(classic_cutoff)s::date
        ) AS classics_read,
        COUNT(*) FILTER (
            WHERE uba.state = 'COMPLETED'
              AND uba.finished_at IS NOT NULL
        ) AS dated_books,
        COUNT(*) FILTER (WHERE uba.is_favorite = TRUE) AS favorites_count,
        COUNT(*) FILTER (WHERE uba.is_liked = TRUE) AS liked_books
    FROM user_book_activities uba
    LEFT JOIN books b ON uba.id_book = b.id_book
    WHERE uba.id_user = %(user_id)s;
"""

SOCIAL_QUERY = """
    SELECT
        (
            SELECT COUNT(*)
            FROM reviews
            WHERE id_user = %(user_id)s
        ) AS reviews_count,
        (
            SELECT COUNT(*)
            FROM reviews
            WHERE id_user = %(user_id)s
              AND LENGTH(TRIM(COALESCE(comment, ''))) >= %(detailed_length)s
        ) AS detailed_reviews,
        (
            SELECT COUNT(*)
            FROM reviews
            WHERE id_user = %(user_id)s
              AND rating = 5
        ) AS five_star_reviews,
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
            FROM playlists
            WHERE id_user = %(user_id)s
        ) AS playlists_count,
        (
            SELECT COALESCE(MAX(sizes.book_count), 0)
            FROM (
                SELECT COUNT(pb.id_book) AS book_count
                FROM playlists p
                LEFT JOIN playlist_books pb ON pb.id_playlist = p.id_playlist
                WHERE p.id_user = %(user_id)s
                GROUP BY p.id_playlist
            ) sizes
        ) AS largest_playlist,
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


class AchievementDAO:
    """Query the reading and social metrics used to award achievements.

    Attributes
    ----------
    cur : RealDictCursor
        PostgreSQL cursor that fetches rows as dictionaries.

    """

    def __init__(self, cur: RealDictCursor) -> None:
        """Initialize the AchievementDAO with a database cursor.

        Parameters
        ----------
        cur : RealDictCursor
            Database cursor that yields rows as dictionaries.

        """
        self.cur = cur

    def get_user_stats(self, user_id: int) -> AchievementUserStats:
        """Retrieve aggregated achievement metrics for a user.

        Parameters
        ----------
        user_id : int
            ID of the user whose metrics to compute.

        Returns
        -------
        AchievementUserStats
            Aggregate library, reading, review, follow, playlist, and
            profile metrics.

        Raises
        ------
        DAOError
            If a database error occurs.

        """
        params = {
            "user_id": user_id,
            "classic_cutoff": CLASSIC_CUTOFF,
            "detailed_length": DETAILED_REVIEW_LENGTH,
        }
        try:
            self.cur.execute(ACTIVITY_QUERY, params)
            activity_row: dict[str, Any] = self.cur.fetchone() or {}

            self.cur.execute(SOCIAL_QUERY, params)
            social_row: dict[str, Any] = self.cur.fetchone() or {}

        except DBError as exc:
            raise DAOError from exc

        row = {**activity_row, **social_row}
        return AchievementUserStats(
            **{
                key: _count(row, key)
                for key in AchievementUserStats.model_fields
            },
        )
