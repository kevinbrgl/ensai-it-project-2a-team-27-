"""Unit tests for BookService.

The BookDAO and external HTTP calls are mocked: no database or external network
access is needed.
"""

from datetime import date
from unittest.mock import Mock

import httpx2
import pytest
from pytest_mock import MockerFixture

from src.dao.books_dao import BookDAO
from src.models.books import Book, BookCreate
from src.services.books_service import OPEN_LIBRARY_FIELDS, BookService
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


@pytest.fixture
def http_get(mocker: MockerFixture) -> Mock:
    """Mock httpx2.Client and return its get method."""
    client_cls = mocker.patch("src.services.books_service.httpx2.Client")
    http = client_cls.return_value.__enter__.return_value
    http.get.return_value = mocker.Mock(
        status_code=200,
        json=mocker.Mock(return_value={"docs": []}),
    )
    return http.get


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

    def test_get_book_details(
        self,
        service: BookService,
        mock_dao: Mock,
        fake_book: Book,
    ) -> None:
        """get_book_details delegates to get_book."""
        mock_dao.read.return_value = fake_book

        book = service.get_book_details(1)

        assert book == fake_book
        mock_dao.read.assert_called_once_with(1)


class TestGetBooks:
    """Tests for BookService.get_books and get_catalogue."""

    def test_get_books_no_filter_calls_find_all(
        self,
        service: BookService,
        mock_dao: Mock,
        fake_book: Book,
    ) -> None:
        """With no filters, find_all is called."""
        mock_dao.find_all.return_value = [fake_book]

        results = service.get_books()

        assert results == [fake_book]
        mock_dao.find_all.assert_called_once()
        mock_dao.find_by_category.assert_not_called()
        mock_dao.find_by_author.assert_not_called()
        mock_dao.find_books.assert_not_called()

    def test_get_books_by_category_only(
        self,
        service: BookService,
        mock_dao: Mock,
        fake_book: Book,
    ) -> None:
        """With only category filter, find_by_category is called."""
        mock_dao.find_by_category.return_value = [fake_book]

        results = service.get_books(category="Fantasy")

        assert results == [fake_book]
        mock_dao.find_by_category.assert_called_once_with("Fantasy")
        mock_dao.find_all.assert_not_called()
        mock_dao.find_by_author.assert_not_called()

    def test_get_books_by_author_only(
        self,
        service: BookService,
        mock_dao: Mock,
        fake_book: Book,
    ) -> None:
        """With only author filter, find_by_author is called."""
        mock_dao.find_by_author.return_value = [fake_book]

        results = service.get_books(author="Tolkien")

        assert results == [fake_book]
        mock_dao.find_by_author.assert_called_once_with("Tolkien")
        mock_dao.find_all.assert_not_called()
        mock_dao.find_by_category.assert_not_called()

    def test_get_books_by_both(
        self,
        service: BookService,
        mock_dao: Mock,
        fake_book: Book,
    ) -> None:
        """With both filters, find_books is called."""
        mock_dao.find_books.return_value = [fake_book]

        results = service.get_books(
            category="Fantasy",
            author="Tolkien",
        )

        assert results == [fake_book]
        mock_dao.find_books.assert_called_once_with(
            category="Fantasy",
            author="Tolkien",
        )

    def test_get_books_whitespace_ignored(
        self,
        service: BookService,
        mock_dao: Mock,
        fake_book: Book,
    ) -> None:
        """Whitespace-only query parameters are treated as None."""
        mock_dao.find_all.return_value = [fake_book]

        results = service.get_books(category="   ", author="")

        assert results == [fake_book]
        mock_dao.find_all.assert_called_once()
        mock_dao.find_books.assert_not_called()

    def test_get_catalogue_alias(
        self,
        service: BookService,
        mock_dao: Mock,
        fake_book: Book,
    ) -> None:
        """get_catalogue behaves identically to get_books."""
        mock_dao.find_by_category.return_value = [fake_book]

        results = service.get_catalogue(category="Fantasy")

        assert results == [fake_book]
        mock_dao.find_by_category.assert_called_once_with("Fantasy")


class TestFetchOpenLibrary:
    """Tests for the parameters sent to Open Library."""

    def test_fields_include_ratings_average(self) -> None:
        """The Open Library rating is requested."""
        assert "ratings_average" in OPEN_LIBRARY_FIELDS.split(",")

    def test_search_books_sends_query(
        self,
        service: BookService,
        http_get: Mock,
    ) -> None:
        """search_books sends q and no subject or sort."""
        service.search_books("dune", limit=5)

        assert http_get.call_args.kwargs["params"] == {
            "q": "dune",
            "limit": 5,
            "fields": OPEN_LIBRARY_FIELDS,
        }

    def test_search_by_subject_sends_subject_and_sort(
        self,
        service: BookService,
        http_get: Mock,
    ) -> None:
        """search_by_subject sends subject and sort and no q."""
        service.search_by_subject("Fantasy", limit=7, sort="rating")

        assert http_get.call_args.kwargs["params"] == {
            "subject": "Fantasy",
            "sort": "rating",
            "limit": 7,
            "fields": OPEN_LIBRARY_FIELDS,
        }

    def test_http_error_status_raises(
        self,
        service: BookService,
        http_get: Mock,
    ) -> None:
        """An HTTP error status raises ExternalServiceError."""
        http_get.return_value.status_code = 503

        with pytest.raises(ExternalServiceError):
            service.search_by_subject("Fantasy")

    def test_network_error_raises(
        self,
        service: BookService,
        http_get: Mock,
    ) -> None:
        """A network error raises ExternalServiceError."""
        http_get.side_effect = httpx2.HTTPError("boom")

        with pytest.raises(ExternalServiceError):
            service.search_by_subject("Fantasy")


class TestSearchBySubject:
    """Tests for BookService.search_by_subject."""

    def test_parses_candidates_and_ratings(
        self,
        service: BookService,
        mock_dao: Mock,
        mocker: MockerFixture,
    ) -> None:
        """Docs become BookCreate objects with their Open Library rating."""
        mocker.patch.object(
            service,
            "_fetch_open_library",
            return_value={
                "docs": [
                    {
                        "key": "/works/OL1W",
                        "title": "The Hobbit",
                        "author_name": ["J.R.R. Tolkien"],
                        "subject": ["Fantasy"],
                        "first_publish_year": 1937,
                        "cover_i": 12345,
                        "ratings_average": 4.256,
                    },
                    {
                        "key": "/works/OL2W",
                        "title": "Int",
                        "ratings_average": 4,
                    },
                    {
                        "key": "/works/OL3W",
                        "title": "Bad",
                        "ratings_average": "x",
                    },
                    {"key": "/works/OL4W", "title": "None"},
                ],
            },
        )

        result = service.search_by_subject("Fantasy")

        assert [book.id_book_api for book, _ in result] == [
            "/works/OL1W",
            "/works/OL2W",
            "/works/OL3W",
            "/works/OL4W",
        ]
        assert [rating for _, rating in result] == [4.26, 4.0, None, None]
        hobbit = result[0][0]
        assert hobbit.title == "The Hobbit"
        assert hobbit.author == "J.R.R. Tolkien"
        assert hobbit.category == "Fantasy"
        assert hobbit.publish_date == date(1937, 1, 1)
        assert hobbit.cover_image == (
            "https://covers.openlibrary.org/b/id/12345-M.jpg"
        )
        mock_dao.upsert.assert_not_called()
        mock_dao.create.assert_not_called()

    def test_skips_docs_without_key_or_title(
        self,
        service: BookService,
        mocker: MockerFixture,
    ) -> None:
        """Docs without key or without title are skipped."""
        mocker.patch.object(
            service,
            "_fetch_open_library",
            return_value={
                "docs": [
                    {"title": "No key"},
                    {"key": "/works/OL1W"},
                    {"key": "/works/OL2W", "title": "Valid"},
                ],
            },
        )

        result = service.search_by_subject("Fantasy")

        assert [book.title for book, _ in result] == ["Valid"]

    def test_blank_subject_returns_empty(
        self,
        service: BookService,
        mocker: MockerFixture,
    ) -> None:
        """A blank subject does not call Open Library."""
        mock_fetch = mocker.patch.object(service, "_fetch_open_library")

        assert service.search_by_subject("   ") == []
        mock_fetch.assert_not_called()

    def test_subject_is_stripped(
        self,
        service: BookService,
        mocker: MockerFixture,
    ) -> None:
        """Spaces around the subject are removed."""
        mock_fetch = mocker.patch.object(
            service,
            "_fetch_open_library",
            return_value={"docs": []},
        )

        service.search_by_subject("  Fantasy ", limit=3, sort="new")

        mock_fetch.assert_called_once_with(
            limit=3,
            subject="Fantasy",
            sort="new",
        )

    def test_missing_docs_returns_empty(
        self,
        service: BookService,
        mocker: MockerFixture,
    ) -> None:
        """A payload without docs gives an empty list."""
        mocker.patch.object(service, "_fetch_open_library", return_value={})

        assert service.search_by_subject("Fantasy") == []

    def test_open_library_unavailable(
        self,
        service: BookService,
        mocker: MockerFixture,
    ) -> None:
        """ExternalServiceError propagates."""
        mocker.patch.object(
            service,
            "_fetch_open_library",
            side_effect=ExternalServiceError(),
        )

        with pytest.raises(ExternalServiceError):
            service.search_by_subject("Fantasy")


class TestSaveBook:
    """Tests for BookService.save_book."""

    def test_upserts_the_book(
        self,
        service: BookService,
        mock_dao: Mock,
        fake_book: Book,
    ) -> None:
        """save_book delegates to BookDAO.upsert."""
        book_create = BookCreate(id_book_api="/works/OL123W", title="Hobbit")
        mock_dao.upsert.return_value = fake_book

        assert service.save_book(book_create) == fake_book
        mock_dao.upsert.assert_called_once_with(book_create)
