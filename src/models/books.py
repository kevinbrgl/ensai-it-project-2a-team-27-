"""Pydantic models for book entities.

Defines schemas for book creation, reading, and database representation.
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


class BookCreate(BookBase):
    """Schema for inserting a book into the database."""


class BookRead(BookBase):
    """Schema returned by the API for a book."""

    id_book: int | None = None


class Book(BookRead):
    """Book model representing a full database row."""

    model_config = ConfigDict(from_attributes=True)
    id_book: int
