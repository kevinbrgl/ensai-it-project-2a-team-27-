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

    def _fetch_open_library(self, query: str, limit: int) -> dict[str, Any]:
        """Fetch search results from Open Library.

        :param query: Search query (title or author)
        :param limit: Maximum number of results to fetch
        :raises ExternalServiceError: If Open Library is unreachable or fails
        :return: JSON payload returned by Open Library
        """
        headers = {"User-Agent": "Ex-Libris/1.0 (contact@ex-libris.fr)"}
        params: dict[str, str | int] = {"q": query, "limit": limit}

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
            title = doc.get("title")
            if not title:
                continue

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

            book_create = BookCreate(
                id_book_api=doc.get("key"),
                title=title[:255],
                author=author[:255] if author else None,
                category=category[:100] if category else None,
                publish_date=publish_date,
                description=None,
                cover_image=cover_image,
            )

            persisted_book = self.dao.upsert(book_create)
            results.append(persisted_book)

        return results

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
