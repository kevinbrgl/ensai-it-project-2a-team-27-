"""Pydantic models for review entities."""

from datetime import datetime

from pydantic import BaseModel, Field


class ReviewCreate(BaseModel):
    """Body of POST /books/{book_id}/reviews."""

    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=2000)


class ReviewUpdate(BaseModel):
    """Body of PUT /reviews/{review_id}."""

    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=2000)


class ReviewRead(BaseModel):
    """Review data returned by the API."""

    id_review: int
    id_user: int
    id_book: int
    rating: int
    comment: str | None = None
    created_at: datetime


class BookReviews(BaseModel):
    """Reviews of a book, with its average rating."""

    id_book: int
    average_rating: float | None = None
    review_count: int
    reviews: list[ReviewRead]
