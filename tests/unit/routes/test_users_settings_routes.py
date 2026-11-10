"""Unit tests for GET and PATCH /users/me/settings."""

from collections.abc import Generator
from unittest.mock import Mock

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from src.api.deps import get_user, get_user_service
from src.core.config import settings
from src.main import app
from src.models.users import User, UserSettingsUpdate
from src.services.users_service import UserService
from src.utils.exceptions import DAOError, UserNotFoundError

ID_USER = 1
SETTINGS_URL = f"{settings.API_STR}/users/me/settings"
ME_FIELDS = {
    "id_user",
    "username",
    "email",
    "bio",
    "profile_picture",
    "theme",
    "profile_visibility",
    "is_admin",
}


def _user(**kwargs: object) -> User:
    return User(
        id_user=ID_USER,
        username="alice",
        email="alice@ensai.fr",
        password_hash="hashed_pw",
        **kwargs,
    )


@pytest.fixture
def mock_service() -> Mock:
    """Return a mocked UserService."""
    return Mock(spec=UserService)


@pytest.fixture
def client(mock_service: Mock) -> Generator[TestClient]:
    """Yield a TestClient with service and auth dependencies overridden."""
    fake_user = _user()
    app.dependency_overrides[get_user_service] = lambda: mock_service
    app.dependency_overrides[get_user] = lambda: fake_user
    yield TestClient(app)
    app.dependency_overrides.clear()


class TestReadSettingsRoute:
    """Unit tests for GET /users/me/settings."""

    def test_fields(self, client: TestClient) -> None:
        """Settings are returned, moderation and password fields are not."""
        response = client.get(SETTINGS_URL)

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert set(body) == ME_FIELDS
        assert body["theme"] == "day"
        assert body["profile_visibility"] == "public"
        assert body["is_admin"] is False


class TestUpdateSettingsRoute:
    """Unit tests for PATCH /users/me/settings."""

    def test_success(self, client: TestClient, mock_service: Mock) -> None:
        """Valid body returns 200 with the new settings."""
        mock_service.update_settings.return_value = _user(theme="night")

        response = client.patch(SETTINGS_URL, json={"theme": "night"})

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["theme"] == "night"
        mock_service.update_settings.assert_called_once_with(
            ID_USER,
            UserSettingsUpdate(theme="night"),
        )

    @pytest.mark.parametrize(
        "body",
        [{"theme": "dark"}, {"profile_visibility": "friends"}],
    )
    def test_invalid_value(
        self,
        client: TestClient,
        mock_service: Mock,
        body: dict[str, str],
    ) -> None:
        """Unknown values return 422 and the service is not called."""
        response = client.patch(SETTINGS_URL, json=body)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        mock_service.update_settings.assert_not_called()

    def test_nothing_to_update(
        self,
        client: TestClient,
        mock_service: Mock,
    ) -> None:
        """Empty body returns 400."""
        mock_service.update_settings.side_effect = ValueError("Nothing")

        response = client.patch(SETTINGS_URL, json={})

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_user_not_found(
        self,
        client: TestClient,
        mock_service: Mock,
    ) -> None:
        """Missing user returns 404."""
        mock_service.update_settings.side_effect = UserNotFoundError(
            user_id=ID_USER,
        )

        response = client.patch(SETTINGS_URL, json={"theme": "night"})

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_dao_error(self, client: TestClient, mock_service: Mock) -> None:
        """Database error returns 500."""
        mock_service.update_settings.side_effect = DAOError()

        response = client.patch(SETTINGS_URL, json={"theme": "night"})

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
