"""Integration tests for the book search routes.

Uses FastAPI TestClient with the rolled-back test cursor.
"""

from collections.abc import Generator
from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from psycopg2.extras import RealDictCursor
from pytest_mock import MockerFixture

from src.api.deps import get_cursor
from src.core.config import settings
from src.main import app
from src.services.books_service import BookService
from src.utils.exceptions import ExternalServiceError

SEARCH_URL = f"{settings.API_STR}/books/search"
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
    uname = f"search_{uuid4().hex[:8]}"
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


class TestSearchBooksRoute:
    """Integration tests for GET /api/books/search."""

    def test_search_unauthenticated(self, client: TestClient) -> None:
        """Route requires authentication: 401 or 403 without token."""
        response = client.get(SEARCH_URL, params={"q": "dune"})
        assert response.status_code in {
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        }

    def test_search_missing_query(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Missing q query param returns 422."""
        response = client.get(SEARCH_URL, headers=auth_headers)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_search_success_mocked_ol(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        mocker: MockerFixture,
    ) -> None:
        """Search returns 200 and books list when Open Library responds."""
        fake_payload = {
            "docs": [
                {
                    "key": "/works/OL45804W",
                    "title": "The Lord of the Rings",
                    "author_name": ["J.R.R. Tolkien"],
                    "subject": ["Fantasy"],
                    "first_publish_year": 1954,
                    "cover_i": 8231856,
                },
            ],
        }
        mocker.patch.object(
            BookService,
            "_fetch_open_library",
            return_value=fake_payload,
        )

        response = client.get(
            SEARCH_URL,
            params={"q": "rings"},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["title"] == "The Lord of the Rings"
        assert data[0]["author"] == "J.R.R. Tolkien"
        assert data[0]["id_book"] is not None

    def test_search_ol_unavailable_502(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        mocker: MockerFixture,
    ) -> None:
        """ExternalServiceError results in 502 Bad Gateway."""
        mocker.patch.object(
            BookService,
            "_fetch_open_library",
            side_effect=ExternalServiceError("Open Library down"),
        )

        response = client.get(
            SEARCH_URL,
            params={"q": "tolkien"},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_502_BAD_GATEWAY
        expected_msg = "Open Library service is unavailable."
        assert response.json()["detail"] == expected_msg
