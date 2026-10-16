"""Pydantic models for library and reading activity entities."""

from pydantic import BaseModel, Field


class LibraryBookAdd(BaseModel):
    """Body of POST /library/books."""

    id_book: int
    state: str = Field(pattern="^(READING|WANT_TO_READ|COMPLETED)$")


class LibraryBookRead(BaseModel):
    """Library activity data returned by the API."""

    id_user: int
    id_book: int
    state: str
    is_liked: bool
    is_favorite: bool
