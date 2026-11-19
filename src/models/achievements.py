"""Pydantic models for achievements and milestone entities.

Defines trophies, categories, tiers, and user milestone metrics.
"""

from enum import StrEnum

from pydantic import BaseModel, Field


class AchievementTier(StrEnum):
    """Trophy tiers representing achievement rarity and prestige."""

    BRONZE = "BRONZE"
    SILVER = "SILVER"
    GOLD = "GOLD"
    PLATINUM = "PLATINUM"


class AchievementCategory(StrEnum):
    """Categories of achievements available in Ex-Libris."""

    READING = "READING"
    EXPLORATION = "EXPLORATION"
    COMMUNITY = "COMMUNITY"
    SOCIAL = "SOCIAL"
    COLLECTION = "COLLECTION"


class AchievementUserStats(BaseModel):
    """Aggregated user metrics used to evaluate achievement unlocks."""

    completed_books: int = Field(
        ge=0,
        description="Number of finished books",
    )
    pages_read: int = Field(
        ge=0,
        description="Total number of pages read from completed books",
    )
    distinct_genres: int = Field(
        ge=0,
        description="Distinct categories of books read",
    )
    reviews_count: int = Field(
        ge=0,
        description="Number of published book reviews",
    )
    favorites_count: int = Field(
        ge=0,
        description="Number of books marked as favorite",
    )
    following_count: int = Field(
        ge=0,
        description="Number of users being followed",
    )
    followers_count: int = Field(
        ge=0,
        description="Number of followers following this user",
    )
    playlists_count: int = Field(
        ge=0,
        description="Number of created playlists",
    )
    library_size: int = Field(
        default=0,
        ge=0,
        description="Number of books in the library, whatever their state",
    )
    want_to_read_books: int = Field(
        default=0,
        ge=0,
        description="Number of books on the want-to-read list",
    )
    reading_books: int = Field(
        default=0,
        ge=0,
        description="Number of books currently being read",
    )
    abandoned_books: int = Field(
        default=0,
        ge=0,
        description="Number of books set aside before the end",
    )
    distinct_authors: int = Field(
        default=0,
        ge=0,
        description="Distinct authors of finished books",
    )
    longest_book_pages: int = Field(
        default=0,
        ge=0,
        description="Page count of the longest finished book",
    )
    classics_read: int = Field(
        default=0,
        ge=0,
        description="Finished books first published before 1950",
    )
    dated_books: int = Field(
        default=0,
        ge=0,
        description="Finished books with a recorded finish date",
    )
    detailed_reviews: int = Field(
        default=0,
        ge=0,
        description="Reviews whose comment is at least 200 characters long",
    )
    five_star_reviews: int = Field(
        default=0,
        ge=0,
        description="Reviews with a 5-star rating",
    )
    liked_books: int = Field(
        default=0,
        ge=0,
        description="Number of liked books",
    )
    largest_playlist: int = Field(
        default=0,
        ge=0,
        description="Number of books in the user's largest playlist",
    )
    mutual_follows: int = Field(
        default=0,
        ge=0,
        description="Followed users who follow the user back",
    )
    profile_fields: int = Field(
        default=0,
        ge=0,
        le=2,
        description="Profile fields filled in among bio and picture (0 to 2)",
    )


class Achievement(BaseModel):
    """Schema representing an achievement and its unlock status."""

    id_achievement: str = Field(
        ...,
        description="Unique slug identifier of the achievement",
    )
    title: str = Field(
        ...,
        description="Human-readable title of the achievement",
    )
    description: str = Field(
        ...,
        description="Detailed requirement to unlock this milestone",
    )
    category: AchievementCategory = Field(
        ...,
        description="Category of the achievement",
    )
    tier: AchievementTier = Field(
        ...,
        description="Trophy tier (BRONZE, SILVER, GOLD, PLATINUM)",
    )
    icon: str = Field(
        ...,
        description="Visual badge icon or emoji",
    )
    is_unlocked: bool = Field(
        ...,
        description="Whether the user has achieved this milestone",
    )
    progress: int = Field(
        ge=0,
        description="Current user progress capped at target",
    )
    target: int = Field(
        gt=0,
        description="Target value required to unlock the achievement",
    )
    progress_percentage: float = Field(
        ge=0.0,
        le=100.0,
        description="Completion percentage between 0.0 and 100.0",
    )
