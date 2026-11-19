"""Database access for book reviews and rating statistics."""

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
    """Manage book reviews and query their ratings."""

    def __init__(self, cursor: RealDictCursor) -> None:
        """Initialize ReviewDAO with a database cursor.

        Parameters
        ----------
        cursor : RealDictCursor
            Database cursor that yields rows as dictionaries.

        """
        self.cur = cursor

    def create(
        self,
        id_user: int,
        id_book: int,
        review_in: ReviewCreate,
    ) -> ReviewRead:
        """Store a user's review of a book.

        Parameters
        ----------
        id_user : int
            ID of the user writing the review.
        id_book : int
            ID of the reviewed book.
        review_in : ReviewCreate
            Rating and comment of the review.

        Returns
        -------
        ReviewRead
            The created review.

        Raises
        ------
        ReviewAlreadyExistsError
            If the user already reviewed the book.
        BookNotFoundError
            If the database rejects a missing user or book reference.
        DAOError
            If a database error occurs.

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
        """Find a review by its ID.

        Parameters
        ----------
        id_review : int
            ID of the review.

        Returns
        -------
        ReviewRead
            The review.

        Raises
        ------
        ReviewNotFoundError
            If the review is missing.
        DAOError
            If a database error occurs.

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

        Parameters
        ----------
        id_book : int
            ID of the book.

        Returns
        -------
        list[ReviewRead]
            The reviews, or an empty list if there are none.

        Raises
        ------
        DAOError
            If a database error occurs.

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

        Parameters
        ----------
        id_user : int
            ID of the user.

        Returns
        -------
        list[ReviewRead]
            The reviews, or an empty list if there are none.

        Raises
        ------
        DAOError
            If a database error occurs.

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
        """Return a book's average rating and review count.

        Parameters
        ----------
        id_book : int
            ID of the book.

        Returns
        -------
        tuple[float | None, int]
            Average rating rounded to two decimal places and number of reviews.
            For a book without reviews, return None and zero.

        Raises
        ------
        DAOError
            If a database error occurs.

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

        Parameters
        ----------
        id_review : int
            ID of the review.
        review_in : ReviewUpdate
            New rating and comment.

        Returns
        -------
        ReviewRead
            The updated review.

        Raises
        ------
        ReviewNotFoundError
            If the review is missing.
        DAOError
            If a database error occurs.

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

        Parameters
        ----------
        id_review : int
            ID of the review.

        Raises
        ------
        ReviewNotFoundError
            If the review is missing.
        DAOError
            If a database error occurs.

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
