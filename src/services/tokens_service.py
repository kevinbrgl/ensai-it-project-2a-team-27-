"""Service layer for token revocation (logout)."""

import hashlib
from datetime import UTC, datetime

import jwt

from src.core import security
from src.core.config import settings
from src.dao.tokens_dao import TokenDAO


def hash_token(token: str) -> str:
    """Return the SHA-256 hash of a token.

    Parameters
    ----------
    token : str
        The JWT.

    Returns
    -------
    str
        Hexadecimal hash.

    """
    return hashlib.sha256(token.encode()).hexdigest()


class TokenService:
    """Revoke access tokens and check their revocation status.

    Attributes
    ----------
    dao : TokenDAO
        Associated TokenDAO object.

    """

    def __init__(self, token_dao: TokenDAO) -> None:
        """Initialize TokenService with a TokenDAO.

        Parameters
        ----------
        token_dao : TokenDAO
            DAO used to access revoked tokens.

        """
        self.dao = token_dao

    def revoke(self, token: str) -> None:
        """Revoke a token until its natural expiration.

        Parameters
        ----------
        token : str
            The JWT to revoke.

        Notes
        -----
        An invalid or expired JWT raises ``jwt.InvalidTokenError``. A missing
        expiration claim raises ``KeyError``.

        """
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[security.ALGORITHM],
        )
        expires_at = datetime.fromtimestamp(payload["exp"], tz=UTC)
        self.dao.revoke(hash_token(token), expires_at)

    def is_revoked(self, token: str) -> bool:
        """Check whether a token has been revoked.

        Parameters
        ----------
        token : str
            The JWT to check.

        Returns
        -------
        bool
            True if the token is revoked, otherwise False.

        """
        return self.dao.is_revoked(hash_token(token))
