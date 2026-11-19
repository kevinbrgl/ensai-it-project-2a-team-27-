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
    """Manage personal book playlists."""

    def __init__(self, dao: PlaylistDAO) -> None:
        """Initialize the service with a DAO.

        Parameters
        ----------
        dao : PlaylistDAO
            The playlist data access object.

        """
        self.dao = dao

    def create_playlist(
        self,
        id_user: int,
        playlist_in: PlaylistCreate,
    ) -> PlaylistRead:
        """Create a playlist for the user.

        Parameters
        ----------
        id_user : int
            ID of the owner of the playlist.
        playlist_in : PlaylistCreate
            Name of the playlist.

        Returns
        -------
        PlaylistRead
            The created playlist.

        Notes
        -----
        A playlist with the same name for this user raises
        ``PlaylistAlreadyExistsError``.

        """
        return self.dao.create(id_user, playlist_in)

    def list_playlists(self, id_user: int) -> list[PlaylistRead]:
        """List the playlists of the user.

        Parameters
        ----------
        id_user : int
            ID of the owner of the playlists.

        Returns
        -------
        list[PlaylistRead]
            The playlists, or an empty list if there are none.

        """
        return self.dao.find_by_user_id(id_user)

    def rename_playlist(
        self,
        id_user: int,
        id_playlist: int,
        playlist_in: PlaylistUpdate,
    ) -> PlaylistRead:
        """Rename one of the user's playlists.

        Parameters
        ----------
        id_user : int
            ID of the owner of the playlist.
        id_playlist : int
            ID of the playlist to rename.
        playlist_in : PlaylistUpdate
            New name of the playlist.

        Returns
        -------
        PlaylistRead
            The renamed playlist.

        Notes
        -----
        An unknown or inaccessible playlist raises ``PlaylistNotFoundError``.
        A duplicate name for this user raises ``PlaylistAlreadyExistsError``.

        """
        return self.dao.rename(id_user, id_playlist, playlist_in)

    def delete_playlist(self, id_user: int, id_playlist: int) -> None:
        """Delete one of the user's playlists.

        Parameters
        ----------
        id_user : int
            ID of the owner of the playlist.
        id_playlist : int
            ID of the playlist to delete.

        Notes
        -----
        An unknown or inaccessible playlist raises ``PlaylistNotFoundError``.

        """
        self.dao.delete(id_user, id_playlist)

    def _get_own_playlist(
        self,
        id_user: int,
        id_playlist: int,
    ) -> PlaylistRead:
        """Return one of the user's playlists.

        Parameters
        ----------
        id_user : int
            ID of the user who must own the playlist.
        id_playlist : int
            ID of the playlist.

        Returns
        -------
        PlaylistRead
            The playlist.

        Raises
        ------
        PlaylistNotFoundError
            If the playlist is absent from the user's playlists.

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

        Parameters
        ----------
        id_user : int
            ID of the owner of the playlist.
        id_playlist : int
            ID of the playlist.
        book_in : PlaylistBookAdd
            ID of the book to add.

        Returns
        -------
        PlaylistBookRead
            The added playlist entry.

        Notes
        -----
        An unknown or inaccessible playlist raises ``PlaylistNotFoundError``.
        A duplicate entry raises ``BookAlreadyInPlaylistError``. An unknown
        book ID raises ``BookNotFoundError``.

        """
        self._get_own_playlist(id_user, id_playlist)
        return self.dao.add_book(id_playlist, book_in.id_book)

    def get_playlist(
        self,
        id_user: int,
        id_playlist: int,
    ) -> PlaylistDetails:
        """Return one of the user's playlists, with its books.

        Parameters
        ----------
        id_user : int
            ID of the owner of the playlist.
        id_playlist : int
            ID of the playlist.

        Returns
        -------
        PlaylistDetails
            The playlist and the details of its books.

        Notes
        -----
        An unknown or inaccessible playlist raises ``PlaylistNotFoundError``.

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

        Parameters
        ----------
        id_user : int
            ID of the owner of the playlist.
        id_playlist : int
            ID of the playlist.
        id_book : int
            ID of the book to remove.

        Notes
        -----
        An unknown or inaccessible playlist raises ``PlaylistNotFoundError``.
        A missing playlist entry raises ``BookNotInPlaylistError``.

        """
        self._get_own_playlist(id_user, id_playlist)
        self.dao.remove_book(id_playlist, id_book)
