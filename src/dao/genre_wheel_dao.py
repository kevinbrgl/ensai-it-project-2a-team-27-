"""Database access for data used to build genre wheels.

Queries completed books, categories, favorite flags, and ratings
for a specific user to compute the avatar genre proportions.
"""

from typing import Any

from psycopg2 import Error as DBError
from psycopg2.extras import RealDictCursor

from src.utils.exceptions import DAOError


class GenreWheelDAO:
    """Retrieve reading activity and ratings for genre wheels.

    Attributes
    ----------
    cur : RealDictCursor
        PostgreSQL cursor that fetches rows as dictionaries.

    """

    def __init__(self, cur: RealDictCursor) -> None:
        """Initialize GenreWheelDAO with a database cursor.

        Parameters
        ----------
        cur : RealDictCursor
            Database cursor that yields rows as dictionaries.

        """
        self.cur = cur

    def get_user_completed_books(
        self,
        user_id: int,
    ) -> list[dict[str, Any]]:
        """Retrieve categorized books a user has finished reading.

        Parameters
        ----------
        user_id : int
            ID of the user whose completed books to retrieve.

        Returns
        -------
        list[dict[str, Any]]
            One dictionary per book with id_book, category, is_favorite, and
            rating. An unreviewed book has a rating of None.

        """
        return self.get_completed_books_by_user([user_id]).get(user_id, [])

    def get_completed_books_by_user(
        self,
        user_ids: list[int],
    ) -> dict[int, list[dict[str, Any]]]:
        """Load categorized, completed books for several readers at once.

        Parameters
        ----------
        user_ids : list[int]
            Readers whose wheels the viewer may see.

        Raises
        ------
        DAOError
            If a database error occurs.

        """
        if not user_ids:
            return {}
        try:
            self.cur.execute(
                """
                SELECT
                    uba.id_user,
                    b.id_book,
                    b.category,
                    uba.is_favorite,
                    r.rating
                FROM user_book_activities uba
                JOIN books b ON b.id_book = uba.id_book
                LEFT JOIN reviews r
                    ON r.id_book = uba.id_book
                   AND r.id_user = uba.id_user
                WHERE uba.id_user = ANY(%s)
                  AND uba.state = 'COMPLETED'
                  AND b.category IS NOT NULL
                  AND TRIM(b.category) <> ''
                ORDER BY uba.id_user, uba.id_book;
                """,
                (user_ids,),
            )
            rows = self.cur.fetchall()
        except DBError as exc:
            raise DAOError from exc
        grouped: dict[int, list[dict[str, Any]]] = {}
        for row in rows:
            book = dict(row)
            grouped.setdefault(book.pop("id_user"), []).append(book)
        return grouped
