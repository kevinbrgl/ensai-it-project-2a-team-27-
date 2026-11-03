"""Unit tests for PlaylistService.

The PlaylistDAO is replaced by a mock: no database is needed.
"""

from unittest.mock import Mock

import pytest
from pytest_mock import MockerFixture

from src.dao.playlists_dao import PlaylistDAO
from src.models.playlists import PlaylistCreate, PlaylistRead, PlaylistUpdate
from src.services.playlists_service import PlaylistService
from src.utils.exceptions import (
    PlaylistAlreadyExistsError,
    PlaylistNotFoundError,
)

ID_USER = 1
ID_PLAYLIST = 10
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
