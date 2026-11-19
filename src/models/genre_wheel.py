"""Pydantic models for the user profile genre color wheel.

Defines the segments, colors, proportions, and aggregated data
used to render the interactive color wheel around user avatars.
"""

from pydantic import BaseModel, Field


class GenreWheelSegment(BaseModel):
    """Single genre segment within the avatar color wheel."""

    genre: str = Field(
        ...,
        description="Name of the book genre or category",
    )
    color: str = Field(
        ...,
        description="Hex color code associated with the genre (e.g. #F43F5E)",
    )
    percentage: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Proportion of the wheel occupied by this genre (0-100)",
    )
    book_count: int = Field(
        ...,
        ge=1,
        description="Number of completed books read in this genre",
    )
    average_rating: float | None = Field(
        None,
        ge=1.0,
        le=5.0,
        description="Average rating given by the user to books in this genre",
    )
    raw_score: float = Field(
        ...,
        ge=0.0,
        description="Weighted score based on volume, ratings, and favorites",
    )


class GenreWheel(BaseModel):
    """User profile avatar genre color wheel representation."""

    id_user: int = Field(
        ...,
        description="ID of the user whose wheel is displayed",
    )
    is_empty: bool = Field(
        ...,
        description="Whether the user has no completed books or valid genres",
    )
    empty_color: str = Field(
        default="#9CA3AF",
        description="Fallback hex color used when the wheel is empty (grey)",
    )
    total_books: int = Field(
        ...,
        ge=0,
        description="Total completed books counted in the wheel",
    )
    segments: list[GenreWheelSegment] = Field(
        default_factory=list,
        description="Ordered list of genre segments sorted by share",
    )
