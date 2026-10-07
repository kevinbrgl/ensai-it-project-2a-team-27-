"""Integration tests for the authentication routes.

The routes are called through FastAPI's TestClient, with the real database
from the .env file. The request cursor is replaced by the test cursor, so
every change made during a test is rolled back afterwards.
"""

from collections.abc import Generator
from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from httpx2 import Response
from psycopg2.extras import RealDictCursor

from src.api.deps import get_cursor
from src.core.config import settings
from src.main import app

REGISTER_URL = f"{settings.API_STR}/auth/register"
LOGIN_URL = f"{settings.API_STR}/auth/login"
ME_URL = f"{settings.API_STR}/users/me"
OLD_LOGIN_URL = f"{settings.API_STR}/login/access-token"

PASSWORD = "motdepasse123"
WRONG_PASSWORD = "mauvaismdp123"
LONG_PASSWORD = "a" * 100


@pytest.fixture
def client(cursor: RealDictCursor) -> Generator[TestClient]:
    """Return a TestClient that uses the rolled-back test cursor.

    The TestClient is created without "with", so the lifespan (pool
    opening and init.sql) is not run: get_cursor is overridden anyway.
    """

    def override_get_cursor() -> RealDictCursor:
        """Give the test cursor to the routes instead of a pool cursor."""
        return cursor

    app.dependency_overrides[get_cursor] = override_get_cursor
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def username(client: TestClient) -> str:
    """Register a new user through the API and return its username.

    A random suffix avoids conflicts with users already in the database.
    """
    name = f"login_{uuid4().hex[:8]}"
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


def login(client: TestClient, name: str, password: str) -> Response:
    """Send the login form, like the "Authorize" button of /docs does.

    :param client: Test client
    :param name: Username sent in the form
    :param password: Password sent in the form
    :return: The HTTP response
    """
    return client.post(
        LOGIN_URL,
        data={"username": name, "password": password},
    )


class TestLogin:
    """Integration tests for POST /api/auth/login."""

    def test_valid(self, client: TestClient, username: str) -> None:
        """Right credentials: 200 with a bearer token."""
        response = login(client, username, PASSWORD)

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["token_type"] == "bearer"
        assert body["access_token"]

    def test_wrong_password(self, client: TestClient, username: str) -> None:
        """Wrong password: 401."""
        response = login(client, username, WRONG_PASSWORD)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_unknown_user_same_error(
        self,
        client: TestClient,
        username: str,
    ) -> None:
        """Unknown user and wrong password give exactly the same error."""
        wrong_password = login(client, username, WRONG_PASSWORD)
        unknown_user = login(client, f"ghost_{uuid4().hex[:8]}", PASSWORD)

        assert unknown_user.status_code == status.HTTP_401_UNAUTHORIZED
        assert unknown_user.json() == wrong_password.json()

    def test_www_authenticate_header(
        self,
        client: TestClient,
        username: str,
    ) -> None:
        """A 401 response tells the client to use a Bearer token."""
        response = login(client, username, WRONG_PASSWORD)

        assert response.headers["www-authenticate"] == "Bearer"

    def test_missing_field(self, client: TestClient, username: str) -> None:
        """Form without password: 422 (validation error)."""
        response = client.post(LOGIN_URL, data={"username": username})

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_long_password(self, client: TestClient, username: str) -> None:
        """Password longer than bcrypt's 72 bytes: 401, not 500."""
        response = login(client, username, LONG_PASSWORD)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_token_gives_access_to_me(
        self,
        client: TestClient,
        username: str,
    ) -> None:
        """The token returned by /login opens GET /users/me."""
        token = login(client, username, PASSWORD).json()["access_token"]

        response = client.get(
            ME_URL,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["username"] == username

    def test_old_route_removed(self, client: TestClient) -> None:
        """The template route /login/access-token no longer exists."""
        response = client.post(
            OLD_LOGIN_URL,
            data={"username": "nobody", "password": PASSWORD},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
