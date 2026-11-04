"""Import all Pydantic models for books, library, quests, users, and tokens.

This module aggregates all model classes for easy access throughout the app.
"""

from src.models.books import Book, BookCreate, BookRead
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
    UserFollow,
    UserRead,
    UserRegister,
    UserUpdate,
    UserUpdateFull,
    UserUpdatePassword,
)

__all__ = [
    "Book",
    "BookCreate",
    "BookRead",
    "LibraryBookAdd",
    "LibraryBookRead",
    "Quest",
    "QuestCategory",
    "QuestUserStats",
    "Token",
    "TokenPayload",
    "User",
    "UserCreate",
    "UserFollow",
    "UserRead",
    "UserRegister",
    "UserUpdate",
    "UserUpdateFull",
    "UserUpdatePassword",
]
