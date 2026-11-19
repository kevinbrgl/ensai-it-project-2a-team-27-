"""Data Access Object for user achievement metrics.

Provides aggregated reading, community, social, and collection stats.
All database errors are caught and re-raised as DAOError.
"""

from typing import Any

from psycopg2 import Error as DBError
from psycopg2.extras import RealDictCursor

from src.models.achievements import AchievementUserStats
from src.utils.exceptions import DAOError


class AchievementDAO:
    """DAO class querying aggregated user statistics for achievements.

    :attr cur: Database cursor (RealDictCursor)
    """

    def __init__(self, cur: RealDictCursor) -> None:
        """Initialize the AchievementDAO with a database cursor.

        :param cur: psycopg2 RealDictCursor
        """
        self.cur = cur

    def get_user_stats(self, user_id: int) -> AchievementUserStats:
        """Retrieve aggregated achievement metrics for a user.

        :param user_id: ID of the user whose metrics to compute
        :raises DAOError: If a database error occurs
        :return: AchievementUserStats containing reading and social counts
        """
        try:
            self.cur.execute(
                """
                SELECT
                    COALESCE(COUNT(*) FILTER (
                        WHERE uba.state = 'COMPLETED'
                    ), 0) AS completed_books,
                    COALESCE(SUM(b.num_pages) FILTER (
                        WHERE uba.state = 'COMPLETED'
                          AND b.num_pages IS NOT NULL
                    ), 0) AS pages_read,
                    COALESCE(COUNT(DISTINCT b.category) FILTER (
                        WHERE b.category IS NOT NULL
                          AND TRIM(b.category) <> ''
                    ), 0) AS distinct_genres,
                    COALESCE(COUNT(*) FILTER (
                        WHERE uba.is_favorite = TRUE
                    ), 0) AS favorites_count
                FROM user_book_activities uba
                LEFT JOIN books b ON uba.id_book = b.id_book
                WHERE uba.id_user = %s;
                """,
                (user_id,),
            )
            activity_row: dict[str, Any] = self.cur.fetchone() or {}

            self.cur.execute(
                """
                SELECT
                    (
                        SELECT COUNT(*)
                        FROM reviews
                        WHERE id_user = %s
                    ) AS reviews_count,
                    (
                        SELECT COUNT(*)
                        FROM user_follows
                        WHERE follower_id = %s
                    ) AS following_count,
                    (
                        SELECT COUNT(*)
                        FROM user_follows
                        WHERE following_id = %s
                    ) AS followers_count,
                    (
                        SELECT COUNT(*)
                        FROM playlists
                        WHERE id_user = %s
                    ) AS playlists_count;
                """,
                (user_id, user_id, user_id, user_id),
            )
            social_row: dict[str, Any] = self.cur.fetchone() or {}

            return AchievementUserStats(
                completed_books=int(activity_row.get("completed_books", 0)),
                pages_read=int(activity_row.get("pages_read", 0)),
                distinct_genres=int(activity_row.get("distinct_genres", 0)),
                favorites_count=int(activity_row.get("favorites_count", 0)),
                reviews_count=int(social_row.get("reviews_count", 0)),
                following_count=int(social_row.get("following_count", 0)),
                followers_count=int(social_row.get("followers_count", 0)),
                playlists_count=int(social_row.get("playlists_count", 0)),
            )

        except DBError as exc:
            raise DAOError from exc
