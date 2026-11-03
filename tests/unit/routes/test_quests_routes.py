"""Unit tests for GET /users/me/quests.

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
    get_quest_service,
    get_user,
)
from src.core.config import settings
from src.main import app
from src.models import User
from src.models.quests import Quest, QuestCategory
from src.services.quests_service import QuestService
from src.utils.exceptions import DAOError

QUESTS_URL = f"{settings.API_STR}/users/me/quests"
FULL_PERCENT = 100.0
EXPECTED_XP = 25


@pytest.fixture
def mock_service() -> Mock:
    """Return a mocked QuestService."""
    return Mock(spec=QuestService)


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
        yield Mock()

    app.dependency_overrides[get_cursor] = dummy_cursor
    app.dependency_overrides[get_quest_service] = lambda: mock_service
    app.dependency_overrides[get_user] = lambda: auth_user

    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def sample_quest() -> Quest:
    """Return a sample Quest object."""
    return Quest(
        id_quest="read_first_book",
        title="Premier pas",
        description="Lire 1 livre",
        category=QuestCategory.READING,
        current=1,
        target=1,
        progress_percentage=FULL_PERCENT,
        is_completed=True,
        reward_xp=25,
    )


class TestGetMyQuestsUnitRoute:
    """Unit tests for GET /users/me/quests."""

    def test_get_my_quests_success_200(
        self,
        client: TestClient,
        mock_service: Mock,
        sample_quest: Quest,
    ) -> None:
        """Retrieving quests returns 200 with quest list payload."""
        mock_service.get_quests.return_value = [sample_quest]

        response = client.get(QUESTS_URL)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["id_quest"] == "read_first_book"
        assert data[0]["title"] == "Premier pas"
        assert data[0]["current"] == 1
        assert data[0]["target"] == 1
        assert data[0]["progress_percentage"] == pytest.approx(FULL_PERCENT)
        assert data[0]["is_completed"] is True
        assert data[0]["reward_xp"] == EXPECTED_XP
        mock_service.get_quests.assert_called_once_with(
            user_id=1,
            status_filter="all",
        )

    def test_get_my_quests_with_filter(
        self,
        client: TestClient,
        mock_service: Mock,
    ) -> None:
        """Passing ?status=active forwards filter to service."""
        mock_service.get_quests.return_value = []

        response = client.get(f"{QUESTS_URL}?status=active")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []
        mock_service.get_quests.assert_called_once_with(
            user_id=1,
            status_filter="active",
        )

    def test_get_my_quests_dao_error_500(
        self,
        client: TestClient,
        mock_service: Mock,
    ) -> None:
        """DAOError returns 500 Internal Server Error."""
        mock_service.get_quests.side_effect = DAOError("DB error")

        response = client.get(QUESTS_URL)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json()["detail"] == "Could not retrieve quests."

    def test_get_my_quests_unauthenticated(
        self,
        mock_service: Mock,
    ) -> None:
        """Unauthenticated request is rejected with 401 or 403."""

        def dummy_cursor() -> Generator[Mock]:
            yield Mock()

        app.dependency_overrides[get_cursor] = dummy_cursor
        app.dependency_overrides[get_quest_service] = lambda: mock_service
        try:
            unauth_client = TestClient(app)
            response = unauth_client.get(QUESTS_URL)
            assert response.status_code in {
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
            }
        finally:
            app.dependency_overrides.clear()
