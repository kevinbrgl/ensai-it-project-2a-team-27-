"""Data Access Object for reading statistics."""

from psycopg2 import Error as DBError
from psycopg2.extras import RealDictCursor

from src.models.stats import GenreCount
from src.utils.exceptions import DAOError


class StatsDAO:
    """DAO class computing a user's reading statistics."""

    def __init__(self, cursor: RealDictCursor) -> None:
        """Initialize StatsDAO with a database cursor.

        :param cursor: Database cursor
        """
        self.cur = cursor

    def count_finished_books(self, id_user: int) -> int:
        """Count the books a user has finished reading.

        :param id_user: ID of the user
        :raises DAOError: If a DB error occurs
        :return: Number of books with the COMPLETED state
        """
        try:
            self.cur.execute(
                """
                SELECT COUNT(*) AS count
                FROM user_book_activities
                WHERE id_user = %s AND state = 'COMPLETED'
                """,
                (id_user,),
            )
            row = self.cur.fetchone()

        except DBError as exc:
            raise DAOError from exc

        return row["count"] if row else 0

    def count_genres(self, id_user: int) -> list[GenreCount]:
        """Count the books read or being read by a user, by category.

        Books the user only wants to read are not counted.

        :param id_user: ID of the user
        :raises DAOError: If a DB error occurs
        :return: One entry per category, the most frequent first
        """
        try:
            self.cur.execute(
                """
                SELECT category, COUNT(*) AS count
                FROM user_book_activities
                JOIN books ON books.id_book = user_book_activities.id_book
                WHERE user_book_activities.id_user = %s
                  AND user_book_activities.state IN ('READING', 'COMPLETED')
                GROUP BY books.category
                ORDER BY count DESC, books.category
                """,
                (id_user,),
            )
            rows = self.cur.fetchall()

        except DBError as exc:
            raise DAOError from exc

        return [GenreCount(**row) for row in rows]

    def count_ratings(self, id_user: int) -> dict[int, int]:
        """Count the reviews written by a user, by rating.

        :param id_user: ID of the user
        :raises DAOError: If a DB error occurs
        :return: The number of reviews for each rating that was used
        """
        try:
            self.cur.execute(
                """
                SELECT rating, COUNT(*) AS count
                FROM reviews
                WHERE id_user = %s
                GROUP BY rating
                """,
                (id_user,),
            )
            rows = self.cur.fetchall()

        except DBError as exc:
            raise DAOError from exc

        return {row["rating"]: row["count"] for row in rows}
