"""Unit tests for the book routes.

Uses FastAPI TestClient with mocked dependencies.
No database or external network access is required.
"""

from collections.abc import Generator
from datetime import date
from unittest.mock import Mock

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from src.api.deps import get_book_service, get_cursor, get_user
from src.core.config import settings
from src.main import app
from src.models.books import Book
from src.models.users import User
from src.services.books_service import BookService
from src.utils.exceptions import (
    BookNotFoundError,
    DAOError,
    ExternalServiceError,
)

BOOKS_URL = f"{settings.API_STR}/books"
TEST_BOOK_ID = 42
NON_EXISTING_BOOK_ID = 999


@pytest.fixture
def mock_service() -> Mock:
    """Return a mocked BookService."""
    return Mock(spec=BookService)


@pytest.fixture
def fake_user() -> User:
    """Return a fake authenticated User."""
    return User(
        id_user=1,
        username="alice",
        email="alice@example.com",
        password_hash="hashed_pw",
        bio=None,
        profile_picture=None,
    )


@pytest.fixture
def fake_book() -> Book:
    """Return a fake Book representing a database row."""
    return Book(
        id_book=42,
        id_book_api="/works/OL42W",
        title="Dune",
        author="Frank Herbert",
        category="Science Fiction",
        publish_date=date(1965, 8, 1),
        description="A masterpiece of science fiction.",
        cover_image="https://covers.openlibrary.org/b/id/111-M.jpg",
    )


@pytest.fixture
def client(
    mock_service: Mock,
    fake_user: User,
) -> Generator[TestClient]:
    """Yield a TestClient with service and auth dependencies overridden."""
    app.dependency_overrides[get_book_service] = lambda: mock_service
    app.dependency_overrides[get_user] = lambda: fake_user
    yield TestClient(app)
    app.dependency_overrides.clear()


class TestGetBookDetailsRoute:
    """Unit tests for GET /api/books/{book_id}."""

    def test_get_book_unauthenticated(self, mock_service: Mock) -> None:
        """Endpoint rejects requests without a valid token."""

        def dummy_cursor() -> Generator[Mock]:
            yield Mock()

        app.dependency_overrides[get_cursor] = dummy_cursor
        app.dependency_overrides[get_book_service] = lambda: mock_service
        try:
            unauth_client = TestClient(app)
            response = unauth_client.get(f"{BOOKS_URL}/{TEST_BOOK_ID}")
            assert response.status_code in {
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
            }
        finally:
            app.dependency_overrides.clear()

    def test_get_book_success(
        self,
        client: TestClient,
        mock_service: Mock,
        fake_book: Book,
    ) -> None:
        """Found book returns 200 with full book details."""
        mock_service.get_book.return_value = fake_book

        response = client.get(f"{BOOKS_URL}/{TEST_BOOK_ID}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id_book"] == fake_book.id_book
        assert data["title"] == fake_book.title
        assert data["author"] == fake_book.author
        assert data["category"] == fake_book.category
        assert data["publish_date"] == str(fake_book.publish_date)
        assert data["description"] == fake_book.description
        assert data["cover_image"] == fake_book.cover_image
        assert data["id_book_api"] == fake_book.id_book_api
        mock_service.get_book.assert_called_once_with(TEST_BOOK_ID)

    def test_get_book_not_found_404(
        self,
        client: TestClient,
        mock_service: Mock,
    ) -> None:
        """Non-existing book raises 404 Not Found."""
        mock_service.get_book.side_effect = BookNotFoundError(
            book_id=NON_EXISTING_BOOK_ID,
        )

        response = client.get(f"{BOOKS_URL}/{NON_EXISTING_BOOK_ID}")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Book not found."

    def test_get_book_dao_error_500(
        self,
        client: TestClient,
        mock_service: Mock,
    ) -> None:
        """DAOError from database raises 500 Internal Server Error."""
        mock_service.get_book.side_effect = DAOError("DB connection failed")

        response = client.get(f"{BOOKS_URL}/{TEST_BOOK_ID}")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        expected_detail = (
            "Database error occurred while retrieving book details."
        )
        assert response.json()["detail"] == expected_detail

    def test_get_book_invalid_id_zero_422(
        self,
        client: TestClient,
    ) -> None:
        """book_id < 1 violates validation and returns 422."""
        response = client.get(f"{BOOKS_URL}/0")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_get_book_invalid_id_string_422(
        self,
        client: TestClient,
    ) -> None:
        """Non-integer book_id returns 422."""
        response = client.get(f"{BOOKS_URL}/invalid-id")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


class TestSearchBooksUnitRoute:
    """Unit tests for GET /api/books/search."""

    def test_search_books_success(
        self,
        client: TestClient,
        mock_service: Mock,
        fake_book: Book,
    ) -> None:
        """Successful search returns 200 with list of books."""
        mock_service.search_books.return_value = [fake_book]

        response = client.get(f"{BOOKS_URL}/search", params={"q": "dune"})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "Dune"
        mock_service.search_books.assert_called_once_with(
            query="dune",
            limit=10,
        )

    def test_search_books_external_error_502(
        self,
        client: TestClient,
        mock_service: Mock,
    ) -> None:
        """ExternalServiceError from Open Library returns 502."""
        mock_service.search_books.side_effect = ExternalServiceError("down")

        response = client.get(f"{BOOKS_URL}/search", params={"q": "dune"})

        assert response.status_code == status.HTTP_502_BAD_GATEWAY
        assert (
            response.json()["detail"] == "Open Library service is unavailable."
        )
