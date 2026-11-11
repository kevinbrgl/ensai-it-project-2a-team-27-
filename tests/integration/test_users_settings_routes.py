"""Integration tests for /users/me/settings (real database)."""

from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from src.core.config import settings

REGISTER_URL = f"{settings.API_STR}/auth/register"
LOGIN_URL = f"{settings.API_STR}/auth/login"
SETTINGS_URL = f"{settings.API_STR}/users/me/settings"
PASSWORD = "password123"


@pytest.fixture
def auth_headers(client: TestClient) -> dict[str, str]:
    """Register a temporary user and return their auth headers."""
    uname = f"settings_{uuid4().hex[:8]}"
    client.post(
        REGISTER_URL,
        json={
            "username": uname,
            "email": f"{uname}@ensai.fr",
            "password": PASSWORD,
        },
    )
    token = client.post(
        LOGIN_URL,
        data={"username": uname, "password": PASSWORD},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestUserSettings:
    """GET and PATCH /users/me/settings against the database."""

    def test_defaults(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """A new account is in day theme, public, and not admin."""
        body = client.get(SETTINGS_URL, headers=auth_headers).json()

        assert body["theme"] == "day"
        assert body["profile_visibility"] == "public"
        assert body["is_admin"] is False

    def test_update_theme_only(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Changing the theme keeps the visibility and is persisted."""
        response = client.patch(
            SETTINGS_URL,
            headers=auth_headers,
            json={"theme": "night"},
        )

        assert response.status_code == status.HTTP_200_OK
        me = client.get(SETTINGS_URL, headers=auth_headers).json()
        assert me["theme"] == "night"
        assert me["profile_visibility"] == "public"

    def test_update_both(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Both settings can be changed at once."""
        response = client.patch(
            SETTINGS_URL,
            headers=auth_headers,
            json={"theme": "night", "profile_visibility": "private"},
        )

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["theme"] == "night"
        assert body["profile_visibility"] == "private"

    def test_empty_body(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Nothing to update returns 400."""
        response = client.patch(SETTINGS_URL, headers=auth_headers, json={})

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_invalid_theme(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Unknown theme returns 422."""
        response = client.patch(
            SETTINGS_URL,
            headers=auth_headers,
            json={"theme": "purple"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_no_token(self, client: TestClient) -> None:
        """Anonymous request returns 401."""
        response = client.patch(SETTINGS_URL, json={"theme": "night"})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
