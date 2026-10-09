"""Unit tests for BookService.

The BookDAO and external HTTP calls are mocked: no database or external network
access is needed.
"""

from datetime import date
from unittest.mock import Mock

import pytest
from pytest_mock import MockerFixture

from src.dao.books_dao import BookDAO
from src.models.books import Book, BookCreate
from src.services.books_service import BookService
from src.utils.exceptions import BookNotFoundError, ExternalServiceError


@pytest.fixture
def mock_dao(mocker: MockerFixture) -> Mock:
    """Return a mocked BookDAO."""
    return mocker.Mock(spec=BookDAO)


@pytest.fixture
def service(mock_dao: Mock) -> BookService:
    """Return a BookService with the mocked BookDAO."""
    return BookService(mock_dao)


@pytest.fixture
def fake_book() -> Book:
    """Return a sample Book as stored in the database."""
    return Book(
        id_book=1,
        id_book_api="/works/OL123W",
        title="The Hobbit",
        author="J.R.R. Tolkien",
        category="Fantasy",
        publish_date=date(1937, 1, 1),
        description=None,
        cover_image="https://covers.openlibrary.org/b/id/12345-M.jpg",
    )


class TestSearchBooks:
    """Tests for BookService.search_books."""

    def test_search_books_success(
        self,
        service: BookService,
        mock_dao: Mock,
        fake_book: Book,
        mocker: MockerFixture,
    ) -> None:
        """Search returns parsed and persisted books from Open Library."""
        fake_payload = {
            "docs": [
                {
                    "key": "/works/OL123W",
                    "title": "The Hobbit",
                    "author_name": ["J.R.R. Tolkien"],
                    "subject": ["Fantasy"],
                    "first_publish_year": 1937,
                    "cover_i": 12345,
                },
            ],
        }
        mocker.patch.object(
            service,
            "_fetch_open_library",
            return_value=fake_payload,
        )
        mock_dao.upsert.return_value = fake_book

        results = service.search_books("hobbit")

        assert len(results) == 1
        assert results[0] == fake_book
        mock_dao.upsert.assert_called_once()
        inserted_data: BookCreate = mock_dao.upsert.call_args[0][0]
        assert inserted_data.title == "The Hobbit"
        assert inserted_data.author == "J.R.R. Tolkien"
        assert inserted_data.category == "Fantasy"
        assert inserted_data.publish_date == date(1937, 1, 1)
        assert inserted_data.id_book_api == "/works/OL123W"

    def test_search_empty_query(
        self,
        service: BookService,
        mock_dao: Mock,
        mocker: MockerFixture,
    ) -> None:
        """Empty or whitespace query immediately returns empty list."""
        mock_fetch = mocker.patch.object(service, "_fetch_open_library")

        results = service.search_books("   ")

        assert results == []
        mock_fetch.assert_not_called()
        mock_dao.upsert.assert_not_called()

    def test_search_open_library_unavailable(
        self,
        service: BookService,
        mocker: MockerFixture,
    ) -> None:
        """External service error from Open Library propagates properly."""
        mocker.patch.object(
            service,
            "_fetch_open_library",
            side_effect=ExternalServiceError("Open Library unavailable"),
        )

        with pytest.raises(ExternalServiceError):
            service.search_books("Tolkien")


class TestGetBook:
    """Tests for BookService.get_book."""

    def test_get_book_found(
        self,
        service: BookService,
        mock_dao: Mock,
        fake_book: Book,
    ) -> None:
        """Found book is returned."""
        mock_dao.read.return_value = fake_book

        book = service.get_book(1)

        assert book == fake_book
        mock_dao.read.assert_called_once_with(1)

    def test_get_book_not_found(
        self,
        service: BookService,
        mock_dao: Mock,
    ) -> None:
        """Non-existing book raises BookNotFoundError."""
        mock_dao.read.return_value = None

        with pytest.raises(BookNotFoundError):
            service.get_book(999)
