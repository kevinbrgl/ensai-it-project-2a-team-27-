"""Pydantic models for user entities.

Defines schemas for user registration, reading, creation, update,
password change, settings, database representation, and user follows.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

Theme = Literal["day", "night"]
ProfileVisibility = Literal["public", "private"]

# bcrypt only uses the first 72 bytes of a password, so a longer password
# would be silently truncated. Accented letters and emoji take several
# bytes, so the character limit alone is not enough.
PASSWORD_MAX_BYTES = 72


def _check_password_bytes(password: str) -> str:
    """Reject a password that bcrypt would truncate.

    Parameters
    ----------
    password : str
        Plain-text password to check.

    Returns
    -------
    str
        The unchanged password.

    Raises
    ------
    ValueError
        If the password is longer than 72 bytes once encoded in UTF-8.

    """
    if len(password.encode("utf-8")) > PASSWORD_MAX_BYTES:
        msg = (
            "Password is too long: at most 72 bytes "
            "(accented letters and emoji count as several)."
        )
        raise ValueError(msg)
    return password


class UserBase(BaseModel):
    """Attributes shared by all user schemas."""

    username: str = Field(min_length=3, max_length=30)
    email: EmailStr = Field(max_length=100)


class UserRegister(UserBase):
    """Body of POST /auth/register."""

    password: str = Field(min_length=8, max_length=72)

    _password_bytes = field_validator("password")(_check_password_bytes)


class UserRead(UserBase):
    """User data returned by the API (never the password)."""

    id_user: int
    bio: str | None = None
    profile_picture: str | None = None


class UserPublic(BaseModel):
    """Profile of a user as other users see it.

    Unlike ``UserRead``, it never contains the email address.
    """

    id_user: int
    username: str
    bio: str | None = None
    profile_picture: str | None = None
    profile_visibility: ProfileVisibility = "public"


class UserMe(UserRead):
    """Own account with its private settings.

    Returned by GET and PATCH /users/me/settings.
    """

    theme: Theme = "day"
    profile_visibility: ProfileVisibility = "public"
    is_admin: bool = False


class UserCreate(UserBase):
    """Data needed to insert a user in the database."""

    password_hash: str


class UserUpdate(BaseModel):
    """Body of PATCH /users/me (all fields optional)."""

    username: str | None = Field(default=None, min_length=3, max_length=30)
    email: EmailStr | None = Field(default=None, max_length=100)
    bio: str | None = None
    profile_picture: str | None = Field(default=None, max_length=255)

    @field_validator("username", "email")
    @classmethod
    def _not_null(cls, value: str | None) -> str | None:
        """Refuse an explicit null for a column that cannot be empty.

        Parameters
        ----------
        value : str | None
            Value sent by the client.

        Returns
        -------
        str | None
            The unchanged value.

        Raises
        ------
        ValueError
            If the client sent null.

        """
        if value is None:
            msg = "This field cannot be null."
            raise ValueError(msg)
        return value


class UserUpdateFull(UserUpdate):
    """Full user update, including the password hash."""

    password_hash: str | None = None


class UserUpdatePassword(BaseModel):
    """Body of PUT /users/me/password."""

    current_password: str
    new_password: str = Field(min_length=8, max_length=72)

    _password_bytes = field_validator("new_password")(_check_password_bytes)


class UserSettingsUpdate(BaseModel):
    """Body of PATCH /users/me/settings (all fields optional)."""

    theme: Theme | None = None
    profile_visibility: ProfileVisibility | None = None


class User(UserCreate, UserMe):
    """User as stored in the database (includes password_hash)."""

    is_banned: bool = False
    suspended_until: datetime | None = None


class UserFollow(BaseModel):
    """Schema representing a follow relationship between two users."""

    follower_id: int
    following_id: int
