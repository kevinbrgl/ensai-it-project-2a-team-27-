"""Unit tests for the registration route.

Uses FastAPI TestClient with a mocked UserService.
No database or external network access is required.
"""

from collections.abc import Generator
from unittest.mock import Mock

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from src.api.deps import get_user_service
from src.core.config import settings
from src.main import app
from src.models.users import User
from src.services.users_service import UserService
from src.utils.exceptions import (
    DAOError,
    EmailAlreadyExistsError,
    UserAlreadyExistsError,
)

REGISTER_URL = f"{settings.API_STR}/auth/register"
PAYLOAD = {
    "username": "alice",
    "email": "alice@ensai.fr",
    "password": "readingpass123",
}


@pytest.fixture
def mock_service() -> Mock:
    """Return a mocked UserService."""
    return Mock(spec=UserService)


@pytest.fixture
def client(mock_service: Mock) -> Generator[TestClient]:
    """Yield a TestClient whose user service is the mock."""
    app.dependency_overrides[get_user_service] = lambda: mock_service
    yield TestClient(app)
    app.dependency_overrides.clear()


class TestRegisterUnitRoute:
    """Unit tests for POST /api/auth/register."""

    def test_register_success_201(
        self,
        client: TestClient,
        mock_service: Mock,
    ) -> None:
        """A new account returns 201 without the password hash."""
        mock_service.register.return_value = User(
            id_user=1,
            username="alice",
            email="alice@ensai.fr",
            password_hash="hashed_pw",
        )

        response = client.post(REGISTER_URL, json=PAYLOAD)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["username"] == "alice"
        assert "password_hash" not in response.json()

    def test_register_username_taken_409(
        self,
        client: TestClient,
        mock_service: Mock,
    ) -> None:
        """A username already taken returns 409 with its own message."""
        mock_service.register.side_effect = UserAlreadyExistsError("alice")

        response = client.post(REGISTER_URL, json=PAYLOAD)

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.json()["detail"] == "Username already used."

    def test_register_email_taken_409(
        self,
        client: TestClient,
        mock_service: Mock,
    ) -> None:
        """An email already used returns 409 with its own message."""
        mock_service.register.side_effect = EmailAlreadyExistsError(
            "alice@ensai.fr",
        )

        response = client.post(REGISTER_URL, json=PAYLOAD)

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.json()["detail"] == "Email already used."

    def test_register_dao_error_500(
        self,
        client: TestClient,
        mock_service: Mock,
    ) -> None:
        """A database error returns 500."""
        mock_service.register.side_effect = DAOError("boom")

        response = client.post(REGISTER_URL, json=PAYLOAD)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json()["detail"] == "Could not register user."
