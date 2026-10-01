"""Miscellaneous Pydantic models.

Includes schemas for authentication tokens and payloads.
"""

from pydantic import BaseModel


class Token(BaseModel):
    """Schema for an authentication token."""

    access_token: str
    token_type: str


class TokenPayload(BaseModel):
    """Schema for the payload of an authentication token."""

    sub: str | None = None
