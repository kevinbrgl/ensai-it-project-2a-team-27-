"""Integration tests for the user routes.

The routes are called through FastAPI's TestClient (fixture "client" from
conftest.py), with the real database from the .env file. Every change made
during a test is rolled back afterwards.
"""

from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from src.core.config import settings

REGISTER_URL = f"{settings.API_STR}/auth/register"
LOGIN_URL = f"{settings.API_STR}/auth/login"
ME_URL = f"{settings.API_STR}/users/me"
PASSWORD_URL = f"{settings.API_STR}/users/me/password"
PASSWORD = "motdepasse123"
NEW_PASSWORD = "nouveaumdp456"
PUBLIC_FIELDS = {"id_user", "username", "email", "bio", "profile_picture"}


@pytest.fixture
def username(client: TestClient) -> str:
    """Register a new user through the API and return its username.

    A random suffix avoids conflicts with users already in the database.
    """
    name = f"me_{uuid4().hex[:8]}"
    response = client.post(
        REGISTER_URL,
        json={
            "username": name,
            "email": f"{name}@ensai.fr",
            "password": PASSWORD,
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    return name


@pytest.fixture
def auth_headers(client: TestClient, username: str) -> dict[str, str]:
    """Log the user in and return the header that carries its token.

    Reused by every test of a protected route (GET, PATCH, PUT).
    """
    response = client.post(
        LOGIN_URL,
        data={"username": username, "password": PASSWORD},
    )
    assert response.status_code == status.HTTP_200_OK
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def other_username(client: TestClient) -> str:
    """Register a second user, to test conflicts on username and email."""
    name = f"other_{uuid4().hex[:8]}"
    response = client.post(
        REGISTER_URL,
        json={
            "username": name,
            "email": f"{name}@ensai.fr",
            "password": PASSWORD,
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    return name


class TestReadSelf:
    """Integration tests for GET /api/users/me."""

    def test_valid(
        self,
        client: TestClient,
        username: str,
        auth_headers: dict[str, str],
    ) -> None:
        """Valid token: 200 with the logged-in user's profile."""
        response = client.get(ME_URL, headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["username"] == username
        assert body["email"] == f"{username}@ensai.fr"
        assert body["bio"] is None
        assert body["profile_picture"] is None

    def test_only_public_fields(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """The response holds the public fields only, never the password."""
        body = client.get(ME_URL, headers=auth_headers).json()

        assert set(body) == PUBLIC_FIELDS
        assert "password_hash" not in body

    def test_no_token(self, client: TestClient) -> None:
        """No token: 401."""
        response = client.get(ME_URL)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_invalid_token(self, client: TestClient) -> None:
        """Invented token: 403."""
        response = client.get(
            ME_URL,
            headers={"Authorization": "Bearer not-a-real-token"},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestUpdateSelf:
    """Integration tests for PATCH /api/users/me."""

    def test_update_bio(
        self,
        client: TestClient,
        username: str,
        auth_headers: dict[str, str],
    ) -> None:
        """Only the bio is sent: it changes, the other fields stay."""
        response = client.patch(
            ME_URL,
            headers=auth_headers,
            json={"bio": "Fan de romans policiers"},
        )

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["bio"] == "Fan de romans policiers"
        assert body["username"] == username
        assert body["email"] == f"{username}@ensai.fr"

    def test_update_is_saved(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """The change is saved: GET /users/me returns the new value."""
        client.patch(
            ME_URL,
            headers=auth_headers,
            json={"bio": "Nouvelle bio"},
        )

        response = client.get(ME_URL, headers=auth_headers)

        assert response.json()["bio"] == "Nouvelle bio"

    def test_update_username(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """A free username can be taken."""
        new_name = f"new_{uuid4().hex[:8]}"

        response = client.patch(
            ME_URL,
            headers=auth_headers,
            json={"username": new_name},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["username"] == new_name

    def test_username_already_taken(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        other_username: str,
    ) -> None:
        """Username of another user: 409."""
        response = client.patch(
            ME_URL,
            headers=auth_headers,
            json={"username": other_username},
        )

        assert response.status_code == status.HTTP_409_CONFLICT

    def test_email_already_taken(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        other_username: str,
    ) -> None:
        """Email of another user: 409."""
        response = client.patch(
            ME_URL,
            headers=auth_headers,
            json={"email": f"{other_username}@ensai.fr"},
        )

        assert response.status_code == status.HTTP_409_CONFLICT

    def test_invalid_email(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Badly formatted email: 422 (validation error)."""
        response = client.patch(
            ME_URL,
            headers=auth_headers,
            json={"email": "pas-un-email"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_username_too_short(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Username shorter than 3 characters: 422 (validation error)."""
        response = client.patch(
            ME_URL,
            headers=auth_headers,
            json={"username": "ab"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_no_token(self, client: TestClient) -> None:
        """No token: 401."""
        response = client.patch(ME_URL, json={"bio": "Pirate"})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_empty_body(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Nothing to update: 400."""
        response = client.patch(ME_URL, headers=auth_headers, json={})

        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestUpdatePassword:
    """Integration tests for PUT /api/users/me/password."""

    def test_change_password(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Right current password and a new one: 200, public fields only."""
        response = client.put(
            PASSWORD_URL,
            headers=auth_headers,
            json={
                "current_password": PASSWORD,
                "new_password": NEW_PASSWORD,
            },
        )

        assert response.status_code == status.HTTP_200_OK
        assert set(response.json()) == PUBLIC_FIELDS

    def test_login_with_new_password(
        self,
        client: TestClient,
        username: str,
        auth_headers: dict[str, str],
    ) -> None:
        """After the change, the new password opens a session."""
        client.put(
            PASSWORD_URL,
            headers=auth_headers,
            json={
                "current_password": PASSWORD,
                "new_password": NEW_PASSWORD,
            },
        )

        response = client.post(
            LOGIN_URL,
            data={"username": username, "password": NEW_PASSWORD},
        )

        assert response.status_code == status.HTTP_200_OK

    def test_old_password_rejected(
        self,
        client: TestClient,
        username: str,
        auth_headers: dict[str, str],
    ) -> None:
        """After the change, the old password no longer works."""
        client.put(
            PASSWORD_URL,
            headers=auth_headers,
            json={
                "current_password": PASSWORD,
                "new_password": NEW_PASSWORD,
            },
        )

        response = client.post(
            LOGIN_URL,
            data={"username": username, "password": PASSWORD},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_wrong_current_password(
        self,
        client: TestClient,
        username: str,
        auth_headers: dict[str, str],
    ) -> None:
        """Wrong current password: 403, and the password is not changed."""
        response = client.put(
            PASSWORD_URL,
            headers=auth_headers,
            json={
                "current_password": "mauvaismdp123",
                "new_password": NEW_PASSWORD,
            },
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        login = client.post(
            LOGIN_URL,
            data={"username": username, "password": PASSWORD},
        )
        assert login.status_code == status.HTTP_200_OK

    def test_same_password(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """New password identical to the current one: 400."""
        response = client.put(
            PASSWORD_URL,
            headers=auth_headers,
            json={
                "current_password": PASSWORD,
                "new_password": PASSWORD,
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_new_password_too_short(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """New password shorter than 8 characters: 422 (validation error)."""
        response = client.put(
            PASSWORD_URL,
            headers=auth_headers,
            json={
                "current_password": PASSWORD,
                "new_password": "court",
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_no_token(self, client: TestClient) -> None:
        """No token: 401."""
        response = client.put(
            PASSWORD_URL,
            json={
                "current_password": PASSWORD,
                "new_password": NEW_PASSWORD,
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
