"""Pydantic models for user entities.

Defines schemas for user creation, registration, update, password change,
and database representation.
"""

from pydantic import BaseModel


class UserBase(BaseModel):
    """Base schema for user attributes."""

    username: str
    first_name: str | None = None
    last_name: str | None = None


class UserRegister(UserBase):
    """Schema for registering a new user."""

    password: str


class UserRead(UserBase):
    """Schema for reading user data."""

    id: int


class UserCreate(UserBase):
    """Schema for creating a user in the database."""

    hashed_password: str


class UserUpdate(BaseModel):
    """Schema for updating user attributes."""

    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None


class UserUpdateFull(UserUpdate):
    """Schema for a full user update, including password."""

    hashed_password: str | None = None


class UserUpdatePassword(BaseModel):
    """Schema for updating a user's password."""

    current_password: str
    new_password: str


class User(UserCreate, UserRead):
    """Schema for a user as stored in the database."""
