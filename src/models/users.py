"""Pydantic models for user entities.

Defines schemas for user registration, reading, creation, update,
password change, and database representation.
"""

from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    """Attributes shared by all user schemas."""

    username: str = Field(min_length=3, max_length=30)
    email: EmailStr


class UserRegister(UserBase):
    """Body of POST /auth/register."""

    password: str = Field(min_length=8, max_length=72)


class UserRead(UserBase):
    """User data returned by the API (never the password)."""

    id_user: int
    bio: str | None = None
    profile_picture: str | None = None


class UserCreate(UserBase):
    """Data needed to insert a user in the database."""

    password_hash: str


class UserUpdate(BaseModel):
    """Body of PATCH /users/me (all fields optional)."""

    username: str | None = Field(default=None, min_length=3, max_length=30)
    email: EmailStr | None = None
    bio: str | None = None
    profile_picture: str | None = None


class UserUpdateFull(UserUpdate):
    """Full user update, including the password hash."""

    password_hash: str | None = None


class UserUpdatePassword(BaseModel):
    """Body of PUT /users/me/password."""

    current_password: str
    new_password: str = Field(min_length=8, max_length=72)


class User(UserCreate, UserRead):
    """User as stored in the database (includes password_hash)."""
