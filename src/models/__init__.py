"""Re-export the most used Pydantic models from one place.

Other models, such as those for playlists, statistics or moderation, are
imported from their own module.
"""

from src.models.achievements import (
    Achievement,
    AchievementCategory,
    AchievementTier,
    AchievementUserStats,
)
from src.models.books import Book, BookCreate, BookRead
from src.models.genre_wheel import GenreWheel, GenreWheelSegment
from src.models.library import LibraryBookAdd, LibraryBookRead
from src.models.misc import Token, TokenPayload
from src.models.quests import Quest, QuestCategory, QuestUserStats
from src.models.reviews import (
    BookReviews,
    ReviewCreate,
    ReviewRead,
    ReviewUpdate,
)
from src.models.users import (
    User,
    UserCreate,
    UserRead,
    UserRegister,
    UserUpdate,
    UserUpdateFull,
    UserUpdatePassword,
)

__all__ = [
    "Achievement",
    "AchievementCategory",
    "AchievementTier",
    "AchievementUserStats",
    "Book",
    "BookCreate",
    "BookRead",
    "GenreWheel",
    "GenreWheelSegment",
    "LibraryBookAdd",
    "LibraryBookRead",
    "Quest",
    "QuestCategory",
    "QuestUserStats",
    "Token",
    "TokenPayload",
    "User",
    "UserCreate",
    "UserRead",
    "UserRegister",
    "UserUpdate",
    "UserUpdateFull",
    "UserUpdatePassword",
]
