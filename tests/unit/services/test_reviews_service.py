"""Unit tests for ReviewService.

The DAOs are replaced by mocks: no database is needed.
"""

from datetime import UTC, datetime
from unittest.mock import Mock

import pytest
from pytest_mock import MockerFixture

from src.dao.books_dao import BookDAO
from src.dao.reviews_dao import ReviewDAO
from src.dao.users_dao import UserDAO
from src.models.reviews import ReviewCreate, ReviewRead, ReviewUpdate
from src.services.reviews_service import ReviewService
from src.utils.exceptions import (
    BookNotFoundError,
    NotReviewAuthorError,
    ReviewNotFoundError,
    UserNotFoundError,
)

AUTHOR_ID = 1
OTHER_USER_ID = 2
ID_BOOK = 100
ID_REVIEW = 10
AVERAGE = 3.5
COUNT = 2


@pytest.fixture
def review_dao(mocker: MockerFixture) -> Mock:
    """Return a fake ReviewDAO."""
    return mocker.Mock(spec=ReviewDAO)


@pytest.fixture
def book_dao(mocker: MockerFixture) -> Mock:
    """Return a fake BookDAO."""
    return mocker.Mock(spec=BookDAO)


@pytest.fixture
def user_dao(mocker: MockerFixture) -> Mock:
    """Return a fake UserDAO."""
    return mocker.Mock(spec=UserDAO)


@pytest.fixture
def service(
    review_dao: Mock,
    book_dao: Mock,
    user_dao: Mock,
) -> ReviewService:
    """Return a ReviewService using the mocked DAOs."""
    return ReviewService(review_dao, book_dao, user_dao)


@pytest.fixture
def review() -> ReviewRead:
    """Return a review written by AUTHOR_ID."""
    return ReviewRead(
        id_review=ID_REVIEW,
        id_user=AUTHOR_ID,
        id_book=ID_BOOK,
        rating=4,
        comment="Very good book",
        created_at=datetime.now(tz=UTC),
    )


class TestGetBookReviews:
    """Tests for ReviewService.get_book_reviews."""

    def test_returns_reviews_and_average(
        self,
        service: ReviewService,
        review_dao: Mock,
        book_dao: Mock,
        review: ReviewRead,
    ) -> None:
        """Existing book: reviews, average and count are returned."""
        book_dao.read.return_value = Mock()
        review_dao.find_by_book_id.return_value = [review]
        review_dao.get_rating_stats.return_value = (AVERAGE, COUNT)

        result = service.get_book_reviews(ID_BOOK)

        assert result.id_book == ID_BOOK
        assert result.average_rating == AVERAGE
        assert result.review_count == COUNT
        assert result.reviews == [review]

    def test_no_reviews_gives_no_average(
        self,
        service: ReviewService,
        review_dao: Mock,
        book_dao: Mock,
    ) -> None:
        """Book without reviews: average is None and count is 0."""
        book_dao.read.return_value = Mock()
        review_dao.find_by_book_id.return_value = []
        review_dao.get_rating_stats.return_value = (None, 0)

        result = service.get_book_reviews(ID_BOOK)

        assert result.average_rating is None
        assert result.review_count == 0
        assert result.reviews == []

    def test_unknown_book_raises(
        self,
        service: ReviewService,
        review_dao: Mock,
        book_dao: Mock,
    ) -> None:
        """Unknown book: BookNotFoundError, reviews are not read."""
        book_dao.read.return_value = None

        with pytest.raises(BookNotFoundError):
            service.get_book_reviews(ID_BOOK)

        review_dao.find_by_book_id.assert_not_called()


class TestCreateReview:
    """Tests for ReviewService.create_review."""

    def test_calls_dao(
        self,
        service: ReviewService,
        review_dao: Mock,
        review: ReviewRead,
    ) -> None:
        """The review is created by the DAO and returned."""
        review_in = ReviewCreate(rating=4, comment="Very good book")
        review_dao.create.return_value = review

        result = service.create_review(AUTHOR_ID, ID_BOOK, review_in)

        assert result == review
        review_dao.create.assert_called_once_with(
            AUTHOR_ID,
            ID_BOOK,
            review_in,
        )


class TestUpdateReview:
    """Tests for ReviewService.update_review."""

    def test_author_can_update(
        self,
        service: ReviewService,
        review_dao: Mock,
        review: ReviewRead,
    ) -> None:
        """The author can edit the review."""
        review_in = ReviewUpdate(rating=5)
        review_dao.find_by_id.return_value = review
        review_dao.update.return_value = review

        result = service.update_review(AUTHOR_ID, ID_REVIEW, review_in)

        assert result == review
        review_dao.update.assert_called_once_with(ID_REVIEW, review_in)

    def test_other_user_cannot_update(
        self,
        service: ReviewService,
        review_dao: Mock,
        review: ReviewRead,
    ) -> None:
        """Another user gets NotReviewAuthorError and nothing changes."""
        review_dao.find_by_id.return_value = review

        with pytest.raises(NotReviewAuthorError):
            service.update_review(
                OTHER_USER_ID,
                ID_REVIEW,
                ReviewUpdate(rating=1),
            )

        review_dao.update.assert_not_called()

    def test_unknown_review_raises(
        self,
        service: ReviewService,
        review_dao: Mock,
    ) -> None:
        """Unknown review: ReviewNotFoundError, nothing changes."""
        review_dao.find_by_id.side_effect = ReviewNotFoundError(ID_REVIEW)

        with pytest.raises(ReviewNotFoundError):
            service.update_review(
                AUTHOR_ID,
                ID_REVIEW,
                ReviewUpdate(rating=5),
            )

        review_dao.update.assert_not_called()


class TestDeleteReview:
    """Tests for ReviewService.delete_review."""

    def test_author_can_delete(
        self,
        service: ReviewService,
        review_dao: Mock,
        review: ReviewRead,
    ) -> None:
        """The author can delete the review."""
        review_dao.find_by_id.return_value = review

        service.delete_review(AUTHOR_ID, ID_REVIEW)

        review_dao.delete.assert_called_once_with(ID_REVIEW)

    def test_other_user_cannot_delete(
        self,
        service: ReviewService,
        review_dao: Mock,
        review: ReviewRead,
    ) -> None:
        """Another user gets NotReviewAuthorError and nothing is deleted."""
        review_dao.find_by_id.return_value = review

        with pytest.raises(NotReviewAuthorError):
            service.delete_review(OTHER_USER_ID, ID_REVIEW)

        review_dao.delete.assert_not_called()


class TestListUserReviews:
    """Tests for ReviewService.list_user_reviews."""

    def test_returns_reviews(
        self,
        service: ReviewService,
        review_dao: Mock,
        user_dao: Mock,
        review: ReviewRead,
    ) -> None:
        """Existing user: their reviews are returned."""
        user_dao.read.return_value = Mock()
        review_dao.find_by_user_id.return_value = [review]

        assert service.list_user_reviews(AUTHOR_ID) == [review]

    def test_unknown_user_raises(
        self,
        service: ReviewService,
        review_dao: Mock,
        user_dao: Mock,
    ) -> None:
        """Unknown user: UserNotFoundError, reviews are not read."""
        user_dao.read.return_value = None

        with pytest.raises(UserNotFoundError):
            service.list_user_reviews(AUTHOR_ID)

        review_dao.find_by_user_id.assert_not_called()
