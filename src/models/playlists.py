"""Pydantic models for playlist entities."""

from pydantic import BaseModel, Field

from src.models.books import Book


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


class PlaylistBookAdd(BaseModel):
    """Body of POST /playlists/{id_playlist}/books."""

    id_book: int


class PlaylistBookRead(BaseModel):
    """A book of a playlist, as returned by the API."""

    id_playlist: int
    id_book: int


class PlaylistDetails(PlaylistRead):
    """A playlist with the details of its books."""

    books: list[Book]
