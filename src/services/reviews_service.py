"""Service layer for review operations."""

from src.dao.books_dao import BookDAO
from src.dao.library_dao import LibraryDAO
from src.dao.reviews_dao import ReviewDAO
from src.dao.users_dao import UserDAO
from src.models.reviews import (
    BookReviews,
    ReviewCreate,
    ReviewRead,
    ReviewUpdate,
)
from src.utils.exceptions import (
    BookNotFoundError,
    BookNotInLibraryError,
    NotReviewAuthorError,
    UserNotFoundError,
)


class ReviewService:
    """Manage book reviews and ratings."""

    def __init__(
        self,
        review_dao: ReviewDAO,
        book_dao: BookDAO,
        user_dao: UserDAO,
        library_dao: LibraryDAO,
    ) -> None:
        """Initialize the service with its DAOs.

        Parameters
        ----------
        review_dao : ReviewDAO
            The review data access object.
        book_dao : BookDAO
            The book data access object.
        user_dao : UserDAO
            The user data access object.
        library_dao : LibraryDAO
            The library data access object.

        """
        self.review_dao = review_dao
        self.book_dao = book_dao
        self.user_dao = user_dao
        self.library_dao = library_dao

    def get_book_reviews(self, id_book: int) -> BookReviews:
        """Return the reviews of a book and its average rating.

        Parameters
        ----------
        id_book : int
            ID of the book.

        Returns
        -------
        BookReviews
            The reviews, the average rating and the number of reviews.

        Raises
        ------
        BookNotFoundError
            If the book does not exist.

        """
        if self.book_dao.read(id_book) is None:
            raise BookNotFoundError(id_book)

        reviews = self.review_dao.find_by_book_id(id_book)
        average, count = self.review_dao.get_rating_stats(id_book)
        return BookReviews(
            id_book=id_book,
            average_rating=average,
            review_count=count,
            reviews=reviews,
        )

    def create_review(
        self,
        id_user: int,
        id_book: int,
        review_in: ReviewCreate,
    ) -> ReviewRead:
        """Write a review on a book of the user's library.

        Parameters
        ----------
        id_user : int
            ID of the author.
        id_book : int
            ID of the book.
        review_in : ReviewCreate
            Rating and comment of the review.

        Returns
        -------
        ReviewRead
            The created review.

        Raises
        ------
        BookNotFoundError
            If the book does not exist.
        BookNotInLibraryError
            If the book is not in the author's library.

        Notes
        -----
        A second review of the same book by this user raises
        ``ReviewAlreadyExistsError``.

        """
        if self.book_dao.read(id_book) is None:
            raise BookNotFoundError(id_book)
        if self.library_dao.read(id_user, id_book) is None:
            raise BookNotInLibraryError(id_book)
        return self.review_dao.create(id_user, id_book, review_in)

    def _check_author(self, id_user: int, id_review: int) -> None:
        """Verify that the user authored the review.

        Parameters
        ----------
        id_user : int
            ID of the user making the request.
        id_review : int
            ID of the review.

        Raises
        ------
        NotReviewAuthorError
            If the request came from a user other than the author.

        Notes
        -----
        A missing review raises ``ReviewNotFoundError``.

        """
        review = self.review_dao.find_by_id(id_review)
        if review.id_user != id_user:
            raise NotReviewAuthorError(id_review)

    def update_review(
        self,
        id_user: int,
        id_review: int,
        review_in: ReviewUpdate,
    ) -> ReviewRead:
        """Update a review as its author.

        Parameters
        ----------
        id_user : int
            ID of the user making the request.
        id_review : int
            ID of the review.
        review_in : ReviewUpdate
            New rating and comment.

        Returns
        -------
        ReviewRead
            The updated review.

        Notes
        -----
        A missing review raises ``ReviewNotFoundError``. A request from
        someone other than the author raises ``NotReviewAuthorError``.

        """
        self._check_author(id_user, id_review)
        return self.review_dao.update(id_review, review_in)

    def delete_review(self, id_user: int, id_review: int) -> None:
        """Delete a review, only if the user is its author.

        Parameters
        ----------
        id_user : int
            ID of the user making the request.
        id_review : int
            ID of the review.

        Notes
        -----
        A missing review raises ``ReviewNotFoundError``. A request from
        someone other than the author raises ``NotReviewAuthorError``.

        """
        self._check_author(id_user, id_review)
        self.review_dao.delete(id_review)

    def list_user_reviews(self, id_user: int) -> list[ReviewRead]:
        """List the reviews written by a user.

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
        UserNotFoundError
            If the user does not exist.

        """
        if self.user_dao.read(id_user) is None:
            raise UserNotFoundError(user_id=id_user)
        return self.review_dao.find_by_user_id(id_user)
