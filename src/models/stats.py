"""Pydantic models for reading statistics."""

from pydantic import BaseModel


class GenreCount(BaseModel):
    """Number of books of one category in a user's library."""

    category: str | None
    count: int


class RatingCount(BaseModel):
    """Number of reviews with one rating."""

    rating: int
    count: int


class UserStats(BaseModel):
    """Reading statistics of a user, returned by GET /users/me/stats."""

    books_finished: int
    genres: list[GenreCount]
    ratings: list[RatingCount]
