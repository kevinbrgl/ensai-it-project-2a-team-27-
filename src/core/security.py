"""Security utilities for password hashing and JWT token creation."""

from datetime import UTC, datetime, timedelta

import jwt
from passlib.context import CryptContext

from src.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"


def create_access_token(subject: int, expires_delta: timedelta) -> str:
    """Create a JWT access token.

    :param subject: Subject (user ID) for the token
    :param expires_delta: Expiration time delta
    :return: Encoded JWT token
    """
    expire = datetime.now(UTC) + expires_delta
    to_encode = {"exp": expire, "sub": str(subject)}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hash.

    :param plain_password: The plain password
    :param hashed_password: The hashed password
    :return: True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt.

    :param password: The plain password
    :return: The hashed password
    """
    return pwd_context.hash(password)
