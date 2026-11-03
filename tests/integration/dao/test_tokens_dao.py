"""Integration tests for TokenDAO, run against the real database.

Each test is rolled back (see tests/integration/conftest.py),
so the database is left unchanged.
"""

from datetime import UTC, datetime, timedelta

import pytest
from psycopg2.extras import RealDictCursor

from src.dao.tokens_dao import TokenDAO

HASH_A = "a" * 64
HASH_B = "b" * 64


@pytest.fixture
def token_dao(cursor: RealDictCursor) -> TokenDAO:
    """Return a TokenDAO bound to the test cursor."""
    return TokenDAO(cursor)


@pytest.fixture
def expires_at() -> datetime:
    """Return an expiration date in the future."""
    return datetime.now(UTC) + timedelta(hours=1)


class TestRevoke:
    """Tests for TokenDAO.revoke."""

    def test_ok(self, token_dao: TokenDAO, expires_at: datetime) -> None:
        """A revoked token hash is stored and then found."""
        token_dao.revoke(HASH_A, expires_at)

        assert token_dao.is_revoked(HASH_A) is True

    def test_twice(self, token_dao: TokenDAO, expires_at: datetime) -> None:
        """Revoking the same token twice raises no error."""
        token_dao.revoke(HASH_A, expires_at)
        token_dao.revoke(HASH_A, expires_at)

        assert token_dao.is_revoked(HASH_A) is True

    def test_other_token_unaffected(
        self,
        token_dao: TokenDAO,
        expires_at: datetime,
    ) -> None:
        """Revoking one token does not revoke another one."""
        token_dao.revoke(HASH_A, expires_at)

        assert token_dao.is_revoked(HASH_B) is False


class TestIsRevoked:
    """Tests for TokenDAO.is_revoked."""

    def test_unknown_token(self, token_dao: TokenDAO) -> None:
        """A token that was never revoked is not in the list."""
        assert token_dao.is_revoked(HASH_A) is False
