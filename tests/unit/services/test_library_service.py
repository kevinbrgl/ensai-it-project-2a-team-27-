"""Unit tests for LibraryService.

The LibraryDAO is replaced by a mock: no database is needed.
"""

from unittest.mock import Mock

import pytest
from pytest_mock import MockerFixture

from src.dao.library_dao import LibraryDAO
from src.models.library import LibraryBookAdd, LibraryBookRead
from src.services.library_service import LibraryService
from src.utils.exceptions import (
    BookAlreadyInLibraryError,
    BookNotFoundError,
)

ID_USER = 1
ID_BOOK = 100
STATE = "READING"


@pytest.fixture
def mock_dao(mocker: MockerFixture) -> Mock:
    """Return a fake LibraryDAO with the same methods as the real one."""
    return mocker.Mock(spec=LibraryDAO)


@pytest.fixture
def service(mock_dao: Mock) -> LibraryService:
    """Return a LibraryService using the mocked DAO."""
    return LibraryService(mock_dao)


@pytest.fixture
def book_in() -> LibraryBookAdd:
    """Return a valid request payload."""
    return LibraryBookAdd(id_book=ID_BOOK, state=STATE)


@pytest.fixture
def book_read() -> LibraryBookRead:
    """Return a reading activity as returned by the DAO."""
    return LibraryBookRead(
        id_user=ID_USER,
        id_book=ID_BOOK,
        state=STATE,
        is_liked=False,
        is_favorite=False,
    )


class TestAddBookToLibrary:
    """Tests for LibraryService.add_book_to_library."""

    def test_valid(
        self,
        service: LibraryService,
        mock_dao: Mock,
        book_in: LibraryBookAdd,
        book_read: LibraryBookRead,
    ) -> None:
        """Valid request: returns the reading activity."""
        mock_dao.add_book.return_value = book_read

        result = service.add_book_to_library(ID_USER, book_in)

        assert result == book_read
        mock_dao.add_book.assert_called_once_with(ID_USER, book_in)

    def test_already_in_library(
        self,
        service: LibraryService,
        mock_dao: Mock,
        book_in: LibraryBookAdd,
    ) -> None:
        """DAO raises BookAlreadyInLibraryError: it is propagated."""
        mock_dao.add_book.side_effect = BookAlreadyInLibraryError(ID_BOOK)

        with pytest.raises(BookAlreadyInLibraryError):
            service.add_book_to_library(ID_USER, book_in)

        mock_dao.add_book.assert_called_once_with(ID_USER, book_in)

    def test_book_not_found(
        self,
        service: LibraryService,
        mock_dao: Mock,
        book_in: LibraryBookAdd,
    ) -> None:
        """DAO raises BookNotFoundError: it is propagated."""
        mock_dao.add_book.side_effect = BookNotFoundError(ID_BOOK)

        with pytest.raises(BookNotFoundError):
            service.add_book_to_library(ID_USER, book_in)

        mock_dao.add_book.assert_called_once_with(ID_USER, book_in)
