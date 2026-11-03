"""Integration tests for UserDAO, run against the real database.

Each test is rolled back (see tests/integration/conftest.py),
so the database is left unchanged.
"""

import pytest

from src.dao.users_dao import UserDAO
from src.models import User, UserCreate, UserUpdateFull
from src.utils.exceptions import (
    AlreadyFollowingError,
    EmailAlreadyExistsError,
    NotFollowingError,
    SelfFollowError,
    SelfUnfollowError,
    UserAlreadyExistsError,
    UserNotFoundError,
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


class TestSearchByUsername:
    """Tests for UserDAO.search_by_username."""

    def test_search_exact_match(self, user_dao: UserDAO, alice: User) -> None:
        """Searching with the exact username returns the user."""
        results = user_dao.search_by_username(alice.username)
        assert any(u.id_user == alice.id_user for u in results)

    def test_search_partial_case_insensitive(
        self,
        user_dao: UserDAO,
        alice: User,
    ) -> None:
        """Searching with a case-insensitive substring matches the user."""
        results = user_dao.search_by_username("ALICE")
        assert any(u.id_user == alice.id_user for u in results)

    def test_search_no_match(self, user_dao: UserDAO) -> None:
        """Searching for a nonexistent substring returns an empty list."""
        results = user_dao.search_by_username("nonexistent_user_xyz")
        assert results == []

    def test_search_limit(self, user_dao: UserDAO) -> None:
        """The limit parameter is respected."""
        prefix = "search_test_limit_"
        for i in range(3):
            user_dao.create(
                UserCreate(
                    username=f"{prefix}{i}",
                    email=f"{prefix}{i}@ensai.fr",
                    password_hash=PASSWORD_HASH,
                ),
            )
        results = user_dao.search_by_username(prefix, limit=2)
        assert len(results) == 2  # ruff: ignore[magic-value-comparison]


class TestFollow:
    """Tests for UserDAO.add_follow and is_following."""

    def test_add_follow_success(
        self,
        user_dao: UserDAO,
        alice: User,
    ) -> None:
        """A user can follow another user."""
        bob = user_dao.create(
            UserCreate(
                username="it_bob_follow",
                email="it_bob_follow@ensai.fr",
                password_hash=PASSWORD_HASH,
            ),
        )
        user_dao.add_follow(alice.id_user, bob.id_user)
        assert user_dao.is_following(alice.id_user, bob.id_user) is True
        assert user_dao.is_following(bob.id_user, alice.id_user) is False

    def test_add_follow_self_error(
        self,
        user_dao: UserDAO,
        alice: User,
    ) -> None:
        """A user cannot follow themselves."""
        with pytest.raises(SelfFollowError):
            user_dao.add_follow(alice.id_user, alice.id_user)

    def test_add_follow_already_following(
        self,
        user_dao: UserDAO,
        alice: User,
    ) -> None:
        """Following twice raises AlreadyFollowingError."""
        bob = user_dao.create(
            UserCreate(
                username="it_bob_follow_dup",
                email="it_bob_follow_dup@ensai.fr",
                password_hash=PASSWORD_HASH,
            ),
        )
        user_dao.add_follow(alice.id_user, bob.id_user)
        with pytest.raises(AlreadyFollowingError):
            user_dao.add_follow(alice.id_user, bob.id_user)

    def test_add_follow_target_not_found(
        self,
        user_dao: UserDAO,
        alice: User,
    ) -> None:
        """Following a nonexistent user raises UserNotFoundError."""
        with pytest.raises(UserNotFoundError):
            user_dao.add_follow(alice.id_user, UNKNOWN_ID)

    def test_remove_follow_success(
        self,
        user_dao: UserDAO,
        alice: User,
    ) -> None:
        """A user can unfollow a followed user."""
        bob = user_dao.create(
            UserCreate(
                username="it_bob_unfollow",
                email="it_bob_unfollow@ensai.fr",
                password_hash=PASSWORD_HASH,
            ),
        )
        user_dao.add_follow(alice.id_user, bob.id_user)
        assert user_dao.is_following(alice.id_user, bob.id_user) is True

        user_dao.remove_follow(alice.id_user, bob.id_user)
        assert user_dao.is_following(alice.id_user, bob.id_user) is False

    def test_remove_follow_self_error(
        self,
        user_dao: UserDAO,
        alice: User,
    ) -> None:
        """A user cannot unfollow themselves."""
        with pytest.raises(SelfUnfollowError):
            user_dao.remove_follow(alice.id_user, alice.id_user)

    def test_remove_follow_not_following(
        self,
        user_dao: UserDAO,
        alice: User,
    ) -> None:
        """Unfollowing when not following raises NotFollowingError."""
        bob = user_dao.create(
            UserCreate(
                username="it_bob_unfollow_not",
                email="it_bob_unfollow_not@ensai.fr",
                password_hash=PASSWORD_HASH,
            ),
        )
        with pytest.raises(NotFollowingError):
            user_dao.remove_follow(alice.id_user, bob.id_user)

    def test_get_followers_multiple(
        self,
        user_dao: UserDAO,
        alice: User,
    ) -> None:
        """get_followers returns all users who follow the user."""
        bob = user_dao.create(
            UserCreate(
                username="it_bob_follower_1",
                email="it_bob_follower_1@ensai.fr",
                password_hash=PASSWORD_HASH,
            ),
        )
        charlie = user_dao.create(
            UserCreate(
                username="it_charlie_follower_2",
                email="it_charlie_follower_2@ensai.fr",
                password_hash=PASSWORD_HASH,
            ),
        )
        user_dao.add_follow(bob.id_user, alice.id_user)
        user_dao.add_follow(charlie.id_user, alice.id_user)

        followers = user_dao.get_followers(alice.id_user)
        follower_ids = [f.id_user for f in followers]

        assert len(followers) == 2  # ruff: ignore[magic-value-comparison]
        assert bob.id_user in follower_ids
        assert charlie.id_user in follower_ids

    def test_get_followers_empty(
        self,
        user_dao: UserDAO,
        alice: User,
    ) -> None:
        """get_followers on a user with no followers returns empty list."""
        followers = user_dao.get_followers(alice.id_user)
        assert followers == []

    def test_get_following_multiple(
        self,
        user_dao: UserDAO,
        alice: User,
    ) -> None:
        """get_following returns all users followed by the user."""
        bob = user_dao.create(
            UserCreate(
                username="it_bob_following_1",
                email="it_bob_following_1@ensai.fr",
                password_hash=PASSWORD_HASH,
            ),
        )
        charlie = user_dao.create(
            UserCreate(
                username="it_charlie_following_2",
                email="it_charlie_following_2@ensai.fr",
                password_hash=PASSWORD_HASH,
            ),
        )
        user_dao.add_follow(alice.id_user, bob.id_user)
        user_dao.add_follow(alice.id_user, charlie.id_user)

        following = user_dao.get_following(alice.id_user)
        following_ids = [f.id_user for f in following]

        assert len(following) == 2  # ruff: ignore[magic-value-comparison]
        assert bob.id_user in following_ids
        assert charlie.id_user in following_ids

    def test_get_following_empty(
        self,
        user_dao: UserDAO,
        alice: User,
    ) -> None:
        """get_following on a user following nobody returns empty list."""
        following = user_dao.get_following(alice.id_user)
        assert following == []


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
