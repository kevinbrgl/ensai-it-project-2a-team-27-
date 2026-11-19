"""Unit tests for GET /users/{userId}/genre-wheel.

Uses FastAPI TestClient with mocked dependencies.
No database or external network access is required.
"""

from collections.abc import Generator
from unittest.mock import Mock

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from src.api.deps import (
    get_cursor,
    get_genre_wheel_service,
    get_user,
    get_user_service,
)
from src.core.config import settings
from src.main import app
from src.models import GenreWheel, GenreWheelSegment, User
from src.services.genre_wheel_service import GenreWheelService
from src.services.users_service import UserService
from src.utils.exceptions import DAOError, UserNotFoundError

GENRE_WHEEL_URL = f"{settings.API_STR}/users/1/genre-wheel"
FULL_PERCENT = 100.0


@pytest.fixture
def mock_wheel_service() -> Mock:
    """Return a mocked GenreWheelService."""
    return Mock(spec=GenreWheelService)


@pytest.fixture
def mock_user_service() -> Mock:
    """Return a mocked UserService."""
    return Mock(spec=UserService)


@pytest.fixture
def auth_user() -> User:
    """Return a dummy authenticated User."""
    return User(
        id_user=1,
        username="testuser",
        email="test@ensai.fr",
        password_hash="fakehash",
        bio="Hello",
        profile_picture=None,
    )


@pytest.fixture
def client(
    mock_wheel_service: Mock,
    mock_user_service: Mock,
    auth_user: User,
) -> Generator[TestClient]:
    """Return a TestClient with overridden dependencies."""

    def dummy_cursor() -> Generator[Mock]:
        yield Mock()

    app.dependency_overrides[get_cursor] = dummy_cursor
    app.dependency_overrides[get_genre_wheel_service] = lambda: (
        mock_wheel_service
    )
    app.dependency_overrides[get_user_service] = lambda: mock_user_service
    app.dependency_overrides[get_user] = lambda: auth_user

    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def sample_wheel() -> GenreWheel:
    """Return a sample GenreWheel object."""
    return GenreWheel(
        id_user=1,
        is_empty=False,
        empty_color="#9CA3AF",
        total_books=1,
        segments=[
            GenreWheelSegment(
                genre="Romance",
                color="#F43F5E",
                percentage=FULL_PERCENT,
                book_count=1,
                average_rating=5.0,
                raw_score=5.0,
            ),
        ],
    )


class TestGetGenreWheelUnitRoute:
    """Unit tests for GET /users/{userId}/genre-wheel."""

    def test_get_genre_wheel_success_200(
        self,
        client: TestClient,
        mock_user_service: Mock,
        mock_wheel_service: Mock,
        sample_wheel: GenreWheel,
    ) -> None:
        """Retrieving genre wheel returns 200 with segments payload."""
        mock_user_service.read.return_value = None
        mock_wheel_service.get_genre_wheel.return_value = sample_wheel

        response = client.get(GENRE_WHEEL_URL)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id_user"] == 1
        assert data["is_empty"] is False
        assert len(data["segments"]) == 1
        assert data["segments"][0]["genre"] == "Romance"
        assert data["segments"][0]["color"] == "#F43F5E"
        assert data["segments"][0]["percentage"] == pytest.approx(FULL_PERCENT)
        mock_wheel_service.get_genre_wheel.assert_called_once_with(user_id=1)

    def test_get_genre_wheel_user_not_found_404(
        self,
        client: TestClient,
        mock_user_service: Mock,
    ) -> None:
        """Non-existing user returns 404 Not Found."""
        mock_user_service.read.side_effect = UserNotFoundError("Missing user")

        response = client.get(GENRE_WHEEL_URL)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "User not found."

    def test_get_genre_wheel_dao_error_500(
        self,
        client: TestClient,
        mock_user_service: Mock,
        mock_wheel_service: Mock,
    ) -> None:
        """DAOError returns 500 Internal Server Error."""
        mock_user_service.read.return_value = None
        mock_wheel_service.get_genre_wheel.side_effect = DAOError("DB error")

        response = client.get(GENRE_WHEEL_URL)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json()["detail"] == "Could not retrieve genre wheel."

    def test_get_genre_wheel_unauthenticated(
        self,
        mock_wheel_service: Mock,
        mock_user_service: Mock,
    ) -> None:
        """Unauthenticated request is rejected with 401 or 403."""

        def dummy_cursor() -> Generator[Mock]:
            yield Mock()

        app.dependency_overrides[get_cursor] = dummy_cursor
        app.dependency_overrides[get_genre_wheel_service] = lambda: (
            mock_wheel_service
        )
        app.dependency_overrides[get_user_service] = lambda: mock_user_service
        try:
            unauth_client = TestClient(app)
            response = unauth_client.get(GENRE_WHEEL_URL)
            assert response.status_code in {
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
            }
        finally:
            app.dependency_overrides.clear()
