"""Service class for book-related business logic.

Integrates local database storage via BookDAO with external book data
retrieved from Open Library.
"""

import logging
from datetime import date
from typing import Any

import httpx2

from src.dao.books_dao import BookDAO
from src.models.books import Book, BookCreate
from src.utils.exceptions import BookNotFoundError, ExternalServiceError

logger = logging.getLogger(__name__)

OPEN_LIBRARY_SEARCH_URL = "https://openlibrary.org/search.json"
OPEN_LIBRARY_FIELDS = (
    "key,title,author_name,subject,first_publish_year,cover_i,"
    "ratings_average"
)
HTTP_ERROR_STATUS = 400
MIN_VALID_YEAR = 1
MAX_VALID_YEAR = 9999


class BookService:
    """Service class for book operations and Open Library integration.

    :attr dao: Associated BookDAO object
    :attr timeout: Timeout in seconds for external requests
    """

    def __init__(self, book_dao: BookDAO, timeout: float = 5.0) -> None:
        """Initialize BookService with a BookDAO.

        :param book_dao: DAO used to access books
        :param timeout: HTTP request timeout for external services
        """
        self.dao = book_dao
        self.timeout = timeout

    def _fetch_open_library(
        self,
        query: str | None = None,
        limit: int = 10,
        *,
        subject: str | None = None,
        sort: str | None = None,
    ) -> dict[str, Any]:
        """Fetch search results from Open Library.

        :param query: Free-text search query (title or author)
        :param limit: Maximum number of results to fetch
        :param subject: Optional subject (genre) filter
        :param sort: Optional Open Library sort order (e.g. "rating")
        :raises ExternalServiceError: If Open Library is unreachable or fails
        :return: JSON payload returned by Open Library
        """
        headers = {"User-Agent": "Ex-Libris/1.0 (contact@ex-libris.fr)"}
        params: dict[str, str | int] = {
            "limit": limit,
            "fields": OPEN_LIBRARY_FIELDS,
        }
        if query:
            params["q"] = query
        if subject:
            params["subject"] = subject
        if sort:
            params["sort"] = sort

        try:
            with httpx2.Client(timeout=self.timeout) as client:
                response = client.get(
                    OPEN_LIBRARY_SEARCH_URL,
                    params=params,
                    headers=headers,
                )
        except httpx2.HTTPError as exc:
            logger.warning("Open Library HTTP error: %s", exc)
            raise ExternalServiceError from exc
        except Exception as exc:
            logger.exception("Unexpected error querying Open Library")
            raise ExternalServiceError from exc

        if response.status_code >= HTTP_ERROR_STATUS:
            logger.error(
                "Open Library returned HTTP error %d",
                response.status_code,
            )
            raise ExternalServiceError

        return response.json()

    @staticmethod
    def _doc_to_book_create(doc: dict[str, Any]) -> BookCreate | None:
        """Convert one Open Library search document into a BookCreate.

        :param doc: A document of the "docs" list returned by Open Library
        :return: The BookCreate, or None if the document has no title
        """
        title = doc.get("title")
        if not title:
            return None

        authors = doc.get("author_name", [])
        author = ", ".join(authors) if authors else None

        subjects = doc.get("subject", [])
        category = subjects[0] if subjects else None

        publish_year = doc.get("first_publish_year")
        publish_date = (
            date(publish_year, 1, 1)
            if isinstance(publish_year, int)
            and MIN_VALID_YEAR <= publish_year <= MAX_VALID_YEAR
            else None
        )

        cover_i = doc.get("cover_i")
        cover_image = (
            f"https://covers.openlibrary.org/b/id/{cover_i}-M.jpg"
            if cover_i
            else None
        )

        return BookCreate(
            id_book_api=doc.get("key"),
            title=title[:255],
            author=author[:255] if author else None,
            category=category[:100] if category else None,
            publish_date=publish_date,
            description=None,
            cover_image=cover_image,
        )

    def search_books(self, query: str, limit: int = 10) -> list[Book]:
        """Search books on Open Library and synchronize them in the local DB.

        :param query: Search query string (title or author)
        :param limit: Maximum number of books to return
        :raises ExternalServiceError: Raised if Open Library is unavailable
        :return: List of normalized Book objects persisted locally
        """
        sanitized_query = query.strip()
        if not sanitized_query:
            return []

        payload = self._fetch_open_library(sanitized_query, limit=limit)
        docs = payload.get("docs", [])

        results: list[Book] = []
        for doc in docs:
            book_create = self._doc_to_book_create(doc)
            if book_create is None:
                continue
            results.append(self.dao.upsert(book_create))

        return results

    def search_by_subject(
        self,
        subject: str,
        limit: int = 10,
        sort: str = "rating",
    ) -> list[tuple[BookCreate, float | None]]:
        """Search Open Library by subject, without saving the results.

        Only documents with an Open Library key are kept, so that they
        can be deduplicated and compared with a user's library.

        :param subject: Subject (genre) to search for
        :param limit: Maximum number of results to fetch
        :param sort: Open Library sort order
        :raises ExternalServiceError: Raised if Open Library is unavailable
        :return: The candidate books with their Open Library rating
        """
        sanitized_subject = subject.strip()
        if not sanitized_subject:
            return []

        payload = self._fetch_open_library(
            limit=limit,
            subject=sanitized_subject,
            sort=sort,
        )

        candidates: list[tuple[BookCreate, float | None]] = []
        for doc in payload.get("docs", []):
            book_create = self._doc_to_book_create(doc)
            if book_create is None or not book_create.id_book_api:
                continue
            rating = doc.get("ratings_average")
            open_library_rating = (
                round(float(rating), 2)
                if isinstance(rating, int | float)
                else None
            )
            candidates.append((book_create, open_library_rating))

        return candidates

    def save_book(self, book_create: BookCreate) -> Book:
        """Insert or update a book in the local database.

        :param book_create: Data of the book to save
        :return: The saved Book, with its internal ID
        """
        return self.dao.upsert(book_create)

    def get_book(self, book_id: int) -> Book:
        """Read a book by its internal ID.

        :param book_id: ID of the book
        :raises BookNotFoundError: Raised if the book does not exist
        :return: The Book object
        """
        book = self.dao.read(book_id)
        if book is None:
            raise BookNotFoundError(book_id=book_id)
        return book

    def get_book_details(self, book_id: int) -> Book:
        """Retrieve details of a book by its internal ID.

        :param book_id: ID of the book
        :raises BookNotFoundError: Raised if the book does not exist
        :return: The Book object
        """
        return self.get_book(book_id)

    def get_books(
        self,
        category: str | None = None,
        author: str | None = None,
    ) -> list[Book]:
        """Filter locally stored books by category and/or author.

        :param category: Optional category filter string
        :param author: Optional author filter string
        :return: List of matching Book objects
        """
        clean_category = (
            category.strip()
            if category is not None and category.strip()
            else None
        )
        clean_author = (
            author.strip() if author is not None and author.strip() else None
        )

        if clean_category and clean_author:
            return self.dao.find_books(
                category=clean_category,
                author=clean_author,
            )
        if clean_category:
            return self.dao.find_by_category(clean_category)
        if clean_author:
            return self.dao.find_by_author(clean_author)
        return self.dao.find_all()

    def get_catalogue(
        self,
        category: str | None = None,
        author: str | None = None,
    ) -> list[Book]:
        """Alias for get_books to retrieve the book catalogue.

        :param category: Optional category filter string
        :param author: Optional author filter string
        :return: List of matching Book objects
        """
        return self.get_books(category=category, author=author)
