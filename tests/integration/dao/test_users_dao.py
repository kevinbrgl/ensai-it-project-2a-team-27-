"""Integration tests for UserDAO, run against the real database.

Each test is rolled back (see tests/integration/conftest.py),
so the database is left unchanged.
"""

import pytest

from src.dao.users_dao import UserDAO
from src.models import User, UserCreate, UserUpdateFull
from src.utils.exceptions import (
    EmailAlreadyExistsError,
    UserAlreadyExistsError,
)

USERNAME = "it_alice"
EMAIL = "it_alice@ensai.fr"
PASSWORD_HASH = "$2b$12$fakehashfakehashfakehash"
UNKNOWN_ID = 999_999_999


@pytest.fixture
def alice(user_dao: UserDAO) -> User:
    """Insert a test user in the database and return it."""
    return user_dao.create(
        UserCreate(
            username=USERNAME,
            email=EMAIL,
            password_hash=PASSWORD_HASH,
        ),
    )


class TestCreate:
    """Tests for UserDAO.create."""

    def test_ok(self, user_dao: UserDAO) -> None:
        """The user is inserted and returned with its generated id."""
        user = user_dao.create(
            UserCreate(
                username=USERNAME,
                email=EMAIL,
                password_hash=PASSWORD_HASH,
            ),
        )

        assert isinstance(user.id_user, int)
        assert user.username == USERNAME
        assert user.email == EMAIL
        assert user.password_hash == PASSWORD_HASH
        assert user.bio is None
        assert user.profile_picture is None

    def test_duplicate_username(self, user_dao: UserDAO, alice: User) -> None:
        """Same username: UNIQUE constraint -> UserAlreadyExistsError."""
        with pytest.raises(UserAlreadyExistsError):
            user_dao.create(
                UserCreate(
                    username=alice.username,
                    email="other@ensai.fr",
                    password_hash=PASSWORD_HASH,
                ),
            )

    def test_duplicate_email(self, user_dao: UserDAO, alice: User) -> None:
        """Same email: UNIQUE constraint -> EmailAlreadyExistsError."""
        with pytest.raises(EmailAlreadyExistsError):
            user_dao.create(
                UserCreate(
                    username="it_bob",
                    email=alice.email,
                    password_hash=PASSWORD_HASH,
                ),
            )


class TestRead:
    """Tests for UserDAO.read (by id)."""

    def test_found(self, user_dao: UserDAO, alice: User) -> None:
        """An existing id returns the user."""
        assert user_dao.read(alice.id_user) == alice

    def test_not_found(self, user_dao: UserDAO) -> None:
        """An unknown id returns None."""
        assert user_dao.read(UNKNOWN_ID) is None


class TestReadByUsername:
    """Tests for UserDAO.read_by_username."""

    def test_found(self, user_dao: UserDAO, alice: User) -> None:
        """An existing username returns the user."""
        assert user_dao.read_by_username(USERNAME) == alice

    def test_not_found(self, user_dao: UserDAO) -> None:
        """An unknown username returns None."""
        assert user_dao.read_by_username("it_nobody") is None


class TestReadByEmail:
    """Tests for UserDAO.read_by_email."""

    def test_found(self, user_dao: UserDAO, alice: User) -> None:
        """An existing email returns the user."""
        assert user_dao.read_by_email(EMAIL) == alice

    def test_not_found(self, user_dao: UserDAO) -> None:
        """An unknown email returns None."""
        assert user_dao.read_by_email("nobody@ensai.fr") is None


class TestUpdate:
    """Tests for UserDAO.update."""

    def test_ok(self, user_dao: UserDAO, alice: User) -> None:
        """Only the given field changes."""
        updated = user_dao.update(
            alice.id_user,
            UserUpdateFull(bio="J'aime la SF"),
        )

        assert updated is not None
        assert updated.bio == "J'aime la SF"
        assert updated.username == alice.username
        assert updated.email == alice.email

    def test_unknown_id(self, user_dao: UserDAO) -> None:
        """An unknown id returns None."""
        assert user_dao.update(UNKNOWN_ID, UserUpdateFull(bio="x")) is None

    def test_nothing_to_update(self, user_dao: UserDAO, alice: User) -> None:
        """An empty update raises ValueError."""
        with pytest.raises(ValueError, match="Nothing to update"):
            user_dao.update(alice.id_user, UserUpdateFull())
