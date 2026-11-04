"""Unit tests for the review routes.

Uses FastAPI TestClient with mocked dependencies.
No database access is required.
"""

from collections.abc import Generator
from datetime import UTC, datetime
from unittest.mock import Mock

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from src.api.deps import get_review_service, get_user
from src.core.config import settings
from src.main import app
from src.models.reviews import BookReviews, ReviewRead
from src.models.users import User
from src.services.reviews_service import ReviewService
from src.utils.exceptions import (
    BookNotFoundError,
    DAOError,
    NotReviewAuthorError,
    ReviewAlreadyExistsError,
    ReviewNotFoundError,
    UserNotFoundError,
)

ID_USER = 1
ID_BOOK = 42
ID_REVIEW = 7
BOOK_REVIEWS_URL = f"{settings.API_STR}/books/{ID_BOOK}/reviews"
REVIEW_URL = f"{settings.API_STR}/reviews/{ID_REVIEW}"
USER_REVIEWS_URL = f"{settings.API_STR}/users/{ID_USER}/reviews"


@pytest.fixture
def mock_service() -> Mock:
    """Return a mocked ReviewService."""
    return Mock(spec=ReviewService)


@pytest.fixture
def fake_user() -> User:
    """Return a fake authenticated User."""
    return User(
        id_user=ID_USER,
        username="alice",
        email="alice@example.com",
        password_hash="hashed_pw",
        bio=None,
        profile_picture=None,
    )


@pytest.fixture
def review() -> ReviewRead:
    """Return a fake review."""
    return ReviewRead(
        id_review=ID_REVIEW,
        id_user=ID_USER,
        id_book=ID_BOOK,
        rating=4,
        comment="Very good book",
        created_at=datetime.now(tz=UTC),
    )


@pytest.fixture
def client(
    mock_service: Mock,
    fake_user: User,
) -> Generator[TestClient]:
    """Yield a TestClient with service and auth dependencies overridden."""
    app.dependency_overrides[get_review_service] = lambda: mock_service
    app.dependency_overrides[get_user] = lambda: fake_user
    yield TestClient(app)
    app.dependency_overrides.clear()


class TestGetBookReviewsRoute:
    """Unit tests for GET /books/{book_id}/reviews."""

    def test_success(
        self,
        client: TestClient,
        mock_service: Mock,
        review: ReviewRead,
    ) -> None:
        """Existing book returns 200 with reviews and average."""
        mock_service.get_book_reviews.return_value = BookReviews(
            id_book=ID_BOOK,
            average_rating=4.0,
            review_count=1,
            reviews=[review],
        )

        response = client.get(BOOK_REVIEWS_URL)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["average_rating"] == review.rating
        assert data["review_count"] == 1
        assert data["reviews"][0]["id_review"] == ID_REVIEW

    def test_book_not_found(
        self,
        client: TestClient,
        mock_service: Mock,
    ) -> None:
        """Unknown book returns 404."""
        mock_service.get_book_reviews.side_effect = BookNotFoundError(ID_BOOK)

        response = client.get(BOOK_REVIEWS_URL)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_dao_error(
        self,
        client: TestClient,
        mock_service: Mock,
    ) -> None:
        """Database error returns 500."""
        mock_service.get_book_reviews.side_effect = DAOError()

        response = client.get(BOOK_REVIEWS_URL)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestCreateReviewRoute:
    """Unit tests for POST /books/{book_id}/reviews."""

    def test_success(
        self,
        client: TestClient,
        mock_service: Mock,
        review: ReviewRead,
    ) -> None:
        """Valid review returns 201 with the created review."""
        mock_service.create_review.return_value = review

        response = client.post(
            BOOK_REVIEWS_URL,
            json={"rating": 4, "comment": "Very good book"},
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["id_review"] == ID_REVIEW

    @pytest.mark.parametrize("rating", [0, 6])
    def test_invalid_rating(
        self,
        client: TestClient,
        mock_service: Mock,
        rating: int,
    ) -> None:
        """Rating outside 1-5 returns 422 and the service is not called."""
        response = client.post(BOOK_REVIEWS_URL, json={"rating": rating})

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        mock_service.create_review.assert_not_called()

    def test_book_not_found(
        self,
        client: TestClient,
        mock_service: Mock,
    ) -> None:
        """Unknown book returns 404."""
        mock_service.create_review.side_effect = BookNotFoundError(ID_BOOK)

        response = client.post(BOOK_REVIEWS_URL, json={"rating": 4})

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_already_reviewed(
        self,
        client: TestClient,
        mock_service: Mock,
    ) -> None:
        """Second review on the same book returns 409."""
        mock_service.create_review.side_effect = ReviewAlreadyExistsError(
            ID_BOOK,
        )

        response = client.post(BOOK_REVIEWS_URL, json={"rating": 4})

        assert response.status_code == status.HTTP_409_CONFLICT


class TestUpdateReviewRoute:
    """Unit tests for PUT /reviews/{review_id}."""

    def test_success(
        self,
        client: TestClient,
        mock_service: Mock,
        review: ReviewRead,
    ) -> None:
        """The author gets 200 with the updated review."""
        mock_service.update_review.return_value = review

        response = client.put(REVIEW_URL, json={"rating": 4})

        assert response.status_code == status.HTTP_200_OK

    def test_not_author(
        self,
        client: TestClient,
        mock_service: Mock,
    ) -> None:
        """Another user gets 403."""
        mock_service.update_review.side_effect = NotReviewAuthorError(
            ID_REVIEW,
        )

        response = client.put(REVIEW_URL, json={"rating": 4})

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_review_not_found(
        self,
        client: TestClient,
        mock_service: Mock,
    ) -> None:
        """Unknown review returns 404."""
        mock_service.update_review.side_effect = ReviewNotFoundError(
            ID_REVIEW,
        )

        response = client.put(REVIEW_URL, json={"rating": 4})

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestDeleteReviewRoute:
    """Unit tests for DELETE /reviews/{review_id}."""

    def test_success(
        self,
        client: TestClient,
        mock_service: Mock,
    ) -> None:
        """The author gets 204 with an empty body."""
        response = client.delete(REVIEW_URL)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not response.content
        mock_service.delete_review.assert_called_once_with(ID_USER, ID_REVIEW)

    def test_not_author(
        self,
        client: TestClient,
        mock_service: Mock,
    ) -> None:
        """Another user gets 403."""
        mock_service.delete_review.side_effect = NotReviewAuthorError(
            ID_REVIEW,
        )

        response = client.delete(REVIEW_URL)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_review_not_found(
        self,
        client: TestClient,
        mock_service: Mock,
    ) -> None:
        """Unknown review returns 404."""
        mock_service.delete_review.side_effect = ReviewNotFoundError(
            ID_REVIEW,
        )

        response = client.delete(REVIEW_URL)

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestListUserReviewsRoute:
    """Unit tests for GET /users/{user_id}/reviews."""

    def test_success(
        self,
        client: TestClient,
        mock_service: Mock,
        review: ReviewRead,
    ) -> None:
        """Existing user returns 200 with their reviews."""
        mock_service.list_user_reviews.return_value = [review]

        response = client.get(USER_REVIEWS_URL)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 1

    def test_user_not_found(
        self,
        client: TestClient,
        mock_service: Mock,
    ) -> None:
        """Unknown user returns 404."""
        mock_service.list_user_reviews.side_effect = UserNotFoundError(
            user_id=ID_USER,
        )

        response = client.get(USER_REVIEWS_URL)

        assert response.status_code == status.HTTP_404_NOT_FOUND
