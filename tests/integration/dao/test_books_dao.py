"""Integration tests for BookDAO, run against the database.

Each test is rolled back (see tests/integration/conftest.py),
so the database is left unchanged.
"""

from datetime import date

import pytest

from src.dao.books_dao import BookDAO
from src.models.books import Book, BookCreate


@pytest.fixture
def sample_book_create() -> BookCreate:
    """Return sample book data for creation."""
    return BookCreate(
        id_book_api="/works/OL001W",
        title="Dune",
        author="Frank Herbert",
        category="Science Fiction",
        publish_date=date(1965, 8, 1),
        description="Epic sci-fi novel",
        cover_image="https://covers.openlibrary.org/b/id/111-M.jpg",
    )


@pytest.fixture
def created_book(
    book_dao: BookDAO,
    sample_book_create: BookCreate,
) -> Book:
    """Insert a book and return it."""
    return book_dao.create(sample_book_create)


class TestCreate:
    """Tests for BookDAO.create."""

    def test_ok(
        self,
        book_dao: BookDAO,
        sample_book_create: BookCreate,
    ) -> None:
        """The book is inserted and returned with its generated id."""
        book = book_dao.create(sample_book_create)

        assert isinstance(book.id_book, int)
        assert book.title == sample_book_create.title
        assert book.author == sample_book_create.author
        assert book.category == sample_book_create.category
        assert book.publish_date == sample_book_create.publish_date
        assert book.id_book_api == sample_book_create.id_book_api


class TestUpsert:
    """Tests for BookDAO.upsert."""

    def test_upsert_new(
        self,
        book_dao: BookDAO,
        sample_book_create: BookCreate,
    ) -> None:
        """Upsert inserts a new book if not existing."""
        book = book_dao.upsert(sample_book_create)
        assert isinstance(book.id_book, int)
        assert book.title == sample_book_create.title

    def test_upsert_existing_updates(
        self,
        book_dao: BookDAO,
        created_book: Book,
    ) -> None:
        """Upsert on an existing id_book_api updates and preserves id_book."""
        update_data = BookCreate(
            id_book_api=created_book.id_book_api,
            title="Dune (Updated Edition)",
            author="Frank Herbert",
            category="Sci-Fi / Space Opera",
        )
        updated_book = book_dao.upsert(update_data)

        assert updated_book.id_book == created_book.id_book
        assert updated_book.title == "Dune (Updated Edition)"
        assert updated_book.category == "Sci-Fi / Space Opera"


class TestRead:
    """Tests for BookDAO.read and read_by_api_id."""

    def test_read_found(self, book_dao: BookDAO, created_book: Book) -> None:
        """Reading an existing book returns it."""
        found = book_dao.read(created_book.id_book)
        assert found == created_book

    def test_read_not_found(self, book_dao: BookDAO) -> None:
        """Reading an unknown id returns None."""
        assert book_dao.read(999_999_999) is None

    def test_read_by_api_id(
        self,
        book_dao: BookDAO,
        created_book: Book,
    ) -> None:
        """Reading by external API ID returns the book."""
        found = book_dao.read_by_api_id(created_book.id_book_api or "")
        assert found == created_book


class TestFind:
    """Tests for BookDAO search and filter methods."""

    def test_find_by_author(
        self,
        book_dao: BookDAO,
        created_book: Book,
    ) -> None:
        """Filter by author returns matching books."""
        results = book_dao.find_by_author("Herbert")
        assert len(results) >= 1
        assert any(b.id_book == created_book.id_book for b in results)

    def test_find_by_category(
        self,
        book_dao: BookDAO,
        created_book: Book,
    ) -> None:
        """Filter by category returns matching books."""
        results = book_dao.find_by_category("Science Fiction")
        assert len(results) >= 1
        assert any(b.id_book == created_book.id_book for b in results)
