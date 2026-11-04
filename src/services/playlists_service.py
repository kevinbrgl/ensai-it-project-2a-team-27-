"""Service layer for playlist operations."""

from src.dao.playlists_dao import PlaylistDAO
from src.models.playlists import (
    PlaylistBookAdd,
    PlaylistBookRead,
    PlaylistCreate,
    PlaylistDetails,
    PlaylistRead,
    PlaylistUpdate,
)
from src.utils.exceptions import PlaylistNotFoundError


class PlaylistService:
    """Service class for managing a user's playlists."""

    def __init__(self, dao: PlaylistDAO) -> None:
        """Initialize the service with a DAO.

        :param dao: The playlist data access object
        """
        self.dao = dao

    def create_playlist(
        self,
        id_user: int,
        playlist_in: PlaylistCreate,
    ) -> PlaylistRead:
        """Create a playlist for the user.

        :param id_user: ID of the owner of the playlist
        :param playlist_in: Name of the playlist
        :return: The created playlist
        """
        return self.dao.create(id_user, playlist_in)

    def list_playlists(self, id_user: int) -> list[PlaylistRead]:
        """List the playlists of the user.

        :param id_user: ID of the owner of the playlists
        :return: The playlists, or an empty list if there are none
        """
        return self.dao.find_by_user_id(id_user)

    def rename_playlist(
        self,
        id_user: int,
        id_playlist: int,
        playlist_in: PlaylistUpdate,
    ) -> PlaylistRead:
        """Rename one of the user's playlists.

        :param id_user: ID of the owner of the playlist
        :param id_playlist: ID of the playlist to rename
        :param playlist_in: New name of the playlist
        :return: The renamed playlist
        """
        return self.dao.rename(id_user, id_playlist, playlist_in)

    def delete_playlist(self, id_user: int, id_playlist: int) -> None:
        """Delete one of the user's playlists.

        :param id_user: ID of the owner of the playlist
        :param id_playlist: ID of the playlist to delete
        """
        self.dao.delete(id_user, id_playlist)

    def _get_own_playlist(
        self,
        id_user: int,
        id_playlist: int,
    ) -> PlaylistRead:
        """Return one of the user's playlists.

        :param id_user: ID of the user who must own the playlist
        :param id_playlist: ID of the playlist
        :raises PlaylistNotFoundError: If the playlist does not exist or
            belongs to another user
        :return: The playlist
        """
        playlist = self.dao.read(id_user, id_playlist)
        if playlist is None:
            raise PlaylistNotFoundError(id_playlist)
        return playlist

    def add_book_to_playlist(
        self,
        id_user: int,
        id_playlist: int,
        book_in: PlaylistBookAdd,
    ) -> PlaylistBookRead:
        """Add a book to one of the user's playlists.

        :param id_user: ID of the owner of the playlist
        :param id_playlist: ID of the playlist
        :param book_in: ID of the book to add
        :raises PlaylistNotFoundError: If the playlist does not exist or
            belongs to another user
        :return: The added playlist entry
        """
        self._get_own_playlist(id_user, id_playlist)
        return self.dao.add_book(id_playlist, book_in.id_book)

    def get_playlist(
        self,
        id_user: int,
        id_playlist: int,
    ) -> PlaylistDetails:
        """Return one of the user's playlists, with its books.

        :param id_user: ID of the owner of the playlist
        :param id_playlist: ID of the playlist
        :raises PlaylistNotFoundError: If the playlist does not exist or
            belongs to another user
        :return: The playlist and the details of its books
        """
        playlist = self._get_own_playlist(id_user, id_playlist)
        books = self.dao.find_books(id_playlist)
        return PlaylistDetails(**playlist.model_dump(), books=books)

    def remove_book_from_playlist(
        self,
        id_user: int,
        id_playlist: int,
        id_book: int,
    ) -> None:
        """Remove a book from one of the user's playlists.

        :param id_user: ID of the owner of the playlist
        :param id_playlist: ID of the playlist
        :param id_book: ID of the book to remove
        :raises PlaylistNotFoundError: If the playlist does not exist or
            belongs to another user
        """
        self._get_own_playlist(id_user, id_playlist)
        self.dao.remove_book(id_playlist, id_book)
