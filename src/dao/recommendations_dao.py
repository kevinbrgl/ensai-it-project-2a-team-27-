"""Data Access Object for book recommendations."""

from psycopg2 import Error as DBError
from psycopg2.extras import RealDictCursor

from src.models.books import Book
from src.models.stats import GenreCount
from src.utils.exceptions import DAOError


class RecommendationDAO:
    """DAO class for the queries used to recommend books."""

    def __init__(self, cursor: RealDictCursor) -> None:
        """Initialize RecommendationDAO with a database cursor.

        :param cursor: Database cursor
        """
        self.cur = cursor

    def count_rated_genres(
        self,
        id_user: int,
        min_rating: int,
    ) -> list[GenreCount]:
        """Count the books a user rated at least min_rating, by category.

        :param id_user: ID of the user
        :param min_rating: Minimum rating for a book to be counted
        :raises DAOError: If a DB error occurs
        :return: One entry per category, the most frequent first
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

        :param id_user: ID of the user
        :raises DAOError: If a DB error occurs
        :return: The id_book_api of every library book that has one
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
        """Return the local average rating of several books.

        :param book_ids: IDs of the books
        :raises DAOError: If a DB error occurs
        :return: The average rating (2 decimals) of each reviewed book;
            books without reviews are absent
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
        """Return the best rated books that are not in a user's library.

        :param id_user: ID of the user whose library is excluded
        :param limit: Maximum number of books to return
        :param category: Optional category filter
        :raises DAOError: If a DB error occurs
        :return: The books with their average rating, best first
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
