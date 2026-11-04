"""Service layer for review operations."""

from src.dao.books_dao import BookDAO
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
    NotReviewAuthorError,
    UserNotFoundError,
)


class ReviewService:
    """Service class for managing reviews and ratings."""

    def __init__(
        self,
        review_dao: ReviewDAO,
        book_dao: BookDAO,
        user_dao: UserDAO,
    ) -> None:
        """Initialize the service with its DAOs.

        :param review_dao: The review data access object
        :param book_dao: The book data access object
        :param user_dao: The user data access object
        """
        self.review_dao = review_dao
        self.book_dao = book_dao
        self.user_dao = user_dao

    def get_book_reviews(self, id_book: int) -> BookReviews:
        """Return the reviews of a book and its average rating.

        :param id_book: ID of the book
        :raises BookNotFoundError: If the book does not exist
        :return: The reviews, the average rating and the number of reviews
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
        """Write a review on a book.

        :param id_user: ID of the author
        :param id_book: ID of the book
        :param review_in: Rating and comment of the review
        :return: The created review
        """
        return self.review_dao.create(id_user, id_book, review_in)

    def _check_author(self, id_user: int, id_review: int) -> None:
        """Make sure that the user wrote the review.

        :param id_user: ID of the user making the request
        :param id_review: ID of the review
        :raises ReviewNotFoundError: If the review does not exist
        :raises NotReviewAuthorError: If the user is not the author
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
        """Edit a review, only if the user is its author.

        :param id_user: ID of the user making the request
        :param id_review: ID of the review
        :param review_in: New rating and comment
        :return: The updated review
        """
        self._check_author(id_user, id_review)
        return self.review_dao.update(id_review, review_in)

    def delete_review(self, id_user: int, id_review: int) -> None:
        """Delete a review, only if the user is its author.

        :param id_user: ID of the user making the request
        :param id_review: ID of the review
        """
        self._check_author(id_user, id_review)
        self.review_dao.delete(id_review)

    def list_user_reviews(self, id_user: int) -> list[ReviewRead]:
        """List the reviews written by a user.

        :param id_user: ID of the user
        :raises UserNotFoundError: If the user does not exist
        :return: The reviews, or an empty list if there are none
        """
        if self.user_dao.read(id_user) is None:
            raise UserNotFoundError(user_id=id_user)
        return self.review_dao.find_by_user_id(id_user)
