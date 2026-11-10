"""Pydantic models for the admin moderation routes."""

from datetime import datetime

from pydantic import BaseModel, Field


class SuspendRequest(BaseModel):
    """Body of POST /admin/users/{user_id}/suspend."""

    days: int = Field(
        ge=1,
        le=365,
        description="Length of the suspension, in days (1-365)",
    )


class ModerationStatus(BaseModel):
    """Moderation state of a user, returned after a suspend or a ban."""

    id_user: int
    username: str
    is_banned: bool
    suspended_until: datetime | None = None
