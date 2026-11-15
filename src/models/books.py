"""Pydantic models for book entities.

Defines schemas for book creation, reading, database representation,
and the editions fetched from Open Library.
"""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class BookBase(BaseModel):
    """Attributes shared by book schemas."""

    title: str = Field(min_length=1, max_length=255)
    author: str | None = Field(default=None, max_length=255)
    category: str | None = Field(default=None, max_length=100)
    publish_date: date | None = None
    description: str | None = None
    cover_image: str | None = None
    id_book_api: str | None = Field(default=None, max_length=100)
    num_pages: int | None = None


class BookCreate(BookBase):
    """Schema for inserting a book into the database."""


class BookRead(BookBase):
    """Schema returned by the API for a book."""

    id_book: int | None = None


class Book(BookRead):
    """Book model representing a full database row."""

    model_config = ConfigDict(from_attributes=True)
    id_book: int


class Edition(BaseModel):
    """One edition of a book, fetched live from Open Library."""

    title: str | None = None
    publishers: list[str] = Field(default_factory=list)
    publish_date: str | None = None
    num_pages: int | None = None
    isbn: str | None = None
    language: str | None = None


class BookDetails(Book):
    """A book with its editions, returned by GET /books/{book_id}."""

    editions: list[Edition] = Field(default_factory=list)
