"""Service layer for token revocation (logout)."""

import hashlib
from datetime import UTC, datetime

import jwt

from src.core import security
from src.core.config import settings
from src.dao.tokens_dao import TokenDAO


def hash_token(token: str) -> str:
    """Return the SHA-256 hash of a token.

    :param token: The JWT
    :return: Hexadecimal hash
    """
    return hashlib.sha256(token.encode()).hexdigest()


class TokenService:
    """Service class for revoking and checking tokens.

    :attr dao: Associated TokenDAO object
    """

    def __init__(self, token_dao: TokenDAO) -> None:
        """Initialize TokenService with a TokenDAO.

        :param token_dao: DAO used to access revoked tokens
        """
        self.dao = token_dao

    def revoke(self, token: str) -> None:
        """Revoke a token until its natural expiration.

        :param token: The JWT to revoke
        """
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[security.ALGORITHM],
        )
        expires_at = datetime.fromtimestamp(payload["exp"], tz=UTC)
        self.dao.revoke(hash_token(token), expires_at)

    def is_revoked(self, token: str) -> bool:
        """Tell whether a token has been revoked.

        :param token: The JWT to check
        :return: True if the token is revoked
        """
        return self.dao.is_revoked(hash_token(token))
