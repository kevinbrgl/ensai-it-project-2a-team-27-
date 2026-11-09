"""Pydantic models for book recommendations."""

from typing import Literal

from pydantic import BaseModel, Field

from src.models.books import Book

RecommendationSort = Literal["rating", "new", "title"]


class Recommendation(BaseModel):
    """A book recommended to a user, returned by GET /recommendations."""

    book: Book
    score: float | None = Field(default=None, ge=0, le=5)
    reason: str
