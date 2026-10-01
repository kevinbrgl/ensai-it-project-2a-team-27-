"""Pydantic models for item entities.

Defines schemas for item creation, registration, update, and db representation.
"""

from pydantic import BaseModel


class ItemBase(BaseModel):
    """Base schema for item attributes."""

    name: str
    description: str | None = None


class ItemRegister(ItemBase):
    """Schema for registering a new item."""


class ItemCreate(ItemRegister):
    """Schema for creating an item in the database."""

    user_id: int


class ItemUpdate(BaseModel):
    """Schema for updating item attributes."""

    name: str | None = None
    description: str | None = None


class Item(ItemCreate):
    """Schema for an item as stored in the database."""

    id: int
