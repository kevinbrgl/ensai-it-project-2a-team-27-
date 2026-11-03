"""Pydantic models for playlist entities."""

from pydantic import BaseModel, Field


class PlaylistCreate(BaseModel):
    """Data sent by the client to create a playlist."""

    name: str = Field(min_length=1, max_length=100)


class PlaylistRead(BaseModel):
    """Playlist data returned by the API."""

    id_playlist: int
    id_user: int
    name: str


class PlaylistUpdate(PlaylistCreate):
    """Body of PATCH /playlists/{id_playlist}."""
