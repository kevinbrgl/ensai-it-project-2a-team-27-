"""Service layer for playlist operations."""

from src.dao.playlists_dao import PlaylistDAO
from src.models.playlists import PlaylistCreate, PlaylistRead, PlaylistUpdate


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
