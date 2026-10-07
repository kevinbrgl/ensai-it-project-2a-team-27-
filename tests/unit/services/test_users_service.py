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
    AuthError,
    EmailAlreadyExistsError,
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
