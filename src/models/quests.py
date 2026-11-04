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
