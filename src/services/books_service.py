"""Service class for book-related business logic.

Integrates local database storage via BookDAO with external book data
retrieved from Open Library.
"""

import logging
from datetime import date
from typing import Any

from src.dao.books_dao import BookDAO
from src.models.books import Book, BookCreate, BookDetails, Edition
from src.services.open_library_client import OpenLibraryClient
from src.utils.exceptions import (
    BookNotFoundError,
    ExternalServiceError,
)

logger = logging.getLogger(__name__)

OPEN_LIBRARY_WORK_PREFIX = "/works/"
MIN_VALID_YEAR = 1
MAX_VALID_YEAR = 9999


def _valid_pages(value: object) -> int | None:
    """Keep a number of pages only if it is a positive integer.

    Parameters
    ----------
    value : object
        Value received from Open Library.

    Returns
    -------
    int | None
        A positive integer page count, or None for an invalid value.

    """
    if isinstance(value, int) and not isinstance(value, bool) and value > 0:
        return value
    return None


def _first(values: object) -> object | None:
    """Return the first element of a list received from Open Library.

    Parameters
    ----------
    values : object
        Value received from Open Library.

    Returns
    -------
    object | None
        The first list element, or None for an empty list or a non-list value.

    """
    if isinstance(values, list) and values:
        return values[0]
    return None


class BookService:
    """Manage the local catalogue and its Open Library integration.

    Attributes
    ----------
    dao : BookDAO
        Associated BookDAO object.
    open_library : OpenLibraryClient
        Client for remote searches and edition lookups.

    """

    def __init__(self, book_dao: BookDAO, timeout: float = 5.0) -> None:
        """Initialize BookService with a BookDAO.

        Parameters
        ----------
        book_dao : BookDAO
            DAO used to access books.
        timeout : float, optional
            HTTP request timeout for external services.

        """
        self.dao = book_dao
        self.open_library = OpenLibraryClient(timeout=timeout)

    @staticmethod
    def _doc_to_book_create(doc: dict[str, Any]) -> BookCreate | None:
        """Normalize an Open Library search result for local storage.

        Parameters
        ----------
        doc : dict[str, Any]
            A document of the "docs" list returned by Open Library.

        Returns
        -------
        BookCreate | None
            The BookCreate, or None if the document has no title.

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
            num_pages=_valid_pages(doc.get("number_of_pages_median")),
        )

    @staticmethod
    def _entry_to_edition(entry: dict[str, Any]) -> Edition:
        """Normalize an Open Library edition entry.

        Parameters
        ----------
        entry : dict[str, Any]
            An item of the "entries" list returned by Open Library.

        Returns
        -------
        Edition
            Edition metadata. An empty publisher list and None values represent
            missing data.

        """
        title = entry.get("title")
        publishers = entry.get("publishers")
        publish_date = entry.get("publish_date")
        isbn = _first(entry.get("isbn_13")) or _first(entry.get("isbn_10"))
        language = _first(entry.get("languages"))
        language_key = (
            language.get("key") if isinstance(language, dict) else None
        )

        return Edition(
            title=title if isinstance(title, str) else None,
            publishers=(
                [name for name in publishers if isinstance(name, str)]
                if isinstance(publishers, list)
                else []
            ),
            publish_date=str(publish_date) if publish_date else None,
            num_pages=_valid_pages(entry.get("number_of_pages")),
            isbn=str(isbn) if isbn else None,
            language=(
                language_key.rsplit("/", 1)[-1]
                if isinstance(language_key, str)
                else None
            ),
        )

    def search_books(self, query: str, limit: int = 10) -> list[Book]:
        """Search Open Library and save the results to the local catalogue.

        Parameters
        ----------
        query : str
            Search query string (title or author).
        limit : int, optional
            Maximum number of books to return.

        Returns
        -------
        list[Book]
            Books saved in the local catalogue, or an empty list for a blank
            query or no results.

        Notes
        -----
        A failed request or invalid response raises ``ExternalServiceError``.

        """
        sanitized_query = query.strip()
        if not sanitized_query:
            return []

        payload = self.open_library.search(sanitized_query, limit=limit)
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
        """Look up Open Library candidates for a given subject.

        Candidates must have an Open Library key so they can be matched with
        local books.

        Parameters
        ----------
        subject : str
            Subject (genre) to search for.
        limit : int, optional
            Maximum number of results to fetch.
        sort : str, optional
            Open Library sort order.

        Returns
        -------
        list[tuple[BookCreate, float | None]]
            Candidate books paired with their Open Library ratings, which may
            be None.

        Notes
        -----
        A failed request or invalid response raises ``ExternalServiceError``.

        """
        sanitized_subject = subject.strip()
        if not sanitized_subject:
            return []

        payload = self.open_library.search(
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

        Parameters
        ----------
        book_create : BookCreate
            Data of the book to save.

        Returns
        -------
        Book
            The saved Book, with its internal ID.

        """
        return self.dao.upsert(book_create)

    def get_book(self, book_id: int) -> Book:
        """Read a book by its internal ID.

        Parameters
        ----------
        book_id : int
            ID of the book.

        Returns
        -------
        Book
            The Book object.

        Raises
        ------
        BookNotFoundError
            If the book does not exist.

        """
        book = self.dao.read(book_id)
        if book is None:
            raise BookNotFoundError(book_id=book_id)
        return book

    def get_editions(self, book: Book) -> list[Edition]:
        """Fetch a book's editions from Open Library.

        Editions are fetched on demand. A missing work key or a failed request
        is logged as a warning.

        Parameters
        ----------
        book : Book
            The book whose editions are wanted.

        Returns
        -------
        list[Edition]
            The editions, or an empty list.

        """
        work_key = book.id_book_api
        if not work_key or not work_key.startswith(OPEN_LIBRARY_WORK_PREFIX):
            logger.warning(
                "Book %s has no Open Library work key: no editions",
                book.id_book,
            )
            return []

        try:
            payload = self.open_library.fetch_editions(work_key)
        except ExternalServiceError:
            logger.warning(
                "Open Library unavailable: no editions for book %s",
                book.id_book,
            )
            return []

        entries = payload.get("entries")
        if not isinstance(entries, list):
            return []
        return [
            self._entry_to_edition(entry)
            for entry in entries
            if isinstance(entry, dict)
        ]

    def get_book_details(self, book_id: int) -> BookDetails:
        """Retrieve a book by its internal ID, with its editions.

        Parameters
        ----------
        book_id : int
            ID of the book.

        Returns
        -------
        BookDetails
            The book and its list of editions.

        Notes
        -----
        An unknown book ID raises ``BookNotFoundError``.

        """
        book = self.get_book(book_id)
        return BookDetails(
            **book.model_dump(),
            editions=self.get_editions(book),
        )

    def get_books(
        self,
        category: str | None = None,
        author: str | None = None,
    ) -> list[Book]:
        """Filter locally stored books by category and/or author.

        Parameters
        ----------
        category : str | None, optional
            Category filter string.
        author : str | None, optional
            Author filter string.

        Returns
        -------
        list[Book]
            List of matching Book objects.

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
        """List catalogue books with optional category and author filters.

        Parameters
        ----------
        category : str | None, optional
            Category filter string.
        author : str | None, optional
            Author filter string.

        Returns
        -------
        list[Book]
            List of matching Book objects.

        """
        return self.get_books(category=category, author=author)
