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
from src.models.books import Book, BookCreate, BookDetails, Edition
from src.services.books_service import BookService
from src.services.open_library_client import (
    EDITIONS_LIMIT,
    OPEN_LIBRARY_FIELDS,
    SEARCH_CACHE_TTL,
    OpenLibraryClient,
)
from src.utils.exceptions import (
    BookNotFoundError,
    ExternalServiceError,
    InvalidSearchQueryError,
)

NB_PAGES = 310
EDITIONS_URL = "https://openlibrary.org/works/OL123W/editions.json"
EDITIONS_PAYLOAD = {
    "entries": [
        {
            "title": "The Hobbit",
            "publishers": ["Allen & Unwin"],
            "publish_date": "September 21, 1937",
            "number_of_pages": NB_PAGES,
            "isbn_13": ["9780261102217"],
            "isbn_10": ["0261102214"],
            "languages": [{"key": "/languages/eng"}],
        },
        {
            "title": "Bilbo le Hobbit",
            "isbn_10": ["2253049417"],
        },
        {},
    ],
}


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
        num_pages=NB_PAGES,
    )


@pytest.fixture
def http_get(mocker: MockerFixture) -> Mock:
    """Mock httpx2.Client and return its get method."""
    client_cls = mocker.patch("src.services.open_library_client.httpx2.Client")
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
                    "number_of_pages_median": NB_PAGES,
                },
            ],
        }
        mocker.patch.object(
            service.open_library,
            "search",
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
        assert inserted_data.num_pages == NB_PAGES

    @pytest.mark.parametrize("pages", [None, 0, -5, "310", 310.5])
    def test_search_books_invalid_pages_ignored(
        self,
        service: BookService,
        mock_dao: Mock,
        fake_book: Book,
        mocker: MockerFixture,
        pages: object,
    ) -> None:
        """A missing or invalid page count is stored as None."""
        doc: dict[str, object] = {"key": "/works/OL123W", "title": "Hobbit"}
        if pages is not None:
            doc["number_of_pages_median"] = pages
        mocker.patch.object(
            service.open_library,
            "search",
            return_value={"docs": [doc]},
        )
        mock_dao.upsert.return_value = fake_book

        service.search_books("hobbit")

        inserted_data: BookCreate = mock_dao.upsert.call_args[0][0]
        assert inserted_data.num_pages is None

    def test_search_empty_query(
        self,
        service: BookService,
        mock_dao: Mock,
        mocker: MockerFixture,
    ) -> None:
        """Empty or whitespace query immediately returns empty list."""
        mock_fetch = mocker.patch.object(service.open_library, "search")

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
            service.open_library,
            "search",
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


class TestGetBookDetails:
    """Tests for BookService.get_book_details and get_editions."""

    def test_returns_book_with_editions(
        self,
        service: BookService,
        mock_dao: Mock,
        fake_book: Book,
        mocker: MockerFixture,
    ) -> None:
        """The book is returned with its editions, mapped correctly."""
        mock_dao.read.return_value = fake_book
        mock_fetch = mocker.patch.object(
            service.open_library,
            "fetch_editions",
            return_value=EDITIONS_PAYLOAD,
        )

        details = service.get_book_details(1)

        assert isinstance(details, BookDetails)
        assert details.id_book == fake_book.id_book
        assert details.title == fake_book.title
        assert details.num_pages == NB_PAGES
        assert details.editions == [
            Edition(
                title="The Hobbit",
                publishers=["Allen & Unwin"],
                publish_date="September 21, 1937",
                num_pages=NB_PAGES,
                isbn="9780261102217",
                language="eng",
            ),
            Edition(title="Bilbo le Hobbit", isbn="2253049417"),
            Edition(),
        ]
        mock_dao.read.assert_called_once_with(1)
        mock_fetch.assert_called_once_with("/works/OL123W")

    def test_book_not_found(
        self,
        service: BookService,
        mock_dao: Mock,
        mocker: MockerFixture,
    ) -> None:
        """Unknown book: BookNotFoundError, Open Library is not called."""
        mock_dao.read.return_value = None
        mock_fetch = mocker.patch.object(
            service.open_library, "fetch_editions",
        )

        with pytest.raises(BookNotFoundError):
            service.get_book_details(999)

        mock_fetch.assert_not_called()

    def test_open_library_down_gives_no_editions(
        self,
        service: BookService,
        mock_dao: Mock,
        fake_book: Book,
        mocker: MockerFixture,
    ) -> None:
        """Open Library unavailable: the book comes with an empty list."""
        mock_dao.read.return_value = fake_book
        mocker.patch.object(
            service.open_library,
            "fetch_editions",
            side_effect=ExternalServiceError(),
        )

        details = service.get_book_details(1)

        assert details.title == fake_book.title
        assert details.editions == []

    @pytest.mark.parametrize("id_book_api", [None, "", "openlib_123"])
    def test_no_work_key_gives_no_editions(
        self,
        service: BookService,
        mock_dao: Mock,
        fake_book: Book,
        mocker: MockerFixture,
        id_book_api: str | None,
    ) -> None:
        """Without a work key, Open Library is not called."""
        mock_dao.read.return_value = fake_book.model_copy(
            update={"id_book_api": id_book_api},
        )
        mock_fetch = mocker.patch.object(
            service.open_library, "fetch_editions",
        )

        details = service.get_book_details(1)

        assert details.editions == []
        mock_fetch.assert_not_called()

    @pytest.mark.parametrize("payload", [{}, {"entries": None}])
    def test_payload_without_entries(
        self,
        service: BookService,
        mock_dao: Mock,
        fake_book: Book,
        mocker: MockerFixture,
        payload: dict[str, object],
    ) -> None:
        """A payload without entries gives an empty list."""
        mock_dao.read.return_value = fake_book
        mocker.patch.object(
            service.open_library, "fetch_editions", return_value=payload,
        )

        assert service.get_book_details(1).editions == []

    def test_sends_work_key_and_limit(
        self,
        service: BookService,
        mock_dao: Mock,
        fake_book: Book,
        http_get: Mock,
    ) -> None:
        """The editions URL is built from the work key, with a limit."""
        mock_dao.read.return_value = fake_book

        service.get_book_details(1)

        assert http_get.call_args.args[0] == EDITIONS_URL
        assert http_get.call_args.kwargs["params"] == {
            "limit": EDITIONS_LIMIT,
        }

    def test_http_error_status_gives_no_editions(
        self,
        service: BookService,
        mock_dao: Mock,
        fake_book: Book,
        http_get: Mock,
    ) -> None:
        """An HTTP error status from Open Library gives an empty list."""
        mock_dao.read.return_value = fake_book
        http_get.return_value.status_code = 503

        assert service.get_book_details(1).editions == []

    def test_network_error_gives_no_editions(
        self,
        service: BookService,
        mock_dao: Mock,
        fake_book: Book,
        http_get: Mock,
    ) -> None:
        """A network error gives an empty list."""
        mock_dao.read.return_value = fake_book
        http_get.side_effect = httpx2.HTTPError("boom")

        assert service.get_book_details(1).editions == []


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

    def test_fields_include_number_of_pages(self) -> None:
        """The median number of pages is requested."""
        assert "number_of_pages_median" in OPEN_LIBRARY_FIELDS.split(",")

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

    def test_search_cache_expires_and_respects_limit(
        self,
        http_get: Mock,
        mocker: MockerFixture,
    ) -> None:
        """Fresh responses are shared across clients for the same limit."""
        clock = mocker.patch(
            "src.services.open_library_client.monotonic", return_value=0.0,
        )
        first = {"docs": [{"title": "The Left Hand of Darkness"}]}
        second = {"docs": [{"title": "The Dispossessed"}]}
        http_get.return_value.json.side_effect = [first, second, second]
        query = "Ursula Le Guin"

        assert OpenLibraryClient().search(query, limit=1) == first
        assert OpenLibraryClient().search(query, limit=1) == first
        http_get.assert_called_once()

        assert OpenLibraryClient().search(query, limit=2) == second
        http_get.reset_mock()
        clock.return_value = SEARCH_CACHE_TTL
        assert OpenLibraryClient().search(query, limit=1) == second
        http_get.assert_called_once()

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

    def test_rejected_query_raises_invalid_search(
        self,
        service: BookService,
        http_get: Mock,
    ) -> None:
        """A 422 from Open Library (q="the") raises InvalidSearchQueryError."""
        http_get.return_value.status_code = 422

        with pytest.raises(InvalidSearchQueryError):
            service.search_books("the")

    def test_network_error_raises(
        self,
        service: BookService,
        http_get: Mock,
    ) -> None:
        """A network error raises ExternalServiceError."""
        http_get.side_effect = httpx2.HTTPError("boom")

        with pytest.raises(ExternalServiceError):
            service.search_by_subject("Fantasy")

    def test_invalid_json_raises(
        self,
        service: BookService,
        http_get: Mock,
    ) -> None:
        """A response that is not JSON raises ExternalServiceError."""
        http_get.return_value.json.side_effect = ValueError("not json")

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
            service.open_library,
            "search",
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
                        "number_of_pages_median": NB_PAGES,
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
        assert hobbit.num_pages == NB_PAGES
        assert result[1][0].num_pages is None
        mock_dao.upsert.assert_not_called()
        mock_dao.create.assert_not_called()

    def test_skips_docs_without_key_or_title(
        self,
        service: BookService,
        mocker: MockerFixture,
    ) -> None:
        """Docs without key or without title are skipped."""
        mocker.patch.object(
            service.open_library,
            "search",
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
        mock_fetch = mocker.patch.object(service.open_library, "search")

        assert service.search_by_subject("   ") == []
        mock_fetch.assert_not_called()

    def test_subject_is_stripped(
        self,
        service: BookService,
        mocker: MockerFixture,
    ) -> None:
        """Spaces around the subject are removed."""
        mock_fetch = mocker.patch.object(
            service.open_library,
            "search",
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
        mocker.patch.object(service.open_library, "search", return_value={})

        assert service.search_by_subject("Fantasy") == []

    def test_open_library_unavailable(
        self,
        service: BookService,
        mocker: MockerFixture,
    ) -> None:
        """ExternalServiceError propagates."""
        mocker.patch.object(
            service.open_library,
            "search",
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
