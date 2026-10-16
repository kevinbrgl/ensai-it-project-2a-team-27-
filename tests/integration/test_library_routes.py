"""Integration tests for the library routes.

The routes are called through FastAPI's TestClient, with the real database
from the .env file. The request cursor is replaced by the test cursor, so
every change made during a test is rolled back afterwards.
"""

from collections.abc import Generator
from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from psycopg2.extras import RealDictCursor

from src.api.deps import get_cursor
from src.core.config import settings
from src.main import app

LIBRARY_BOOKS_URL = f"{settings.API_STR}/library/books"
REGISTER_URL = f"{settings.API_STR}/auth/register"
LOGIN_URL = f"{settings.API_STR}/auth/login"
PASSWORD = "password123"


@pytest.fixture
def client(cursor: RealDictCursor) -> Generator[TestClient]:
    """Return a TestClient bound to the rolled-back test cursor."""

    def override_get_cursor() -> RealDictCursor:
        return cursor

    app.dependency_overrides[get_cursor] = override_get_cursor
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(client: TestClient) -> dict[str, str]:
    """Register and log in a temporary test user and return auth headers."""
    uname = f"libuser_{uuid4().hex[:8]}"
    client.post(
        REGISTER_URL,
        json={
            "username": uname,
            "email": f"{uname}@ensai.fr",
            "password": PASSWORD,
        },
    )
    login_resp = client.post(
        LOGIN_URL,
        data={"username": uname, "password": PASSWORD},
    )
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def id_book(cursor: RealDictCursor) -> int:
    """Insert a test book in the database and return its ID."""
    cursor.execute(
        """
        INSERT INTO books (id_book_api, title)
        VALUES ('openlib_test_route', 'Test Book API')
        RETURNING id_book
        """,
    )
    row = cursor.fetchone()
    assert row is not None
    return row["id_book"]


class TestAddBookRoute:
    """Integration tests for POST /api/library/books."""

    def test_add_book_success(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        id_book: int,
    ) -> None:
        """Valid request: returns 201 Created and the book data."""
        payload = {"id_book": id_book, "state": "READING"}
        response = client.post(
            LIBRARY_BOOKS_URL, headers=auth_headers, json=payload,
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["id_book"] == id_book
        assert data["state"] == "READING"
        assert data["is_favorite"] is False

    def test_unauthorized(self, client: TestClient, id_book: int) -> None:
        """Missing token: the authentication dependency rejects with 401."""
        payload = {"id_book": id_book, "state": "READING"}
        response = client.post(LIBRARY_BOOKS_URL, json=payload)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_book_not_found(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Unknown book ID: Exception is mapped to 404 Not Found."""
        payload = {"id_book": 999_999_999, "state": "READING"}
        response = client.post(
            LIBRARY_BOOKS_URL, headers=auth_headers, json=payload,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_book_already_in_library(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        id_book: int,
    ) -> None:
        """Adding the same book twice: Exception is mapped to 409 Conflict."""
        payload = {"id_book": id_book, "state": "READING"}

        client.post(LIBRARY_BOOKS_URL, headers=auth_headers, json=payload)

        response = client.post(
            LIBRARY_BOOKS_URL, headers=auth_headers, json=payload,
        )

        assert response.status_code == status.HTTP_409_CONFLICT

    def test_invalid_state(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        id_book: int,
    ) -> None:
        """Invalid state: 422 Unprocessable Content."""
        payload = {"id_book": id_book, "state": "EN_COURS"}
        response = client.post(
            LIBRARY_BOOKS_URL, headers=auth_headers, json=payload,
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
