"""Integration tests for the book search routes.

Uses FastAPI TestClient with the rolled-back test cursor.
Open Library is always mocked: no external network access is needed.
"""

from collections.abc import Generator
from datetime import date
from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from psycopg2.extras import RealDictCursor
from pytest_mock import MockerFixture

from src.api.deps import get_cursor
from src.core.config import settings
from src.dao.books_dao import BookDAO
from src.main import app
from src.models.books import BookCreate
from src.services.open_library_client import OpenLibraryClient
from src.utils.exceptions import ExternalServiceError

BOOKS_URL = f"{settings.API_STR}/books"
SEARCH_URL = f"{settings.API_STR}/books/search"
REGISTER_URL = f"{settings.API_STR}/auth/register"
LOGIN_URL = f"{settings.API_STR}/auth/login"
PASSWORD = "password123"
NB_PAGES = 1193
EDITION_PAGES = 255
EDITIONS_PAYLOAD = {
    "entries": [
        {
            "title": "Foundation",
            "publishers": ["Gnome Press"],
            "publish_date": "1951",
            "number_of_pages": EDITION_PAGES,
            "isbn_10": ["0553293354"],
            "languages": [{"key": "/languages/eng"}],
        },
        {"title": "Fondation", "languages": [{"key": "/languages/fre"}]},
    ],
}


@pytest.fixture
def client(cursor: RealDictCursor) -> Generator[TestClient]:
    """Return a TestClient bound to the rolled-back test cursor."""

    def override_get_cursor() -> RealDictCursor:
        """Return the cursor for the current test transaction."""
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
                    "number_of_pages_median": NB_PAGES,
                },
            ],
        }
        mocker.patch.object(
            OpenLibraryClient,
            "search",
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
        assert data[0]["num_pages"] == NB_PAGES

    def test_search_stores_num_pages(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        book_dao: BookDAO,
        mocker: MockerFixture,
    ) -> None:
        """The page count sent by Open Library is saved in the catalog."""
        key = f"/works/OL{uuid4().hex[:8]}W"
        mocker.patch.object(
            OpenLibraryClient,
            "search",
            return_value={
                "docs": [
                    {
                        "key": key,
                        "title": "Stored pages",
                        "number_of_pages_median": NB_PAGES,
                    },
                ],
            },
        )

        client.get(SEARCH_URL, params={"q": "pages"}, headers=auth_headers)

        stored = book_dao.read_by_api_id(key)
        assert stored is not None
        assert stored.num_pages == NB_PAGES

    def test_search_ol_unavailable_502(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        mocker: MockerFixture,
    ) -> None:
        """ExternalServiceError results in 502 Bad Gateway."""
        mocker.patch.object(
            OpenLibraryClient,
            "search",
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


class TestGetBooksCatalogueRoute:
    """Integration tests for GET /api/books (catalogue and filters)."""

    def test_get_books_unauthenticated(self, client: TestClient) -> None:
        """Route requires authentication: 401 or 403 without token."""
        response = client.get(BOOKS_URL)
        assert response.status_code in {
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        }

    def test_get_books_success_no_filter(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        book_dao: BookDAO,
    ) -> None:
        """Returns 200 and list of stored books."""
        created = book_dao.create(
            BookCreate(
                title="Dune Messiah",
                author="Frank Herbert",
                category="Science Fiction",
                publish_date=date(1969, 1, 1),
                description="Sequel to Dune",
            ),
        )

        response = client.get(BOOKS_URL, headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert any(b["id_book"] == created.id_book for b in data)

    def test_get_books_filter_by_category(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        book_dao: BookDAO,
    ) -> None:
        """Filter by category returns matching books."""
        created = book_dao.create(
            BookCreate(
                title="Hyperion",
                author="Dan Simmons",
                category="Space Opera",
                publish_date=date(1989, 5, 1),
            ),
        )

        response = client.get(
            BOOKS_URL,
            params={"category": "Space Opera"},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert any(b["id_book"] == created.id_book for b in data)

    def test_get_books_filter_by_author(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        book_dao: BookDAO,
    ) -> None:
        """Filter by author returns matching books."""
        created = book_dao.create(
            BookCreate(
                title="Neuromancer",
                author="William Gibson",
                category="Cyberpunk",
                publish_date=date(1984, 7, 1),
            ),
        )

        response = client.get(
            BOOKS_URL,
            params={"author": "Gibson"},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert any(b["id_book"] == created.id_book for b in data)

    def test_get_books_filter_by_both(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        book_dao: BookDAO,
    ) -> None:
        """Filter by both author and category returns matching books."""
        created = book_dao.create(
            BookCreate(
                title="Snow Crash",
                author="Neal Stephenson",
                category="Cyberpunk",
                publish_date=date(1992, 6, 1),
            ),
        )

        response = client.get(
            BOOKS_URL,
            params={"author": "Stephenson", "category": "Cyberpunk"},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert any(b["id_book"] == created.id_book for b in data)


class TestGetBookDetailsRoute:
    """Integration tests for GET /api/books/{book_id}."""

    def test_get_book_unauthenticated(self, client: TestClient) -> None:
        """Route requires authentication: 401 or 403 without token."""
        response = client.get(f"{BOOKS_URL}/1")
        assert response.status_code in {
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        }

    def test_get_book_invalid_id_422(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Invalid book_id (<= 0 or non-int) returns 422."""
        response = client.get(f"{BOOKS_URL}/0", headers=auth_headers)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

        response_str = client.get(
            f"{BOOKS_URL}/invalid",
            headers=auth_headers,
        )
        assert response_str.status_code == (
            status.HTTP_422_UNPROCESSABLE_CONTENT
        )

    def test_get_book_not_found_404(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Non-existing book returns 404 Not Found."""
        response = client.get(f"{BOOKS_URL}/999999999", headers=auth_headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Book not found."

    def test_get_book_success(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        book_dao: BookDAO,
        mocker: MockerFixture,
    ) -> None:
        """Existing book returns 200 with full book details."""
        mock_fetch = mocker.patch.object(
            OpenLibraryClient,
            "fetch_editions",
            return_value=EDITIONS_PAYLOAD,
        )
        created = book_dao.create(
            BookCreate(
                title="Foundation",
                author="Isaac Asimov",
                category="Science Fiction",
                publish_date=date(1951, 1, 1),
                description="A galactic empire falls into chaos.",
                cover_image="https://example.com/foundation.jpg",
                id_book_api="/works/OL99999W",
                num_pages=EDITION_PAGES,
            ),
        )

        response = client.get(
            f"{BOOKS_URL}/{created.id_book}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id_book"] == created.id_book
        assert data["title"] == "Foundation"
        assert data["author"] == "Isaac Asimov"
        assert data["category"] == "Science Fiction"
        assert data["publish_date"] == "1951-01-01"
        assert data["description"] == "A galactic empire falls into chaos."
        assert data["cover_image"] == "https://example.com/foundation.jpg"
        assert data["id_book_api"] == "/works/OL99999W"
        assert data["num_pages"] == EDITION_PAGES
        assert data["editions"] == [
            {
                "title": "Foundation",
                "publishers": ["Gnome Press"],
                "publish_date": "1951",
                "num_pages": EDITION_PAGES,
                "isbn": "0553293354",
                "language": "eng",
            },
            {
                "title": "Fondation",
                "publishers": [],
                "publish_date": None,
                "num_pages": None,
                "isbn": None,
                "language": "fre",
            },
        ]
        mock_fetch.assert_called_once_with("/works/OL99999W")

    def test_get_book_ol_unavailable_empty_editions(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        book_dao: BookDAO,
        mocker: MockerFixture,
    ) -> None:
        """Open Library down: 200 with the book and no editions."""
        mocker.patch.object(
            OpenLibraryClient,
            "fetch_editions",
            side_effect=ExternalServiceError("Open Library down"),
        )
        created = book_dao.create(
            BookCreate(
                title="I, Robot",
                id_book_api=f"/works/OL{uuid4().hex[:8]}W",
            ),
        )

        response = client.get(
            f"{BOOKS_URL}/{created.id_book}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["title"] == "I, Robot"
        assert data["editions"] == []

    def test_get_book_without_work_key_empty_editions(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        book_dao: BookDAO,
        mocker: MockerFixture,
    ) -> None:
        """Book without a work key: no editions, Open Library not called."""
        mock_fetch = mocker.patch.object(OpenLibraryClient, "fetch_editions")
        created = book_dao.create(BookCreate(title="Local book"))

        response = client.get(
            f"{BOOKS_URL}/{created.id_book}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["num_pages"] is None
        assert data["editions"] == []
        mock_fetch.assert_not_called()
