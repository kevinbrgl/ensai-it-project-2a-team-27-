"""Unit tests for the recommendation routes.

Uses FastAPI TestClient with mocked dependencies.
No database or external network access is required.
"""

from collections.abc import Generator
from datetime import date
from unittest.mock import Mock

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from src.api.deps import get_cursor, get_recommendation_service, get_user
from src.core.config import settings
from src.main import app
from src.models.books import Book
from src.models.recommendations import Recommendation
from src.models.users import User
from src.services.recommendations_service import RecommendationService
from src.utils.exceptions import DAOError

RECOMMENDATIONS_URL = f"{settings.API_STR}/recommendations"


@pytest.fixture
def mock_service() -> Mock:
    """Return a mocked RecommendationService."""
    return Mock(spec=RecommendationService)


@pytest.fixture
def fake_user() -> User:
    """Return a fake authenticated User."""
    return User(
        id_user=1,
        username="alice",
        email="alice@example.com",
        password_hash="hashed_pw",
        bio=None,
        profile_picture=None,
    )


@pytest.fixture
def fake_recommendation() -> Recommendation:
    """Return a fake Recommendation."""
    return Recommendation(
        book=Book(
            id_book=42,
            id_book_api="/works/OL42W",
            title="Dune",
            author="Frank Herbert",
            category="Science Fiction",
            publish_date=date(1965, 8, 1),
        ),
        score=4.5,
        reason="Because you like Science Fiction",
    )


@pytest.fixture
def client(
    mock_service: Mock,
    fake_user: User,
) -> Generator[TestClient]:
    """Yield a TestClient with service and auth dependencies overridden."""
    app.dependency_overrides[get_recommendation_service] = (
        lambda: mock_service
    )
    app.dependency_overrides[get_user] = lambda: fake_user
    yield TestClient(app)
    app.dependency_overrides.clear()


class TestGetRecommendationsRoute:
    """Unit tests for GET /api/recommendations."""

    def test_unauthenticated(self, mock_service: Mock) -> None:
        """Endpoint rejects requests without a valid token."""

        def dummy_cursor() -> Generator[Mock]:
            yield Mock()

        app.dependency_overrides[get_cursor] = dummy_cursor
        app.dependency_overrides[get_recommendation_service] = (
            lambda: mock_service
        )
        try:
            response = TestClient(app).get(RECOMMENDATIONS_URL)
            assert response.status_code in {
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
            }
            mock_service.get_recommendations.assert_not_called()
        finally:
            app.dependency_overrides.clear()

    def test_success_default_parameters(
        self,
        client: TestClient,
        mock_service: Mock,
        fake_user: User,
        fake_recommendation: Recommendation,
    ) -> None:
        """Default call returns 200 with the recommendations."""
        mock_service.get_recommendations.return_value = [fake_recommendation]

        response = client.get(RECOMMENDATIONS_URL)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["book"]["id_book"] == fake_recommendation.book.id_book
        assert data[0]["book"]["title"] == "Dune"
        assert data[0]["book"]["id_book_api"] == "/works/OL42W"
        assert data[0]["score"] == fake_recommendation.score
        assert data[0]["reason"] == "Because you like Science Fiction"
        mock_service.get_recommendations.assert_called_once_with(
            fake_user.id_user,
            genre=None,
            sort="rating",
            limit=10,
        )

    def test_passes_query_parameters(
        self,
        client: TestClient,
        mock_service: Mock,
        fake_user: User,
    ) -> None:
        """genre, sort and limit are passed to the service."""
        mock_service.get_recommendations.return_value = []

        response = client.get(
            RECOMMENDATIONS_URL,
            params={"genre": "Fantasy", "sort": "title", "limit": 5},
        )

        assert response.status_code == status.HTTP_200_OK
        mock_service.get_recommendations.assert_called_once_with(
            fake_user.id_user,
            genre="Fantasy",
            sort="title",
            limit=5,
        )

    @pytest.mark.parametrize("sort", ["rating", "new", "title"])
    def test_valid_sorts(
        self,
        client: TestClient,
        mock_service: Mock,
        sort: str,
    ) -> None:
        """Every supported sort is accepted."""
        mock_service.get_recommendations.return_value = []

        response = client.get(RECOMMENDATIONS_URL, params={"sort": sort})

        assert response.status_code == status.HTTP_200_OK

    def test_empty_result(
        self,
        client: TestClient,
        mock_service: Mock,
    ) -> None:
        """No recommendation returns 200 with an empty list."""
        mock_service.get_recommendations.return_value = []

        response = client.get(RECOMMENDATIONS_URL)

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    @pytest.mark.parametrize(
        "params",
        [
            {"sort": "popularity"},
            {"limit": 0},
            {"limit": 51},
            {"limit": "abc"},
            {"genre": ""},
            {"genre": "x" * 101},
        ],
    )
    def test_invalid_parameters_422(
        self,
        client: TestClient,
        mock_service: Mock,
        params: dict[str, str | int],
    ) -> None:
        """Invalid query parameters return 422."""
        response = client.get(RECOMMENDATIONS_URL, params=params)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        mock_service.get_recommendations.assert_not_called()

    def test_dao_error_500(
        self,
        client: TestClient,
        mock_service: Mock,
    ) -> None:
        """DAOError returns 500."""
        mock_service.get_recommendations.side_effect = DAOError("DB error")

        response = client.get(RECOMMENDATIONS_URL)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json()["detail"] == (
            "Could not compute the recommendations."
        )
