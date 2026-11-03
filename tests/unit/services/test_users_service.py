"""Unit tests for UserService.

The UserDAO is replaced by a mock: no database is needed.
"""

from datetime import timedelta
from unittest.mock import Mock

import jwt
import pytest
from pytest_mock import MockerFixture

from src.core.config import settings
from src.core.security import ALGORITHM, verify_password
from src.dao.users_dao import UserDAO
from src.models import Token, User, UserCreate, UserRegister
from src.services.users_service import UserService
from src.utils.exceptions import (
    AlreadyFollowingError,
    AuthError,
    EmailAlreadyExistsError,
    NotFollowingError,
    SelfFollowError,
    SelfUnfollowError,
    UserAlreadyExistsError,
    UserNotFoundError,
)

USERNAME = "johndoe"
EMAIL = "john@ensai.fr"
PASSWORD = "motdepasse123"
FAKE_JWT = "fake.jwt.value"


@pytest.fixture
def mock_dao(mocker: MockerFixture) -> Mock:
    """Return a fake UserDAO with the same methods as the real one."""
    return mocker.Mock(spec=UserDAO)


@pytest.fixture
def service(mock_dao: Mock) -> UserService:
    """Return a UserService using the mocked DAO."""
    return UserService(mock_dao)


@pytest.fixture
def db_user() -> User:
    """Return a user as stored in the database."""
    return User(
        id_user=1,
        username=USERNAME,
        email=EMAIL,
        password_hash="hashedpwd",
    )


class TestAuthenticate:
    """Tests for UserService.authenticate (used by UserService.login)."""

    def test_valid(
        self,
        service: UserService,
        mock_dao: Mock,
        db_user: User,
        mocker: MockerFixture,
    ) -> None:
        """Right username and password: the user is returned."""
        mock_dao.read_by_username.return_value = db_user
        mocker.patch(
            "src.services.users_service.verify_password",
            return_value=True,
        )

        user = service.authenticate(USERNAME, PASSWORD)

        assert user == db_user
        mock_dao.read_by_username.assert_called_once_with(USERNAME)

    def test_user_not_found(
        self,
        service: UserService,
        mock_dao: Mock,
    ) -> None:
        """Unknown username: UserNotFoundError."""
        mock_dao.read_by_username.return_value = None

        with pytest.raises(UserNotFoundError):
            service.authenticate(USERNAME, PASSWORD)

        mock_dao.read_by_username.assert_called_once_with(USERNAME)

    def test_wrong_password(
        self,
        service: UserService,
        mock_dao: Mock,
        db_user: User,
        mocker: MockerFixture,
    ) -> None:
        """Wrong password: AuthError."""
        mock_dao.read_by_username.return_value = db_user
        mocker.patch(
            "src.services.users_service.verify_password",
            return_value=False,
        )

        with pytest.raises(AuthError):
            service.authenticate(USERNAME, "mauvaismdp")


class TestLogin:
    """Tests for UserService.login (POST /auth/login)."""

    def test_valid(
        self,
        service: UserService,
        mock_dao: Mock,
        db_user: User,
        mocker: MockerFixture,
    ) -> None:
        """Right credentials: a signed JWT for this user is returned."""
        mock_dao.read_by_username.return_value = db_user
        mocker.patch(
            "src.services.users_service.verify_password",
            return_value=True,
        )

        token = service.login(USERNAME, PASSWORD)

        assert isinstance(token, Token)
        assert token.token_type == settings.TOKEN_TYPE
        payload = jwt.decode(
            token.access_token,
            settings.SECRET_KEY,
            algorithms=[ALGORITHM],
        )
        assert payload["sub"] == str(db_user.id_user)
        assert "exp" in payload

    def test_token_lifetime(
        self,
        service: UserService,
        mock_dao: Mock,
        db_user: User,
        mocker: MockerFixture,
    ) -> None:
        """The token is built for the user id with the configured lifetime."""
        mock_dao.read_by_username.return_value = db_user
        mocker.patch(
            "src.services.users_service.verify_password",
            return_value=True,
        )
        mock_create = mocker.patch(
            "src.services.users_service.create_access_token",
            return_value=FAKE_JWT,
        )

        token = service.login(USERNAME, PASSWORD)

        assert token.access_token == FAKE_JWT
        mock_create.assert_called_once_with(
            db_user.id_user,
            expires_delta=timedelta(
                minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
            ),
        )

    def test_user_not_found(
        self,
        service: UserService,
        mock_dao: Mock,
        mocker: MockerFixture,
    ) -> None:
        """Unknown username: UserNotFoundError, no token created."""
        mock_dao.read_by_username.return_value = None
        mock_create = mocker.patch(
            "src.services.users_service.create_access_token",
        )

        with pytest.raises(UserNotFoundError):
            service.login(USERNAME, PASSWORD)

        mock_create.assert_not_called()

    def test_wrong_password(
        self,
        service: UserService,
        mock_dao: Mock,
        db_user: User,
        mocker: MockerFixture,
    ) -> None:
        """Wrong password: AuthError, no token created."""
        mock_dao.read_by_username.return_value = db_user
        mocker.patch(
            "src.services.users_service.verify_password",
            return_value=False,
        )
        mock_create = mocker.patch(
            "src.services.users_service.create_access_token",
        )

        with pytest.raises(AuthError):
            service.login(USERNAME, "mauvaismdp")

        mock_create.assert_not_called()


class TestRegister:
    """Tests for UserService.register (POST /auth/register)."""

    @pytest.fixture
    def user_in(self) -> UserRegister:
        """Return the registration data sent by the client."""
        return UserRegister(username=USERNAME, email=EMAIL, password=PASSWORD)

    def test_valid(
        self,
        service: UserService,
        mock_dao: Mock,
        user_in: UserRegister,
        db_user: User,
    ) -> None:
        """New username and email: the user is created and returned."""
        mock_dao.read_by_username.return_value = None
        mock_dao.read_by_email.return_value = None
        mock_dao.create.return_value = db_user

        user = service.register(user_in)

        assert user == db_user
        mock_dao.read_by_username.assert_called_once_with(USERNAME)
        mock_dao.read_by_email.assert_called_once_with(EMAIL)
        mock_dao.create.assert_called_once()

    def test_password_is_hashed(
        self,
        service: UserService,
        mock_dao: Mock,
        user_in: UserRegister,
    ) -> None:
        """The DAO receives a bcrypt hash, never the plain password."""
        mock_dao.read_by_username.return_value = None
        mock_dao.read_by_email.return_value = None

        service.register(user_in)

        user_create: UserCreate = mock_dao.create.call_args[0][0]
        assert user_create.username == USERNAME
        assert user_create.email == EMAIL
        assert "password" not in user_create.model_dump()
        assert user_create.password_hash != PASSWORD
        assert verify_password(PASSWORD, user_create.password_hash)

    def test_username_taken(
        self,
        service: UserService,
        mock_dao: Mock,
        user_in: UserRegister,
        db_user: User,
    ) -> None:
        """Username already used: UserAlreadyExistsError, nothing created."""
        mock_dao.read_by_username.return_value = db_user

        with pytest.raises(UserAlreadyExistsError):
            service.register(user_in)

        mock_dao.create.assert_not_called()

    def test_email_taken(
        self,
        service: UserService,
        mock_dao: Mock,
        user_in: UserRegister,
        db_user: User,
    ) -> None:
        """Email already used: EmailAlreadyExistsError, nothing created."""
        mock_dao.read_by_username.return_value = None
        mock_dao.read_by_email.return_value = db_user

        with pytest.raises(EmailAlreadyExistsError):
            service.register(user_in)

        mock_dao.create.assert_not_called()


class TestSearchUsers:
    """Tests for UserService.search_users."""

    def test_search_valid(
        self,
        service: UserService,
        mock_dao: Mock,
        db_user: User,
    ) -> None:
        """Searching with a valid query returns matching users."""
        mock_dao.search_by_username.return_value = [db_user]

        result = service.search_users("john")

        assert result == [db_user]
        mock_dao.search_by_username.assert_called_once_with("john", limit=10)

    def test_search_whitespace_trimmed(
        self,
        service: UserService,
        mock_dao: Mock,
        db_user: User,
    ) -> None:
        """Leading/trailing spaces are trimmed before querying the DAO."""
        mock_dao.search_by_username.return_value = [db_user]

        result = service.search_users("  john  ", limit=5)

        assert result == [db_user]
        mock_dao.search_by_username.assert_called_once_with("john", limit=5)

    def test_search_empty_query(
        self,
        service: UserService,
        mock_dao: Mock,
    ) -> None:
        """Empty query returns an empty list without calling the DAO."""
        result = service.search_users("   ")

        assert result == []
        mock_dao.search_by_username.assert_not_called()


class TestFollowUser:
    """Tests for UserService.follow_user."""

    def test_follow_valid(
        self,
        service: UserService,
        mock_dao: Mock,
        db_user: User,
    ) -> None:
        """Following another existing user succeeds."""
        mock_dao.read.return_value = db_user

        service.follow_user(follower_id=1, following_id=2)

        mock_dao.read.assert_called_once_with(2)
        mock_dao.add_follow.assert_called_once_with(1, 2)

    def test_follow_self_rejected(
        self,
        service: UserService,
        mock_dao: Mock,
    ) -> None:
        """Following oneself raises SelfFollowError."""
        with pytest.raises(SelfFollowError):
            service.follow_user(follower_id=1, following_id=1)

        mock_dao.read.assert_not_called()
        mock_dao.add_follow.assert_not_called()

    def test_follow_target_not_found(
        self,
        service: UserService,
        mock_dao: Mock,
    ) -> None:
        """Following a nonexistent user raises UserNotFoundError."""
        mock_dao.read.return_value = None

        with pytest.raises(UserNotFoundError):
            service.follow_user(follower_id=1, following_id=999)

        mock_dao.read.assert_called_once_with(999)
        mock_dao.add_follow.assert_not_called()

    def test_follow_already_following(
        self,
        service: UserService,
        mock_dao: Mock,
        db_user: User,
    ) -> None:
        """Following an already followed user raises AlreadyFollowingError."""
        mock_dao.read.return_value = db_user
        mock_dao.add_follow.side_effect = AlreadyFollowingError

        with pytest.raises(AlreadyFollowingError):
            service.follow_user(follower_id=1, following_id=2)

        mock_dao.add_follow.assert_called_once_with(1, 2)


class TestUnfollowUser:
    """Tests for UserService.unfollow_user."""

    def test_unfollow_valid(
        self,
        service: UserService,
        mock_dao: Mock,
        db_user: User,
    ) -> None:
        """Unfollowing an existing followed user succeeds."""
        mock_dao.read.return_value = db_user

        service.unfollow_user(follower_id=1, following_id=2)

        mock_dao.read.assert_called_once_with(2)
        mock_dao.remove_follow.assert_called_once_with(1, 2)

    def test_unfollow_self_rejected(
        self,
        service: UserService,
        mock_dao: Mock,
    ) -> None:
        """Unfollowing oneself raises SelfUnfollowError."""
        with pytest.raises(SelfUnfollowError):
            service.unfollow_user(follower_id=1, following_id=1)

        mock_dao.read.assert_not_called()
        mock_dao.remove_follow.assert_not_called()

    def test_unfollow_target_not_found(
        self,
        service: UserService,
        mock_dao: Mock,
    ) -> None:
        """Unfollowing a nonexistent user raises UserNotFoundError."""
        mock_dao.read.return_value = None

        with pytest.raises(UserNotFoundError):
            service.unfollow_user(follower_id=1, following_id=999)

        mock_dao.read.assert_called_once_with(999)
        mock_dao.remove_follow.assert_not_called()

    def test_unfollow_not_following(
        self,
        service: UserService,
        mock_dao: Mock,
        db_user: User,
    ) -> None:
        """Unfollowing when not following raises NotFollowingError."""
        mock_dao.read.return_value = db_user
        mock_dao.remove_follow.side_effect = NotFollowingError

        with pytest.raises(NotFollowingError):
            service.unfollow_user(follower_id=1, following_id=2)

        mock_dao.remove_follow.assert_called_once_with(1, 2)


class TestGetFollowers:
    """Tests for UserService.get_followers."""

    def test_get_followers_valid(
        self,
        service: UserService,
        mock_dao: Mock,
        db_user: User,
    ) -> None:
        """Retrieving followers for an existing user returns follower list."""
        follower = User(
            id_user=2,
            username="bob",
            email="bob@ensai.fr",
            password_hash="hash",
            bio="bio",
            profile_picture="pic",
        )
        mock_dao.read.return_value = db_user
        mock_dao.get_followers.return_value = [follower]

        result = service.get_followers(1)

        assert result == [follower]
        mock_dao.read.assert_called_once_with(1)
        mock_dao.get_followers.assert_called_once_with(1)

    def test_get_followers_empty(
        self,
        service: UserService,
        mock_dao: Mock,
        db_user: User,
    ) -> None:
        """User with no followers returns an empty list."""
        mock_dao.read.return_value = db_user
        mock_dao.get_followers.return_value = []

        result = service.get_followers(1)

        assert result == []
        mock_dao.read.assert_called_once_with(1)
        mock_dao.get_followers.assert_called_once_with(1)

    def test_get_followers_user_not_found(
        self,
        service: UserService,
        mock_dao: Mock,
    ) -> None:
        """Followers for nonexistent user raises UserNotFoundError."""
        mock_dao.read.return_value = None

        with pytest.raises(UserNotFoundError):
            service.get_followers(999)

        mock_dao.read.assert_called_once_with(999)
        mock_dao.get_followers.assert_not_called()
