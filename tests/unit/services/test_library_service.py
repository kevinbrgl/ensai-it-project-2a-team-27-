"""Unit tests for LibraryService.

The LibraryDAO is replaced by a mock: no database is needed.
"""

from datetime import date
from unittest.mock import Mock

import pytest
from pydantic import ValidationError
from pytest_mock import MockerFixture

from src.dao.library_dao import LibraryDAO
from src.models.library import (
    LibraryBookAdd,
    LibraryBookRead,
    LibraryBookUpdateDates,
    LibraryBookUpdateStatus,
)
from src.services.library_service import LibraryService
from src.utils.exceptions import (
    BookAlreadyInLibraryError,
    BookNotFoundError,
    BookNotInLibraryError,
    InvalidReadingDatesError,
)

ID_USER = 1
ID_BOOK = 100
STATE = "READING"
START = date(2026, 1, 5)
END = date(2026, 1, 20)
BEFORE_START = date(2026, 1, 1)


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


class TestReadingStates:
    """Tests for the reading states accepted by the request models."""

    @pytest.mark.parametrize(
        "state",
        ["WANT_TO_READ", "READING", "COMPLETED", "ABANDONED"],
    )
    def test_valid_states(self, state: str) -> None:
        """The four reading states are accepted, ABANDONED included."""
        assert LibraryBookAdd(id_book=ID_BOOK, state=state).state == state
        assert LibraryBookUpdateStatus(state=state).state == state

    def test_unknown_state_rejected(self) -> None:
        """Any other state is refused by both models."""
        with pytest.raises(ValidationError):
            LibraryBookAdd(id_book=ID_BOOK, state="FINISHED")
        with pytest.raises(ValidationError):
            LibraryBookUpdateStatus(state="FINISHED")


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


class TestRemoveBookFromLibrary:
    """Tests for LibraryService.remove_book_from_library."""

    def test_valid(self, service: LibraryService, mock_dao: Mock) -> None:
        """Valid request: the DAO is called with the right arguments."""
        service.remove_book_from_library(ID_USER, ID_BOOK)

        mock_dao.remove_book.assert_called_once_with(ID_USER, ID_BOOK)

    def test_not_in_library(
        self,
        service: LibraryService,
        mock_dao: Mock,
    ) -> None:
        """DAO raises BookNotInLibraryError: it is propagated."""
        mock_dao.remove_book.side_effect = BookNotInLibraryError(ID_BOOK)

        with pytest.raises(BookNotInLibraryError):
            service.remove_book_from_library(ID_USER, ID_BOOK)

        mock_dao.remove_book.assert_called_once_with(ID_USER, ID_BOOK)


class TestToggleLike:
    """Tests for LibraryService.toggle_like."""

    def test_valid(
        self,
        service: LibraryService,
        mock_dao: Mock,
        book_read: LibraryBookRead,
    ) -> None:
        """Valid request: returns the updated reading activity."""
        liked = book_read.model_copy(update={"is_liked": True})
        mock_dao.toggle_like.return_value = liked

        result = service.toggle_like(ID_USER, ID_BOOK)

        assert result == liked
        mock_dao.toggle_like.assert_called_once_with(ID_USER, ID_BOOK)

    def test_not_in_library(
        self,
        service: LibraryService,
        mock_dao: Mock,
    ) -> None:
        """DAO raises BookNotInLibraryError: it is propagated."""
        mock_dao.toggle_like.side_effect = BookNotInLibraryError(ID_BOOK)

        with pytest.raises(BookNotInLibraryError):
            service.toggle_like(ID_USER, ID_BOOK)

        mock_dao.toggle_like.assert_called_once_with(ID_USER, ID_BOOK)


class TestToggleFavorite:
    """Tests for LibraryService.toggle_favorite."""

    def test_valid(
        self,
        service: LibraryService,
        mock_dao: Mock,
        book_read: LibraryBookRead,
    ) -> None:
        """Valid request: returns the updated reading activity."""
        favorite = book_read.model_copy(update={"is_favorite": True})
        mock_dao.toggle_favorite.return_value = favorite

        result = service.toggle_favorite(ID_USER, ID_BOOK)

        assert result == favorite
        mock_dao.toggle_favorite.assert_called_once_with(ID_USER, ID_BOOK)

    def test_not_in_library(
        self,
        service: LibraryService,
        mock_dao: Mock,
    ) -> None:
        """DAO raises BookNotInLibraryError: it is propagated."""
        mock_dao.toggle_favorite.side_effect = BookNotInLibraryError(ID_BOOK)

        with pytest.raises(BookNotInLibraryError):
            service.toggle_favorite(ID_USER, ID_BOOK)

        mock_dao.toggle_favorite.assert_called_once_with(ID_USER, ID_BOOK)


class TestListFavorites:
    """Tests for LibraryService.list_favorites."""

    def test_valid(
        self,
        service: LibraryService,
        mock_dao: Mock,
        book_read: LibraryBookRead,
    ) -> None:
        """The favorites returned by the DAO are returned as they are."""
        favorite = book_read.model_copy(update={"is_favorite": True})
        mock_dao.find_favorites_by_user_id.return_value = [favorite]

        result = service.list_favorites(ID_USER)

        assert result == [favorite]
        mock_dao.find_favorites_by_user_id.assert_called_once_with(ID_USER)

    def test_no_favorites(
        self,
        service: LibraryService,
        mock_dao: Mock,
    ) -> None:
        """No favorites: returns an empty list, without error."""
        mock_dao.find_favorites_by_user_id.return_value = []

        result = service.list_favorites(ID_USER)

        assert result == []
        mock_dao.find_favorites_by_user_id.assert_called_once_with(ID_USER)


class TestListBooks:
    """Tests for LibraryService.list_books."""

    def test_valid_no_status(
        self,
        service: LibraryService,
        mock_dao: Mock,
    ) -> None:
        """Valid request without status calls DAO with None."""
        mock_dao.find_books_by_user_id.return_value = []

        result = service.list_books(ID_USER)

        assert result == []
        mock_dao.find_books_by_user_id.assert_called_once_with(ID_USER, None)

    def test_valid_with_status(
        self,
        service: LibraryService,
        mock_dao: Mock,
    ) -> None:
        """Valid request with status forwards the filter to DAO."""
        mock_dao.find_books_by_user_id.return_value = []

        result = service.list_books(ID_USER, status="READING")

        assert result == []
        mock_dao.find_books_by_user_id.assert_called_once_with(
            ID_USER,
            "READING",
        )

    def test_abandoned_status(
        self,
        service: LibraryService,
        mock_dao: Mock,
    ) -> None:
        """The ABANDONED filter is forwarded to the DAO like the others."""
        mock_dao.find_books_by_user_id.return_value = []

        service.list_books(ID_USER, status="ABANDONED")

        mock_dao.find_books_by_user_id.assert_called_once_with(
            ID_USER,
            "ABANDONED",
        )


class TestUpdateBookStatus:
    """Tests for LibraryService.update_book_status."""

    def test_valid(
        self,
        service: LibraryService,
        mock_dao: Mock,
        book_read: LibraryBookRead,
    ) -> None:
        """Valid request: returns the updated reading activity."""
        updated_book = book_read.model_copy(update={"state": "COMPLETED"})
        mock_dao.update_status.return_value = updated_book

        result = service.update_book_status(ID_USER, ID_BOOK, "COMPLETED")

        assert result == updated_book
        mock_dao.update_status.assert_called_once_with(
            ID_USER,
            ID_BOOK,
            "COMPLETED",
        )

    def test_abandoned(
        self,
        service: LibraryService,
        mock_dao: Mock,
        book_read: LibraryBookRead,
    ) -> None:
        """A book can be marked as abandoned."""
        abandoned = book_read.model_copy(update={"state": "ABANDONED"})
        mock_dao.update_status.return_value = abandoned

        result = service.update_book_status(ID_USER, ID_BOOK, "ABANDONED")

        assert result.state == "ABANDONED"
        mock_dao.update_status.assert_called_once_with(
            ID_USER,
            ID_BOOK,
            "ABANDONED",
        )

    def test_not_in_library(
        self,
        service: LibraryService,
        mock_dao: Mock,
    ) -> None:
        """DAO raises BookNotInLibraryError: it is propagated."""
        mock_dao.update_status.side_effect = BookNotInLibraryError(ID_BOOK)

        with pytest.raises(BookNotInLibraryError):
            service.update_book_status(ID_USER, ID_BOOK, "COMPLETED")

        mock_dao.update_status.assert_called_once_with(
            ID_USER,
            ID_BOOK,
            "COMPLETED",
        )


class TestUpdateBookDates:
    """Tests for LibraryService.update_book_dates."""

    def test_both_dates(
        self,
        service: LibraryService,
        mock_dao: Mock,
        book_read: LibraryBookRead,
    ) -> None:
        """Both dates are sent: both are written and returned."""
        updated = book_read.model_copy(
            update={"started_at": START, "finished_at": END},
        )
        mock_dao.read.return_value = book_read
        mock_dao.update_dates.return_value = updated

        result = service.update_book_dates(
            ID_USER,
            ID_BOOK,
            LibraryBookUpdateDates(started_at=START, finished_at=END),
        )

        assert result == updated
        mock_dao.read.assert_called_once_with(ID_USER, ID_BOOK)
        mock_dao.update_dates.assert_called_once_with(
            ID_USER,
            ID_BOOK,
            START,
            END,
        )

    def test_partial_update_keeps_stored_date(
        self,
        service: LibraryService,
        mock_dao: Mock,
        book_read: LibraryBookRead,
    ) -> None:
        """Only the end date is sent: the stored start date is kept."""
        mock_dao.read.return_value = book_read.model_copy(
            update={"started_at": START},
        )

        service.update_book_dates(
            ID_USER,
            ID_BOOK,
            LibraryBookUpdateDates(finished_at=END),
        )

        mock_dao.update_dates.assert_called_once_with(
            ID_USER,
            ID_BOOK,
            START,
            END,
        )

    def test_null_erases_a_date(
        self,
        service: LibraryService,
        mock_dao: Mock,
        book_read: LibraryBookRead,
    ) -> None:
        """A date sent as null is erased, the other one is kept."""
        mock_dao.read.return_value = book_read.model_copy(
            update={"started_at": START, "finished_at": END},
        )

        service.update_book_dates(
            ID_USER,
            ID_BOOK,
            LibraryBookUpdateDates(finished_at=None),
        )

        mock_dao.update_dates.assert_called_once_with(
            ID_USER,
            ID_BOOK,
            START,
            None,
        )

    def test_same_day_allowed(
        self,
        service: LibraryService,
        mock_dao: Mock,
        book_read: LibraryBookRead,
    ) -> None:
        """A book started and finished the same day is accepted."""
        mock_dao.read.return_value = book_read

        service.update_book_dates(
            ID_USER,
            ID_BOOK,
            LibraryBookUpdateDates(started_at=START, finished_at=START),
        )

        mock_dao.update_dates.assert_called_once_with(
            ID_USER,
            ID_BOOK,
            START,
            START,
        )

    def test_empty_body(
        self,
        service: LibraryService,
        mock_dao: Mock,
    ) -> None:
        """Nothing is sent: ValueError, the DAO is not called."""
        with pytest.raises(ValueError, match="Nothing to update"):
            service.update_book_dates(
                ID_USER,
                ID_BOOK,
                LibraryBookUpdateDates(),
            )

        mock_dao.read.assert_not_called()
        mock_dao.update_dates.assert_not_called()

    def test_not_in_library(
        self,
        service: LibraryService,
        mock_dao: Mock,
    ) -> None:
        """Book not in the library: BookNotInLibraryError, no update."""
        mock_dao.read.return_value = None

        with pytest.raises(BookNotInLibraryError):
            service.update_book_dates(
                ID_USER,
                ID_BOOK,
                LibraryBookUpdateDates(started_at=START),
            )

        mock_dao.update_dates.assert_not_called()

    def test_end_before_start(
        self,
        service: LibraryService,
        mock_dao: Mock,
        book_read: LibraryBookRead,
    ) -> None:
        """Both dates sent, end before start: refused, no update."""
        mock_dao.read.return_value = book_read

        with pytest.raises(InvalidReadingDatesError):
            service.update_book_dates(
                ID_USER,
                ID_BOOK,
                LibraryBookUpdateDates(started_at=END, finished_at=START),
            )

        mock_dao.update_dates.assert_not_called()

    def test_end_before_stored_start(
        self,
        service: LibraryService,
        mock_dao: Mock,
        book_read: LibraryBookRead,
    ) -> None:
        """Only the end is sent, before the stored start: refused."""
        mock_dao.read.return_value = book_read.model_copy(
            update={"started_at": START},
        )

        with pytest.raises(InvalidReadingDatesError):
            service.update_book_dates(
                ID_USER,
                ID_BOOK,
                LibraryBookUpdateDates(finished_at=BEFORE_START),
            )

        mock_dao.update_dates.assert_not_called()

    def test_start_after_stored_end(
        self,
        service: LibraryService,
        mock_dao: Mock,
        book_read: LibraryBookRead,
    ) -> None:
        """Only the start is sent, after the stored end: refused."""
        mock_dao.read.return_value = book_read.model_copy(
            update={"finished_at": START},
        )

        with pytest.raises(InvalidReadingDatesError):
            service.update_book_dates(
                ID_USER,
                ID_BOOK,
                LibraryBookUpdateDates(started_at=END),
            )

        mock_dao.update_dates.assert_not_called()
