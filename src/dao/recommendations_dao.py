"""Database access for book recommendation queries."""

from psycopg2 import Error as DBError
from psycopg2.extras import RealDictCursor

from src.models.books import Book
from src.models.stats import GenreCount
from src.utils.exceptions import DAOError


class RecommendationDAO:
    """Query reading preferences and candidate book ratings."""

    def __init__(self, cursor: RealDictCursor) -> None:
        """Initialize RecommendationDAO with a database cursor.

        Parameters
        ----------
        cursor : RealDictCursor
            Database cursor that yields rows as dictionaries.

        """
        self.cur = cursor

    def count_rated_genres(
        self,
        id_user: int,
        min_rating: int,
    ) -> list[GenreCount]:
        """Count books that meet a user rating threshold, by category.

        Parameters
        ----------
        id_user : int
            ID of the user.
        min_rating : int
            Minimum rating for a book to be counted.

        Returns
        -------
        list[GenreCount]
            One count per nonblank category, ordered by descending count and
            then by category name.

        Raises
        ------
        DAOError
            If a database error occurs.

        """
        try:
            self.cur.execute(
                """
                SELECT b.category, COUNT(*) AS count
                FROM reviews AS r
                JOIN books AS b ON b.id_book = r.id_book
                WHERE r.id_user = %s
                  AND r.rating >= %s
                  AND b.category IS NOT NULL
                  AND TRIM(b.category) <> ''
                GROUP BY b.category
                ORDER BY count DESC, b.category
                """,
                (id_user, min_rating),
            )
            rows = self.cur.fetchall()

        except DBError as exc:
            raise DAOError from exc

        return [GenreCount(**row) for row in rows]

    def find_library_api_keys(self, id_user: int) -> set[str]:
        """Return the Open Library keys of the books in a user's library.

        Parameters
        ----------
        id_user : int
            ID of the user.

        Returns
        -------
        set[str]
            The external keys for library books that have a stored key.

        Raises
        ------
        DAOError
            If a database error occurs.

        """
        try:
            self.cur.execute(
                """
                SELECT b.id_book_api
                FROM user_book_activities AS uba
                JOIN books AS b ON b.id_book = uba.id_book
                WHERE uba.id_user = %s
                  AND b.id_book_api IS NOT NULL
                """,
                (id_user,),
            )
            rows = self.cur.fetchall()

        except DBError as exc:
            raise DAOError from exc

        return {row["id_book_api"] for row in rows}

    def get_average_ratings(self, book_ids: list[int]) -> dict[int, float]:
        """Calculate the average local rating for each requested book.

        Parameters
        ----------
        book_ids : list[int]
            IDs of the books.

        Returns
        -------
        dict[int, float]
            Average ratings rounded to two decimal places, keyed by local
            book ID. Only reviewed books appear.

        Raises
        ------
        DAOError
            If a database error occurs.

        """
        if not book_ids:
            return {}

        try:
            self.cur.execute(
                """
                SELECT id_book, AVG(rating) AS average_rating
                FROM reviews
                WHERE id_book = ANY(%s)
                GROUP BY id_book
                """,
                (book_ids,),
            )
            rows = self.cur.fetchall()

        except DBError as exc:
            raise DAOError from exc

        return {
            row["id_book"]: round(float(row["average_rating"]), 2)
            for row in rows
        }

    def find_top_rated_books(
        self,
        id_user: int,
        limit: int,
        category: str | None = None,
    ) -> list[tuple[Book, float]]:
        """Find the highest-rated books outside a user's library.

        Parameters
        ----------
        id_user : int
            ID of the user whose library books are excluded.
        limit : int
            Maximum number of books to return.
        category : str | None, optional
            Case-insensitive category substring. Defaults to None.

        Returns
        -------
        list[tuple[Book, float]]
            Books paired with average ratings rounded to two decimal places.
            Results are ordered by descending average rating, descending review
            count, and ascending book ID.

        Raises
        ------
        DAOError
            If a database error occurs.

        """
        query = """
            SELECT b.id_book, b.id_book_api, b.title, b.author,
                   b.category, b.publish_date, b.description,
                   b.cover_image,
                   AVG(r.rating) AS average_rating,
                   COUNT(r.id_review) AS review_count
            FROM reviews AS r
            JOIN books AS b ON b.id_book = r.id_book
            WHERE NOT EXISTS (
                SELECT 1
                FROM user_book_activities AS uba
                WHERE uba.id_user = %s AND uba.id_book = b.id_book
            )
        """
        params: list[int | str] = [id_user]

        if category is not None:
            query += " AND b.category ILIKE %s"
            params.append(f"%{category}%")

        query += """
            GROUP BY b.id_book
            ORDER BY average_rating DESC, review_count DESC, b.id_book
            LIMIT %s
        """
        params.append(limit)

        try:
            self.cur.execute(query, tuple(params))
            rows = self.cur.fetchall()

        except DBError as exc:
            raise DAOError from exc

        return [
            (Book(**row), round(float(row["average_rating"]), 2))
            for row in rows
        ]
