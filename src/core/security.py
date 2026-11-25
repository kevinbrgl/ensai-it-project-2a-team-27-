"""Security utilities for password hashing and JWT token creation."""

from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from src.core.config import settings

ALGORITHM = "HS256"


def create_access_token(subject: int, expires_delta: timedelta) -> str:
    """Create a JWT access token.

    Parameters
    ----------
    subject : int
        User ID stored in the token's subject claim.
    expires_delta : timedelta
        Time from creation until the token expires.

    Returns
    -------
    str
        Encoded JWT signed with the application's secret key.

    """
    expire = datetime.now(UTC) + expires_delta
    to_encode = {"exp": expire, "sub": str(subject)}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hash.

    Parameters
    ----------
    plain_password : str
        Password submitted by the user.
    hashed_password : str
        Stored password hash to check against.

    Returns
    -------
    bool
        Whether the submitted password matches the stored hash.

    """
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("ascii"),
    )


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt.

    Parameters
    ----------
    password : str
        Plain-text password to hash.

    Returns
    -------
    str
        Bcrypt hash suitable for storage.

    """
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("ascii")
