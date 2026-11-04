"""Data Access Object for review operations."""

from psycopg2 import Error as DBError
from psycopg2.errors import ForeignKeyViolation
from psycopg2.extras import RealDictCursor

from src.models.reviews import ReviewCreate, ReviewRead, ReviewUpdate
from src.utils.exceptions import (
    BookNotFoundError,
    DAOError,
    ReviewAlreadyExistsError,
    ReviewNotFoundError,
)


class ReviewDAO:
    """DAO class for review operations."""

    def __init__(self, cursor: RealDictCursor) -> None:
        """Initialize ReviewDAO with a database cursor.

        :param cursor: Database cursor
        """
        self.cur = cursor

    def create(
        self,
        id_user: int,
        id_book: int,
        review_in: ReviewCreate,
    ) -> ReviewRead:
        """Insert a review written by a user on a book.

        :param id_user: ID of the author
        :param id_book: ID of the reviewed book
        :param review_in: Rating and comment of the review
        :raises ReviewAlreadyExistsError: If the user already reviewed the book
        :raises BookNotFoundError: If the book does not exist
        :raises DAOError: If a DB error occurs
        :return: The created review
        """
        try:
            self.cur.execute(
                """
                INSERT INTO reviews (id_user, id_book, rating, comment)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (id_user, id_book) DO NOTHING
                RETURNING *
                """,
                (id_user, id_book, review_in.rating, review_in.comment),
            )
            row = self.cur.fetchone()

        except ForeignKeyViolation:
            raise BookNotFoundError(id_book) from None
        except DBError as exc:
            raise DAOError from exc

        if row is None:
            raise ReviewAlreadyExistsError(id_book)
        return ReviewRead(**row)

    def find_by_id(self, id_review: int) -> ReviewRead:
        """Return one review.

        :param id_review: ID of the review
        :raises ReviewNotFoundError: If the review does not exist
        :raises DAOError: If a DB error occurs
        :return: The review
        """
        try:
            self.cur.execute(
                "SELECT * FROM reviews WHERE id_review = %s",
                (id_review,),
            )
            row = self.cur.fetchone()

        except DBError as exc:
            raise DAOError from exc

        if row is None:
            raise ReviewNotFoundError(id_review)
        return ReviewRead(**row)

    def find_by_book_id(self, id_book: int) -> list[ReviewRead]:
        """List the reviews of a book, newest first.

        :param id_book: ID of the book
        :raises DAOError: If a DB error occurs
        :return: The reviews, or an empty list if there are none
        """
        try:
            self.cur.execute(
                """
                SELECT * FROM reviews
                WHERE id_book = %s
                ORDER BY created_at DESC, id_review DESC
                """,
                (id_book,),
            )
            rows = self.cur.fetchall()

        except DBError as exc:
            raise DAOError from exc

        return [ReviewRead(**row) for row in rows]

    def find_by_user_id(self, id_user: int) -> list[ReviewRead]:
        """List the reviews written by a user, newest first.

        :param id_user: ID of the user
        :raises DAOError: If a DB error occurs
        :return: The reviews, or an empty list if there are none
        """
        try:
            self.cur.execute(
                """
                SELECT * FROM reviews
                WHERE id_user = %s
                ORDER BY created_at DESC, id_review DESC
                """,
                (id_user,),
            )
            rows = self.cur.fetchall()

        except DBError as exc:
            raise DAOError from exc

        return [ReviewRead(**row) for row in rows]

    def get_rating_stats(self, id_book: int) -> tuple[float | None, int]:
        """Return the average rating and the number of reviews of a book.

        :param id_book: ID of the book
        :raises DAOError: If a DB error occurs
        :return: (average rounded to 2 decimals or None, number of reviews)
        """
        try:
            self.cur.execute(
                """
                SELECT AVG(rating) AS average_rating,
                       COUNT(*)    AS review_count
                FROM reviews
                WHERE id_book = %s
                """,
                (id_book,),
            )
            row = self.cur.fetchone()

        except DBError as exc:
            raise DAOError from exc

        if row is None:
            return None, 0

        average = row["average_rating"]
        if average is not None:
            average = round(float(average), 2)
        return average, row["review_count"]

    def update(self, id_review: int, review_in: ReviewUpdate) -> ReviewRead:
        """Update the rating and comment of a review.

        :param id_review: ID of the review
        :param review_in: New rating and comment
        :raises ReviewNotFoundError: If the review does not exist
        :raises DAOError: If a DB error occurs
        :return: The updated review
        """
        try:
            self.cur.execute(
                """
                UPDATE reviews
                SET rating = %s, comment = %s
                WHERE id_review = %s
                RETURNING *
                """,
                (review_in.rating, review_in.comment, id_review),
            )
            row = self.cur.fetchone()

        except DBError as exc:
            raise DAOError from exc

        if row is None:
            raise ReviewNotFoundError(id_review)
        return ReviewRead(**row)

    def delete(self, id_review: int) -> None:
        """Delete a review.

        :param id_review: ID of the review
        :raises ReviewNotFoundError: If the review does not exist
        :raises DAOError: If a DB error occurs
        """
        try:
            self.cur.execute(
                """
                DELETE FROM reviews
                WHERE id_review = %s
                RETURNING id_review
                """,
                (id_review,),
            )
            row = self.cur.fetchone()

        except DBError as exc:
            raise DAOError from exc

        if row is None:
            raise ReviewNotFoundError(id_review)
