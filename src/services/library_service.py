"""Service layer for library operations."""

from src.dao.library_dao import LibraryDAO
from src.models.library import (
    LibraryBookAdd,
    LibraryBookDetails,
    LibraryBookRead,
    LibraryBookUpdateDates,
)
from src.utils.exceptions import (
    BookNotInLibraryError,
    InvalidReadingDatesError,
)


class LibraryService:
    """Manage books and reading activity in personal libraries."""

    def __init__(self, dao: LibraryDAO) -> None:
        """Initialize the service with a DAO.

        Parameters
        ----------
        dao : LibraryDAO
            The library data access object.

        """
        self.dao = dao

    def add_book_to_library(
        self,
        id_user: int,
        book_in: LibraryBookAdd,
    ) -> LibraryBookRead:
        """Add a book to the user's library.

        Parameters
        ----------
        id_user : int
            ID of the user.
        book_in : LibraryBookAdd
            Data containing the book ID and reading state.

        Returns
        -------
        LibraryBookRead
            The created library activity.

        Notes
        -----
        A duplicate entry raises ``BookAlreadyInLibraryError``. An unknown book
        ID raises ``BookNotFoundError``.

        """
        return self.dao.add_book(id_user, book_in)

    def remove_book_from_library(self, id_user: int, id_book: int) -> None:
        """Remove a book from the user's library.

        Parameters
        ----------
        id_user : int
            ID of the user.
        id_book : int
            ID of the book to remove.

        Notes
        -----
        A missing library entry raises ``BookNotInLibraryError``.

        """
        self.dao.remove_book(id_user, id_book)

    def toggle_like(self, id_user: int, id_book: int) -> LibraryBookRead:
        """Like or unlike a book in the user's library.

        Parameters
        ----------
        id_user : int
            ID of the user.
        id_book : int
            ID of the book.

        Returns
        -------
        LibraryBookRead
            The updated library activity.

        Notes
        -----
        A missing library entry raises ``BookNotInLibraryError``.

        """
        return self.dao.toggle_like(id_user, id_book)

    def toggle_favorite(
        self,
        id_user: int,
        id_book: int,
    ) -> LibraryBookRead:
        """Add or remove a book from the user's favorites.

        Parameters
        ----------
        id_user : int
            ID of the user.
        id_book : int
            ID of the book.

        Returns
        -------
        LibraryBookRead
            The updated library activity.

        Notes
        -----
        A missing library entry raises ``BookNotInLibraryError``.

        """
        return self.dao.toggle_favorite(id_user, id_book)

    def update_book_status(
        self,
        id_user: int,
        id_book: int,
        state: str,
    ) -> LibraryBookRead:
        """Update the reading status of a book in the user's library.

        Parameters
        ----------
        id_user : int
            ID of the user.
        id_book : int
            ID of the book.
        state : str
            The new reading state.

        Returns
        -------
        LibraryBookRead
            The updated library activity.

        Notes
        -----
        A missing library entry raises ``BookNotInLibraryError``.

        """
        return self.dao.update_status(id_user, id_book, state)

    def update_book_dates(
        self,
        id_user: int,
        id_book: int,
        dates_in: LibraryBookUpdateDates,
    ) -> LibraryBookRead:
        """Update the reading dates of a book in the user's library.

        Only the dates that were sent are changed. A date that was not sent
        keeps its stored value, which is used for the comparison.

        Parameters
        ----------
        id_user : int
            ID of the user.
        id_book : int
            ID of the book.
        dates_in : LibraryBookUpdateDates
            New start and/or end date.

        Returns
        -------
        LibraryBookRead
            The updated library activity.

        Raises
        ------
        ValueError
            If no date is given.
        BookNotInLibraryError
            If the book is not in the library.
        InvalidReadingDatesError
            If the resulting end date is before the resulting start date.

        """
        changes = dates_in.model_dump(exclude_unset=True)
        if not changes:
            msg = "Nothing to update."
            raise ValueError(msg)

        current = self.dao.read(id_user, id_book)
        if current is None:
            raise BookNotInLibraryError(id_book)

        started_at = changes.get("started_at", current.started_at)
        finished_at = changes.get("finished_at", current.finished_at)
        if (
            started_at is not None
            and finished_at is not None
            and finished_at < started_at
        ):
            raise InvalidReadingDatesError

        return self.dao.update_dates(
            id_user,
            id_book,
            started_at,
            finished_at,
        )

    def list_favorites(self, id_user: int) -> list[LibraryBookDetails]:
        """List the favorite books of the user's library.

        Parameters
        ----------
        id_user : int
            ID of the user.

        Returns
        -------
        list[LibraryBookDetails]
            The favorite books, or an empty list if there are none.

        """
        return self.dao.find_favorites_by_user_id(id_user)

    def list_books(
        self,
        id_user: int,
        status: str | None = None,
    ) -> list[LibraryBookDetails]:
        """List the books in a user's library.

        Parameters
        ----------
        id_user : int
            ID of the user.
        status : str | None, optional
            Reading state to filter by.

        Returns
        -------
        list[LibraryBookDetails]
            The user's books, or an empty list if there are none.

        """
        return self.dao.find_books_by_user_id(id_user, status)
