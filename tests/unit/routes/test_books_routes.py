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
from src.utils.exceptions import DAOError, ExternalServiceError

BOOKS_URL = f"{settings.API_STR}/books"


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

    def test_search_books_dao_error_500(
        self,
        client: TestClient,
        mock_service: Mock,
    ) -> None:
        """DAOError during search returns 500."""
        mock_service.search_books.side_effect = DAOError("DB error")

        response = client.get(f"{BOOKS_URL}/search", params={"q": "dune"})

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        expected = "Database error occurred during book search."
        assert response.json()["detail"] == expected


class TestGetBooksCatalogueRoute:
    """Unit tests for GET /api/books (catalogue & filtering)."""

    def test_get_books_unauthenticated(self, mock_service: Mock) -> None:
        """Endpoint rejects requests without a valid token."""

        def dummy_cursor() -> Generator[Mock]:
            yield Mock()

        app.dependency_overrides[get_cursor] = dummy_cursor
        app.dependency_overrides[get_book_service] = lambda: mock_service
        try:
            unauth_client = TestClient(app)
            response = unauth_client.get(BOOKS_URL)
            assert response.status_code in {
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
            }
        finally:
            app.dependency_overrides.clear()

    def test_get_books_no_filters_success(
        self,
        client: TestClient,
        mock_service: Mock,
        fake_book: Book,
    ) -> None:
        """Calling GET /books without params returns all books."""
        mock_service.get_books.return_value = [fake_book]

        response = client.get(BOOKS_URL)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "Dune"
        mock_service.get_books.assert_called_once_with(
            category=None,
            author=None,
        )

    def test_get_books_filter_by_category(
        self,
        client: TestClient,
        mock_service: Mock,
        fake_book: Book,
    ) -> None:
        """Calling GET /books?category=... passes category to service."""
        mock_service.get_books.return_value = [fake_book]

        response = client.get(
            BOOKS_URL,
            params={"category": "Science Fiction"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        mock_service.get_books.assert_called_once_with(
            category="Science Fiction",
            author=None,
        )

    def test_get_books_filter_by_author(
        self,
        client: TestClient,
        mock_service: Mock,
        fake_book: Book,
    ) -> None:
        """Calling GET /books?author=... passes author to service."""
        mock_service.get_books.return_value = [fake_book]

        response = client.get(
            BOOKS_URL,
            params={"author": "Frank Herbert"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        mock_service.get_books.assert_called_once_with(
            category=None,
            author="Frank Herbert",
        )

    def test_get_books_filter_by_both(
        self,
        client: TestClient,
        mock_service: Mock,
        fake_book: Book,
    ) -> None:
        """Calling GET /books with both category and author filters."""
        mock_service.get_books.return_value = [fake_book]

        response = client.get(
            BOOKS_URL,
            params={"category": "Sci-Fi", "author": "Herbert"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        mock_service.get_books.assert_called_once_with(
            category="Sci-Fi",
            author="Herbert",
        )

    def test_get_books_dao_error_500(
        self,
        client: TestClient,
        mock_service: Mock,
    ) -> None:
        """DAOError from database raises 500 Internal Server Error."""
        mock_service.get_books.side_effect = DAOError("DB failed")

        response = client.get(BOOKS_URL)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        expected_detail = "Database error occurred while retrieving books."
        assert response.json()["detail"] == expected_detail
