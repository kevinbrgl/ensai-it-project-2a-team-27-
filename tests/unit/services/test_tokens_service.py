"""Unit tests for TokenService.

The TokenDAO is replaced by a mock: no database is needed.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest
from jwt.exceptions import InvalidTokenError
from pytest_mock import MockerFixture

from src.core.security import create_access_token
from src.dao.tokens_dao import TokenDAO
from src.services.tokens_service import TokenService, hash_token

ID_USER = 1
TOKEN_LIFETIME = timedelta(minutes=5)


@pytest.fixture
def mock_dao(mocker: MockerFixture) -> Mock:
    """Return a fake TokenDAO with the same methods as the real one."""
    return mocker.Mock(spec=TokenDAO)


@pytest.fixture
def service(mock_dao: Mock) -> TokenService:
    """Return a TokenService using the mocked DAO."""
    return TokenService(mock_dao)


@pytest.fixture
def token() -> str:
    """Return a valid JWT for a test user."""
    return create_access_token(ID_USER, TOKEN_LIFETIME)


class TestHashToken:
    """Tests for hash_token."""

    def test_same_token_same_hash(self, token: str) -> None:
        """Hashing the same token twice gives the same value."""
        assert hash_token(token) == hash_token(token)

    def test_hash_is_not_the_token(self, token: str) -> None:
        """The stored value is a 64-character hash, not the token."""
        result = hash_token(token)

        assert result != token
        assert len(result) == 64  # ruff: ignore[magic-value-comparison]

    def test_different_tokens_different_hashes(self) -> None:
        """Two different tokens do not share the same hash."""
        assert hash_token("token_a") != hash_token("token_b")


class TestRevoke:
    """Tests for TokenService.revoke."""

    def test_valid(
        self,
        service: TokenService,
        mock_dao: Mock,
        token: str,
    ) -> None:
        """A valid token is sent to the DAO as a hash with its expiry."""
        service.revoke(token)

        mock_dao.revoke.assert_called_once()
        token_hash, expires_at = mock_dao.revoke.call_args.args
        assert token_hash == hash_token(token)
        assert expires_at > datetime.now(UTC)
        assert expires_at < datetime.now(UTC) + TOKEN_LIFETIME

    def test_invalid_token(
        self,
        service: TokenService,
        mock_dao: Mock,
    ) -> None:
        """A malformed token raises InvalidTokenError, nothing is stored."""
        with pytest.raises(InvalidTokenError):
            service.revoke("not.a.token")

        mock_dao.revoke.assert_not_called()


class TestIsRevoked:
    """Tests for TokenService.is_revoked."""

    def test_revoked(
        self,
        service: TokenService,
        mock_dao: Mock,
        token: str,
    ) -> None:
        """A token known by the DAO is reported as revoked."""
        mock_dao.is_revoked.return_value = True

        assert service.is_revoked(token) is True
        mock_dao.is_revoked.assert_called_once_with(hash_token(token))

    def test_not_revoked(
        self,
        service: TokenService,
        mock_dao: Mock,
        token: str,
    ) -> None:
        """A token unknown to the DAO is not revoked."""
        mock_dao.is_revoked.return_value = False

        assert service.is_revoked(token) is False
