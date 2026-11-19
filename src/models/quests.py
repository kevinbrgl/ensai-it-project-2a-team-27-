"""Pydantic models for quests and gamification entities.

Defines categories, user quest progress, and aggregated metrics.
"""

from enum import StrEnum

from pydantic import BaseModel, Field


class QuestCategory(StrEnum):
    """Categories of quests available in Ex-Libris."""

    READING = "READING"
    EXPLORATION = "EXPLORATION"
    SOCIAL = "SOCIAL"
    ENGAGEMENT = "ENGAGEMENT"


class QuestUserStats(BaseModel):
    """Aggregated user metrics used to evaluate quest progress."""

    completed_books: int = Field(
        ge=0,
        description="Number of finished books",
    )
    reading_books: int = Field(
        ge=0,
        description="Number of books currently reading",
    )
    distinct_categories: int = Field(
        ge=0,
        description="Distinct categories of books in library",
    )
    following_count: int = Field(
        ge=0,
        description="Number of users being followed",
    )
    favorite_books: int = Field(
        ge=0,
        description="Number of favorite books",
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
    pages_read: int = Field(
        default=0,
        ge=0,
        description="Total number of pages of finished books",
    )
    distinct_authors: int = Field(
        default=0,
        ge=0,
        description="Distinct authors of finished books",
    )
    dated_books: int = Field(
        default=0,
        ge=0,
        description="Finished books with a recorded finish date",
    )
    liked_books: int = Field(
        default=0,
        ge=0,
        description="Number of liked books",
    )
    reviews_count: int = Field(
        default=0,
        ge=0,
        description="Number of published reviews",
    )
    playlists_count: int = Field(
        default=0,
        ge=0,
        description="Number of created playlists",
    )
    playlist_books: int = Field(
        default=0,
        ge=0,
        description="Books placed in playlists, counted once per playlist",
    )
    followers_count: int = Field(
        default=0,
        ge=0,
        description="Number of users following this user",
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


class Quest(BaseModel):
    """Schema representing a quest and its progress for a user."""

    id_quest: str = Field(
        ...,
        description="Unique slug identifier of the quest",
    )
    title: str = Field(..., description="Human-readable title of the quest")
    description: str = Field(
        ...,
        description="Detailed explanation of the quest goal",
    )
    category: QuestCategory = Field(
        ...,
        description="Category of the quest",
    )
    current: int = Field(ge=0, description="Current progress value")
    target: int = Field(
        gt=0,
        description="Target value required to complete the quest",
    )
    progress_percentage: float = Field(
        ge=0.0,
        le=100.0,
        description="Completion percentage between 0 and 100",
    )
    is_completed: bool = Field(
        description="Whether the quest is fully completed",
    )
    reward_xp: int = Field(
        ge=0,
        description="Experience points rewarded upon completion",
    )
