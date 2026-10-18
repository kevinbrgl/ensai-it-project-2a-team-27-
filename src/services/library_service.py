"""Service layer for library operations."""

from src.dao.library_dao import LibraryDAO
from src.models.library import (
    LibraryBookAdd,
    LibraryBookDetails,
    LibraryBookRead,
)


class LibraryService:
    """Service class for managing a user's library."""

    def __init__(self, dao: LibraryDAO) -> None:
        """Initialize the service with a DAO.

        :param dao: The library data access object
        """
        self.dao = dao

    def add_book_to_library(
        self,
        id_user: int,
        book_in: LibraryBookAdd,
    ) -> LibraryBookRead:
        """Add a book to the user's library.

        :param id_user: ID of the user
        :param book_in: Data containing the book ID and reading state
        :return: The created library activity
        """
        return self.dao.add_book(id_user, book_in)

    def remove_book_from_library(self, id_user: int, id_book: int) -> None:
        """Remove a book from the user's library.

        :param id_user: ID of the user
        :param id_book: ID of the book to remove
        """
        self.dao.remove_book(id_user, id_book)

    def toggle_like(self, id_user: int, id_book: int) -> LibraryBookRead:
        """Like or unlike a book in the user's library.

        :param id_user: ID of the user
        :param id_book: ID of the book
        :return: The updated library activity
        """
        return self.dao.toggle_like(id_user, id_book)

    def toggle_favorite(
        self,
        id_user: int,
        id_book: int,
    ) -> LibraryBookRead:
        """Add or remove a book from the user's favorites.

        :param id_user: ID of the user
        :param id_book: ID of the book
        :return: The updated library activity
        """
        return self.dao.toggle_favorite(id_user, id_book)

    def list_favorites(self, id_user: int) -> list[LibraryBookDetails]:
        """List the favorite books of the user's library.
        :param id_user: ID of the user
        :return: The favorite books, or an empty list if there are none
        """
        return self.dao.find_favorites_by_user_id(id_user)
