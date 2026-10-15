"""Service layer for library operations."""

from src.dao.library_dao import LibraryDAO
from src.models.library import LibraryBookAdd, LibraryBookRead


class LibraryService:
    """Service class for managing a user's library."""

    def __init__(self, dao: LibraryDAO) -> None:
        """Initialize the service with a DAO.

        :param dao: The library data access object
        """
        self.dao = dao

    def add_book_to_library(
        self, id_user: int, book_in: LibraryBookAdd,
    ) -> LibraryBookRead:
        """Add a book to the user's library.

        :param id_user: ID of the user
        :param book_in: Data containing the book ID and reading state
        :return: The created library activity
        """
        return self.dao.add_book(id_user, book_in)
