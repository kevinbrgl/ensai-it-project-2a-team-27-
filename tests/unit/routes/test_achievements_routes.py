"""Unit tests for GET /users/me/achievements.

Uses FastAPI TestClient with mocked dependencies.
No database or external network access is required.
"""

from collections.abc import Generator
from unittest.mock import Mock

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from src.api.deps import (
    get_achievement_service,
    get_cursor,
    get_user,
)
from src.core.config import settings
from src.main import app
from src.models import User
from src.models.achievements import (
    Achievement,
    AchievementCategory,
    AchievementTier,
)
from src.services.achievements_service import AchievementService
from src.utils.exceptions import DAOError

ACHIEVEMENTS_URL = f"{settings.API_STR}/users/me/achievements"
FULL_PERCENT = 100.0


@pytest.fixture
def mock_service() -> Mock:
    """Return a mocked AchievementService."""
    return Mock(spec=AchievementService)


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
def client(mock_service: Mock, auth_user: User) -> Generator[TestClient]:
    """Return a TestClient with overridden dependencies."""

    def dummy_cursor() -> Generator[Mock]:
        """Yield a mock cursor for the route dependency."""
        yield Mock()

    app.dependency_overrides[get_cursor] = dummy_cursor
    app.dependency_overrides[get_achievement_service] = lambda: mock_service
    app.dependency_overrides[get_user] = lambda: auth_user

    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def sample_achievement() -> Achievement:
    """Return a sample Achievement object."""
    return Achievement(
        id_achievement="first_book",
        title="First Chapter",
        description="Finish your first book.",
        category=AchievementCategory.READING,
        tier=AchievementTier.BRONZE,
        icon="🌱",
        is_unlocked=True,
        progress=1,
        target=1,
        progress_percentage=FULL_PERCENT,
    )


class TestGetMyAchievementsUnitRoute:
    """Unit tests for GET /users/me/achievements."""

    def test_get_my_achievements_success_200(
        self,
        client: TestClient,
        mock_service: Mock,
        sample_achievement: Achievement,
    ) -> None:
        """Retrieving achievements returns 200 with achievements payload."""
        mock_service.get_achievements.return_value = [sample_achievement]

        response = client.get(ACHIEVEMENTS_URL)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["id_achievement"] == "first_book"
        assert data[0]["title"] == "First Chapter"
        assert data[0]["tier"] == "BRONZE"
        assert data[0]["icon"] == "🌱"
        assert data[0]["is_unlocked"] is True
        assert data[0]["progress"] == 1
        assert data[0]["target"] == 1
        assert data[0]["progress_percentage"] == pytest.approx(FULL_PERCENT)
        mock_service.get_achievements.assert_called_once_with(
            user_id=1,
            status_filter="all",
        )

    def test_get_my_achievements_with_filter(
        self,
        client: TestClient,
        mock_service: Mock,
    ) -> None:
        """Passing ?status=unlocked forwards filter to service."""
        mock_service.get_achievements.return_value = []

        response = client.get(f"{ACHIEVEMENTS_URL}?status=unlocked")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []
        mock_service.get_achievements.assert_called_once_with(
            user_id=1,
            status_filter="unlocked",
        )

    def test_get_my_achievements_dao_error_500(
        self,
        client: TestClient,
        mock_service: Mock,
    ) -> None:
        """DAOError returns 500 Internal Server Error."""
        mock_service.get_achievements.side_effect = DAOError("DB error")

        response = client.get(ACHIEVEMENTS_URL)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json()["detail"] == "Could not retrieve achievements."

    def test_get_my_achievements_unauthenticated(
        self,
        mock_service: Mock,
    ) -> None:
        """Unauthenticated request is rejected with 401 or 403."""

        def dummy_cursor() -> Generator[Mock]:
            """Yield a mock cursor for the route dependency."""
            yield Mock()

        app.dependency_overrides[get_cursor] = dummy_cursor
        app.dependency_overrides[get_achievement_service] = lambda: (
            mock_service
        )
        try:
            unauth_client = TestClient(app)
            response = unauth_client.get(ACHIEVEMENTS_URL)
            assert response.status_code in {
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
            }
        finally:
            app.dependency_overrides.clear()
