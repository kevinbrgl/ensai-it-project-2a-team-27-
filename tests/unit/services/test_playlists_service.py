"""Unit tests for PlaylistService.

The PlaylistDAO is replaced by a mock: no database is needed.
"""

from unittest.mock import Mock

import pytest
from pytest_mock import MockerFixture

from src.dao.playlists_dao import PlaylistDAO
from src.models.books import Book
from src.models.playlists import (
    PlaylistBookAdd,
    PlaylistBookRead,
    PlaylistCreate,
    PlaylistDetails,
    PlaylistRead,
    PlaylistUpdate,
)
from src.services.playlists_service import PlaylistService
from src.utils.exceptions import (
    BookAlreadyInPlaylistError,
    BookNotInPlaylistError,
    PlaylistAlreadyExistsError,
    PlaylistNotFoundError,
)

ID_USER = 1
ID_PLAYLIST = 10
ID_BOOK = 100
NAME = "Polars"


@pytest.fixture
def mock_dao(mocker: MockerFixture) -> Mock:
    """Return a fake PlaylistDAO with the same methods as the real one."""
    return mocker.Mock(spec=PlaylistDAO)


@pytest.fixture
def service(mock_dao: Mock) -> PlaylistService:
    """Return a PlaylistService using the mocked DAO."""
    return PlaylistService(mock_dao)


@pytest.fixture
def playlist_in() -> PlaylistCreate:
    """Return a valid request payload."""
    return PlaylistCreate(name=NAME)


@pytest.fixture
def playlist() -> PlaylistRead:
    """Return a playlist as returned by the DAO."""
    return PlaylistRead(id_playlist=ID_PLAYLIST, id_user=ID_USER, name=NAME)


@pytest.fixture
def book() -> Book:
    """Return a book as returned by the DAO."""
    return Book(
        id_book=ID_BOOK,
        id_book_api="/works/OL1W",
        title="Dune",
        author="Frank Herbert",
        category=None,
        publish_date=None,
        description=None,
        cover_image=None,
    )


class TestCreatePlaylist:
    """Tests for PlaylistService.create_playlist."""

    def test_valid(
        self,
        service: PlaylistService,
        mock_dao: Mock,
        playlist_in: PlaylistCreate,
    ) -> None:
        """Valid request: returns the playlist created by the DAO."""
        created = PlaylistRead(
            id_playlist=ID_PLAYLIST,
            id_user=ID_USER,
            name=NAME,
        )
        mock_dao.create.return_value = created

        result = service.create_playlist(ID_USER, playlist_in)

        assert result == created
        mock_dao.create.assert_called_once_with(ID_USER, playlist_in)

    def test_duplicate_name(
        self,
        service: PlaylistService,
        mock_dao: Mock,
        playlist_in: PlaylistCreate,
    ) -> None:
        """DAO raises PlaylistAlreadyExistsError: it is propagated."""
        mock_dao.create.side_effect = PlaylistAlreadyExistsError(NAME)

        with pytest.raises(PlaylistAlreadyExistsError):
            service.create_playlist(ID_USER, playlist_in)

        mock_dao.create.assert_called_once_with(ID_USER, playlist_in)


class TestListPlaylists:
    """Tests for PlaylistService.list_playlists."""

    def test_valid(
        self,
        service: PlaylistService,
        mock_dao: Mock,
    ) -> None:
        """The playlists returned by the DAO are returned as they are."""
        playlist = PlaylistRead(
            id_playlist=ID_PLAYLIST,
            id_user=ID_USER,
            name=NAME,
        )
        mock_dao.find_by_user_id.return_value = [playlist]

        result = service.list_playlists(ID_USER)

        assert result == [playlist]
        mock_dao.find_by_user_id.assert_called_once_with(ID_USER)

    def test_no_playlists(
        self,
        service: PlaylistService,
        mock_dao: Mock,
    ) -> None:
        """No playlists: returns an empty list, without error."""
        mock_dao.find_by_user_id.return_value = []

        assert service.list_playlists(ID_USER) == []
        mock_dao.find_by_user_id.assert_called_once_with(ID_USER)


class TestRenamePlaylist:
    """Tests for PlaylistService.rename_playlist."""

    def test_valid(
        self,
        service: PlaylistService,
        mock_dao: Mock,
    ) -> None:
        """Valid request: returns the playlist renamed by the DAO."""
        playlist_in = PlaylistUpdate(name="Thrillers")
        renamed = PlaylistRead(
            id_playlist=ID_PLAYLIST,
            id_user=ID_USER,
            name="Thrillers",
        )
        mock_dao.rename.return_value = renamed

        result = service.rename_playlist(ID_USER, ID_PLAYLIST, playlist_in)

        assert result == renamed
        mock_dao.rename.assert_called_once_with(
            ID_USER,
            ID_PLAYLIST,
            playlist_in,
        )

    def test_not_found(
        self,
        service: PlaylistService,
        mock_dao: Mock,
    ) -> None:
        """DAO raises PlaylistNotFoundError: it is propagated."""
        mock_dao.rename.side_effect = PlaylistNotFoundError(ID_PLAYLIST)

        with pytest.raises(PlaylistNotFoundError):
            service.rename_playlist(
                ID_USER,
                ID_PLAYLIST,
                PlaylistUpdate(name="Thrillers"),
            )


class TestDeletePlaylist:
    """Tests for PlaylistService.delete_playlist."""

    def test_valid(
        self,
        service: PlaylistService,
        mock_dao: Mock,
    ) -> None:
        """Valid request: the DAO is asked to delete the playlist."""
        service.delete_playlist(ID_USER, ID_PLAYLIST)

        mock_dao.delete.assert_called_once_with(ID_USER, ID_PLAYLIST)

    def test_not_found(
        self,
        service: PlaylistService,
        mock_dao: Mock,
    ) -> None:
        """DAO raises PlaylistNotFoundError: it is propagated."""
        mock_dao.delete.side_effect = PlaylistNotFoundError(ID_PLAYLIST)

        with pytest.raises(PlaylistNotFoundError):
            service.delete_playlist(ID_USER, ID_PLAYLIST)


class TestAddBookToPlaylist:
    """Tests for PlaylistService.add_book_to_playlist."""

    def test_valid(
        self,
        service: PlaylistService,
        mock_dao: Mock,
        playlist: PlaylistRead,
    ) -> None:
        """Own playlist: the book is added by the DAO."""
        entry = PlaylistBookRead(id_playlist=ID_PLAYLIST, id_book=ID_BOOK)
        mock_dao.read.return_value = playlist
        mock_dao.add_book.return_value = entry

        result = service.add_book_to_playlist(
            ID_USER,
            ID_PLAYLIST,
            PlaylistBookAdd(id_book=ID_BOOK),
        )

        assert result == entry
        mock_dao.read.assert_called_once_with(ID_USER, ID_PLAYLIST)
        mock_dao.add_book.assert_called_once_with(ID_PLAYLIST, ID_BOOK)

    def test_playlist_not_found(
        self,
        service: PlaylistService,
        mock_dao: Mock,
    ) -> None:
        """Playlist not found or not mine: error, and nothing is added."""
        mock_dao.read.return_value = None

        with pytest.raises(PlaylistNotFoundError):
            service.add_book_to_playlist(
                ID_USER,
                ID_PLAYLIST,
                PlaylistBookAdd(id_book=ID_BOOK),
            )

        mock_dao.add_book.assert_not_called()

    def test_book_already_in_playlist(
        self,
        service: PlaylistService,
        mock_dao: Mock,
        playlist: PlaylistRead,
    ) -> None:
        """DAO raises BookAlreadyInPlaylistError: it is propagated."""
        mock_dao.read.return_value = playlist
        mock_dao.add_book.side_effect = BookAlreadyInPlaylistError(ID_BOOK)

        with pytest.raises(BookAlreadyInPlaylistError):
            service.add_book_to_playlist(
                ID_USER,
                ID_PLAYLIST,
                PlaylistBookAdd(id_book=ID_BOOK),
            )


class TestGetPlaylist:
    """Tests for PlaylistService.get_playlist."""

    def test_valid(
        self,
        service: PlaylistService,
        mock_dao: Mock,
        playlist: PlaylistRead,
        book: Book,
    ) -> None:
        """Own playlist: returned with its books."""
        mock_dao.read.return_value = playlist
        mock_dao.find_books.return_value = [book]

        result = service.get_playlist(ID_USER, ID_PLAYLIST)

        assert result == PlaylistDetails(
            id_playlist=ID_PLAYLIST,
            id_user=ID_USER,
            name=NAME,
            books=[book],
        )
        mock_dao.find_books.assert_called_once_with(ID_PLAYLIST)

    def test_not_found(
        self,
        service: PlaylistService,
        mock_dao: Mock,
    ) -> None:
        """Playlist not found or not mine: error, books are not read."""
        mock_dao.read.return_value = None

        with pytest.raises(PlaylistNotFoundError):
            service.get_playlist(ID_USER, ID_PLAYLIST)

        mock_dao.find_books.assert_not_called()


class TestRemoveBookFromPlaylist:
    """Tests for PlaylistService.remove_book_from_playlist."""

    def test_valid(
        self,
        service: PlaylistService,
        mock_dao: Mock,
        playlist: PlaylistRead,
    ) -> None:
        """Own playlist: the DAO is asked to remove the book."""
        mock_dao.read.return_value = playlist

        service.remove_book_from_playlist(ID_USER, ID_PLAYLIST, ID_BOOK)

        mock_dao.remove_book.assert_called_once_with(ID_PLAYLIST, ID_BOOK)

    def test_playlist_not_found(
        self,
        service: PlaylistService,
        mock_dao: Mock,
    ) -> None:
        """Playlist not found or not mine: error, nothing is removed."""
        mock_dao.read.return_value = None

        with pytest.raises(PlaylistNotFoundError):
            service.remove_book_from_playlist(ID_USER, ID_PLAYLIST, ID_BOOK)

        mock_dao.remove_book.assert_not_called()

    def test_book_not_in_playlist(
        self,
        service: PlaylistService,
        mock_dao: Mock,
        playlist: PlaylistRead,
    ) -> None:
        """DAO raises BookNotInPlaylistError: it is propagated."""
        mock_dao.read.return_value = playlist
        mock_dao.remove_book.side_effect = BookNotInPlaylistError(ID_BOOK)

        with pytest.raises(BookNotInPlaylistError):
            service.remove_book_from_playlist(ID_USER, ID_PLAYLIST, ID_BOOK)
