"""Data Access Object for user genre wheel calculations.

Queries completed books, categories, favorite flags, and ratings
for a specific user to compute the avatar genre proportions.
"""

from typing import Any

from psycopg2 import Error as DBError
from psycopg2.extras import RealDictCursor

from src.utils.exceptions import DAOError


class GenreWheelDAO:
    """DAO retrieving user reading activities and reviews for genre wheels.

    :attr cur: Database cursor (RealDictCursor)
    """

    def __init__(self, cur: RealDictCursor) -> None:
        """Initialize GenreWheelDAO with a database cursor.

        :param cur: psycopg2 RealDictCursor
        """
        self.cur = cur

    def get_user_completed_books(
        self,
        user_id: int,
    ) -> list[dict[str, Any]]:
        """Retrieve completed books with category, favorite flag and rating.

        :param user_id: ID of the user whose completed reads are queried
        :raises DAOError: If a database error occurs
        :return: List of dictionaries with category, is_favorite, and rating
        """
        try:
            self.cur.execute(
                """
                SELECT
                    b.id_book,
                    b.category,
                    uba.is_favorite,
                    r.rating
                FROM user_book_activities uba
                JOIN books b ON b.id_book = uba.id_book
                LEFT JOIN reviews r
                    ON r.id_book = uba.id_book
                   AND r.id_user = uba.id_user
                WHERE uba.id_user = %s
                  AND uba.state = 'COMPLETED'
                  AND b.category IS NOT NULL
                  AND TRIM(b.category) <> ''
                ORDER BY uba.id_book ASC;
                """,
                (user_id,),
            )
            rows = self.cur.fetchall()
        except DBError as exc:
            raise DAOError from exc
        else:
            return [dict(row) for row in rows] if rows else []
