"""Database access for reading and rating statistics."""

from psycopg2 import Error as DBError
from psycopg2.extras import RealDictCursor

from src.models.stats import GenreCount
from src.utils.exceptions import DAOError


class StatsDAO:
    """Aggregate a user's reading activity and ratings."""

    def __init__(self, cursor: RealDictCursor) -> None:
        """Initialize StatsDAO with a database cursor.

        Parameters
        ----------
        cursor : RealDictCursor
            Database cursor that yields rows as dictionaries.

        """
        self.cur = cursor

    def count_finished_books(self, id_user: int) -> int:
        """Count the books a user has finished reading.

        Parameters
        ----------
        id_user : int
            ID of the user.

        Returns
        -------
        int
            Number of books with the COMPLETED reading state.

        Raises
        ------
        DAOError
            If a database error occurs.

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

    def sum_pages_read(self, id_user: int) -> int:
        """Sum the pages of the books a user has finished reading.

        Books with an unknown page count contribute zero pages.

        Parameters
        ----------
        id_user : int
            ID of the user.

        Returns
        -------
        int
            Total number of pages across completed books.

        Raises
        ------
        DAOError
            If a database error occurs.

        """
        try:
            self.cur.execute(
                """
                SELECT COALESCE(SUM(books.num_pages), 0) AS pages
                FROM user_book_activities
                JOIN books ON books.id_book = user_book_activities.id_book
                WHERE user_book_activities.id_user = %s
                  AND user_book_activities.state = 'COMPLETED'
                """,
                (id_user,),
            )
            row = self.cur.fetchone()

        except DBError as exc:
            raise DAOError from exc

        return int(row["pages"]) if row else 0

    def count_genres(self, id_user: int) -> list[GenreCount]:
        """Count books a user is reading or has finished, by category.

        Parameters
        ----------
        id_user : int
            ID of the user.

        Returns
        -------
        list[GenreCount]
            One count per category, ordered by descending count and then
            category name.

        Raises
        ------
        DAOError
            If a database error occurs.

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

        Parameters
        ----------
        id_user : int
            ID of the user.

        Returns
        -------
        dict[int, int]
            The number of reviews for each rating that was used.

        Raises
        ------
        DAOError
            If a database error occurs.

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
