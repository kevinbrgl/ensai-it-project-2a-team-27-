"""Unit tests for user routes.

Uses FastAPI TestClient with mocked dependencies.
No database or external network access is required.
"""

from collections.abc import Generator
from unittest.mock import Mock

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from src.api.deps import get_cursor, get_user, get_user_service
from src.core.config import settings
from src.main import app
from src.models.users import User
from src.services.users_service import UserService
from src.utils.exceptions import DAOError

USERS_URL = f"{settings.API_STR}/users"
PUBLIC_FIELDS = {"id_user", "username", "email", "bio", "profile_picture"}


@pytest.fixture
def mock_service() -> Mock:
    """Return a mocked UserService."""
    return Mock(spec=UserService)


@pytest.fixture
def fake_user() -> User:
    """Return a fake authenticated User."""
    return User(
        id_user=1,
        username="alice",
        email="alice@ensai.fr",
        password_hash="hashed_pw",
        bio="Passionnée de lecture",
        profile_picture="https://example.com/avatar.png",
    )


@pytest.fixture
def fake_matched_user() -> User:
    """Return a fake matching User for search results."""
    return User(
        id_user=2,
        username="alicia",
        email="alicia@ensai.fr",
        password_hash="hashed_pw_2",
        bio=None,
        profile_picture=None,
    )


@pytest.fixture
def client(
    mock_service: Mock,
    fake_user: User,
) -> Generator[TestClient]:
    """Yield a TestClient with service and auth dependencies overridden."""
    app.dependency_overrides[get_user_service] = lambda: mock_service
    app.dependency_overrides[get_user] = lambda: fake_user
    yield TestClient(app)
    app.dependency_overrides.clear()


class TestSearchUsersUnitRoute:
    """Unit tests for GET /api/users/search."""

    def test_search_users_success(
        self,
        client: TestClient,
        mock_service: Mock,
        fake_matched_user: User,
    ) -> None:
        """Successful search returns 200 with list of matching users."""
        mock_service.search_users.return_value = [fake_matched_user]

        response = client.get(
            f"{USERS_URL}/search",
            params={"username": "ali", "limit": 10},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["id_user"] == 2  # ruff: ignore[magic-value-comparison]
        assert data[0]["username"] == "alicia"
        assert set(data[0].keys()) == PUBLIC_FIELDS
        assert "password" not in data[0]
        assert "password_hash" not in data[0]
        mock_service.search_users.assert_called_once_with(
            username="ali",
            limit=10,
        )

    def test_search_users_empty_results(
        self,
        client: TestClient,
        mock_service: Mock,
    ) -> None:
        """Search with no matching users returns 200 and empty list."""
        mock_service.search_users.return_value = []

        response = client.get(
            f"{USERS_URL}/search",
            params={"username": "nobody"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    def test_search_users_missing_param_422(
        self,
        client: TestClient,
    ) -> None:
        """Missing username query parameter returns 422."""
        response = client.get(f"{USERS_URL}/search")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_search_users_empty_string_422(
        self,
        client: TestClient,
    ) -> None:
        """Empty username query parameter returns 422."""
        response = client.get(
            f"{USERS_URL}/search",
            params={"username": ""},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_search_users_dao_error_500(
        self,
        client: TestClient,
        mock_service: Mock,
    ) -> None:
        """DAOError during search returns 500."""
        mock_service.search_users.side_effect = DAOError("DB error")

        response = client.get(
            f"{USERS_URL}/search",
            params={"username": "error"},
        )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json()["detail"] == "Could not search users."

    def test_search_users_unauthenticated(
        self,
        mock_service: Mock,
    ) -> None:
        """Unauthenticated request is rejected with 401 or 403."""

        def dummy_cursor() -> Generator[Mock]:
            yield Mock()

        app.dependency_overrides[get_cursor] = dummy_cursor
        app.dependency_overrides[get_user_service] = lambda: mock_service
        try:
            unauth_client = TestClient(app)
            response = unauth_client.get(
                f"{USERS_URL}/search",
                params={"username": "ali"},
            )
            assert response.status_code in {
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
            }
        finally:
            app.dependency_overrides.clear()
