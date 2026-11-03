"""Integration tests for PlaylistDAO, run against the real database.

Each test is rolled back (see tests/integration/conftest.py),
so the database is left unchanged.
"""

from uuid import uuid4

import pytest
from psycopg2.extras import RealDictCursor

from src.dao.playlists_dao import PlaylistDAO
from src.dao.users_dao import UserDAO
from src.models.playlists import PlaylistCreate, PlaylistUpdate
from src.models.users import UserCreate
from src.utils.exceptions import (
    PlaylistAlreadyExistsError,
    PlaylistNotFoundError,
)


def create_user(user_dao: UserDAO, prefix: str) -> int:
    """Insert a test user with a unique name and return its ID.

    :param user_dao: DAO used to insert the user
    :param prefix: Beginning of the username
    :return: ID of the created user
    """
    name = f"{prefix}_{uuid4().hex[:8]}"
    user = user_dao.create(
        UserCreate(
            username=name,
            email=f"{name}@ensai.fr",
            password_hash="fakehash",
        ),
    )
    return user.id_user


@pytest.fixture
def playlist_dao(cursor: RealDictCursor) -> PlaylistDAO:
    """Return a PlaylistDAO bound to the test cursor."""
    return PlaylistDAO(cursor)


@pytest.fixture
def id_user(user_dao: UserDAO) -> int:
    """Insert a test user in the database and return its ID."""
    return create_user(user_dao, "playlister")


@pytest.fixture
def id_other_user(user_dao: UserDAO) -> int:
    """Insert a second test user in the database and return its ID."""
    return create_user(user_dao, "other")


@pytest.fixture
def id_playlist(playlist_dao: PlaylistDAO, id_user: int) -> int:
    """Create a playlist named "Polars" for the test user, return its ID."""
    playlist = playlist_dao.create(id_user, PlaylistCreate(name="Polars"))
    return playlist.id_playlist


class TestCreate:
    """Tests for PlaylistDAO.create."""

    def test_ok(self, playlist_dao: PlaylistDAO, id_user: int) -> None:
        """The playlist is created for the user, with a new ID."""
        result = playlist_dao.create(id_user, PlaylistCreate(name="Polars"))

        assert result.id_playlist > 0
        assert result.id_user == id_user
        assert result.name == "Polars"

    def test_saved_in_database(
        self,
        playlist_dao: PlaylistDAO,
        cursor: RealDictCursor,
        id_user: int,
    ) -> None:
        """The playlist is really stored in the playlists table."""
        created = playlist_dao.create(id_user, PlaylistCreate(name="Polars"))

        cursor.execute(
            "SELECT id_user, name FROM playlists WHERE id_playlist = %s",
            (created.id_playlist,),
        )
        row = cursor.fetchone()

        assert row is not None
        assert row["id_user"] == id_user
        assert row["name"] == "Polars"

    def test_two_playlists(
        self,
        playlist_dao: PlaylistDAO,
        id_user: int,
    ) -> None:
        """Two playlists with different names get different IDs."""
        first = playlist_dao.create(id_user, PlaylistCreate(name="Polars"))
        second = playlist_dao.create(id_user, PlaylistCreate(name="Romans"))

        assert first.id_playlist != second.id_playlist

    def test_duplicate_name(
        self,
        playlist_dao: PlaylistDAO,
        id_user: int,
    ) -> None:
        """Same name twice for the same user raises an error."""
        playlist_dao.create(id_user, PlaylistCreate(name="Polars"))

        with pytest.raises(PlaylistAlreadyExistsError):
            playlist_dao.create(id_user, PlaylistCreate(name="Polars"))

    def test_same_name_other_user(
        self,
        playlist_dao: PlaylistDAO,
        id_user: int,
        id_other_user: int,
    ) -> None:
        """Two different users can each have a playlist with the same name."""
        mine = playlist_dao.create(id_user, PlaylistCreate(name="Polars"))
        theirs = playlist_dao.create(
            id_other_user,
            PlaylistCreate(name="Polars"),
        )

        assert mine.id_user == id_user
        assert theirs.id_user == id_other_user


class TestFindByUserId:
    """Tests for PlaylistDAO.find_by_user_id."""

    def test_no_playlists(
        self,
        playlist_dao: PlaylistDAO,
        id_user: int,
    ) -> None:
        """A user without playlists gets an empty list."""
        assert playlist_dao.find_by_user_id(id_user) == []

    def test_in_creation_order(
        self,
        playlist_dao: PlaylistDAO,
        id_user: int,
    ) -> None:
        """All the user's playlists are listed, in creation order."""
        first = playlist_dao.create(id_user, PlaylistCreate(name="Romans"))
        second = playlist_dao.create(id_user, PlaylistCreate(name="Polars"))

        result = playlist_dao.find_by_user_id(id_user)

        assert [p.id_playlist for p in result] == [
            first.id_playlist,
            second.id_playlist,
        ]

    def test_other_user_not_listed(
        self,
        playlist_dao: PlaylistDAO,
        id_user: int,
        id_other_user: int,
    ) -> None:
        """The playlists of another user are never listed."""
        playlist_dao.create(id_other_user, PlaylistCreate(name="Polars"))

        assert playlist_dao.find_by_user_id(id_user) == []
        assert len(playlist_dao.find_by_user_id(id_other_user)) == 1


class TestRename:
    """Tests for PlaylistDAO.rename."""

    def test_ok(
        self,
        playlist_dao: PlaylistDAO,
        id_user: int,
        id_playlist: int,
    ) -> None:
        """The playlist gets its new name and keeps its ID."""
        result = playlist_dao.rename(
            id_user,
            id_playlist,
            PlaylistUpdate(name="Thrillers"),
        )

        assert result.id_playlist == id_playlist
        assert result.name == "Thrillers"
        assert [p.name for p in playlist_dao.find_by_user_id(id_user)] == [
            "Thrillers",
        ]

    def test_not_found(self, playlist_dao: PlaylistDAO, id_user: int) -> None:
        """Unknown playlist: PlaylistNotFoundError."""
        with pytest.raises(PlaylistNotFoundError):
            playlist_dao.rename(id_user, 999999999, PlaylistUpdate(name="X"))

    def test_other_user_cannot_rename(
        self,
        playlist_dao: PlaylistDAO,
        id_user: int,
        id_other_user: int,
        id_playlist: int,
    ) -> None:
        """Another user's playlist is treated as not found and unchanged."""
        with pytest.raises(PlaylistNotFoundError):
            playlist_dao.rename(
                id_other_user,
                id_playlist,
                PlaylistUpdate(name="Pirate"),
            )

        assert [p.name for p in playlist_dao.find_by_user_id(id_user)] == [
            "Polars",
        ]

    def test_name_already_used(
        self,
        playlist_dao: PlaylistDAO,
        id_user: int,
        id_playlist: int,
    ) -> None:
        """New name already used by another of my playlists: error."""
        playlist_dao.create(id_user, PlaylistCreate(name="Romans"))

        with pytest.raises(PlaylistAlreadyExistsError):
            playlist_dao.rename(
                id_user,
                id_playlist,
                PlaylistUpdate(name="Romans"),
            )


class TestDelete:
    """Tests for PlaylistDAO.delete."""

    def test_ok(
        self,
        playlist_dao: PlaylistDAO,
        id_user: int,
        id_playlist: int,
    ) -> None:
        """The playlist no longer exists after deletion."""
        playlist_dao.delete(id_user, id_playlist)

        assert playlist_dao.find_by_user_id(id_user) == []

    def test_not_found(self, playlist_dao: PlaylistDAO, id_user: int) -> None:
        """Unknown playlist: PlaylistNotFoundError."""
        with pytest.raises(PlaylistNotFoundError):
            playlist_dao.delete(id_user, 999999999)

    def test_delete_twice(
        self,
        playlist_dao: PlaylistDAO,
        id_user: int,
        id_playlist: int,
    ) -> None:
        """Deleting the same playlist twice: the second time is an error."""
        playlist_dao.delete(id_user, id_playlist)

        with pytest.raises(PlaylistNotFoundError):
            playlist_dao.delete(id_user, id_playlist)

    def test_other_user_cannot_delete(
        self,
        playlist_dao: PlaylistDAO,
        id_user: int,
        id_other_user: int,
        id_playlist: int,
    ) -> None:
        """Another user's playlist is treated as not found and kept."""
        with pytest.raises(PlaylistNotFoundError):
            playlist_dao.delete(id_other_user, id_playlist)

        assert len(playlist_dao.find_by_user_id(id_user)) == 1
