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
