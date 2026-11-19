"""Database access for user metrics used by quests.

Provides aggregated reading, library, and social metrics for users.
All database errors are wrapped in DAOError.
"""

from typing import Any

from psycopg2 import Error as DBError
from psycopg2.extras import RealDictCursor

from src.models.quests import QuestUserStats
from src.utils.exceptions import DAOError


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
            Counts of completed books, books in progress, favorites, distinct
            categories, and accounts the user follows.

        Raises
        ------
        DAOError
            If a database error occurs.

        """
        try:
            self.cur.execute(
                """
                SELECT
                    COALESCE(COUNT(*) FILTER (
                        WHERE uba.state = 'COMPLETED'
                    ), 0) AS completed_books,
                    COALESCE(COUNT(*) FILTER (
                        WHERE uba.state = 'READING'
                    ), 0) AS reading_books,
                    COALESCE(COUNT(*) FILTER (
                        WHERE uba.is_favorite = TRUE
                    ), 0) AS favorite_books,
                    COALESCE(COUNT(DISTINCT b.category) FILTER (
                        WHERE b.category IS NOT NULL
                          AND TRIM(b.category) <> ''
                    ), 0) AS distinct_categories
                FROM user_book_activities uba
                LEFT JOIN books b ON uba.id_book = b.id_book
                WHERE uba.id_user = %s;
                """,
                (user_id,),
            )
            activity_row: dict[str, Any] = self.cur.fetchone() or {}

            self.cur.execute(
                """
                SELECT COUNT(*) AS following_count
                FROM user_follows
                WHERE follower_id = %s;
                """,
                (user_id,),
            )
            follow_row: dict[str, Any] = self.cur.fetchone() or {}

            return QuestUserStats(
                completed_books=int(activity_row.get("completed_books", 0)),
                reading_books=int(activity_row.get("reading_books", 0)),
                distinct_categories=int(
                    activity_row.get("distinct_categories", 0),
                ),
                favorite_books=int(activity_row.get("favorite_books", 0)),
                following_count=int(follow_row.get("following_count", 0)),
            )

        except DBError as exc:
            raise DAOError from exc
