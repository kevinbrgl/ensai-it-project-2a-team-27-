"""Unit tests for UserService.

The UserDAO is replaced by a mock: no database is needed.
"""

from unittest.mock import Mock

import pytest
from pytest_mock import MockerFixture

from src.core.security import verify_password
from src.dao.users_dao import UserDAO
from src.models import User, UserCreate, UserRegister
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
    """Tests for UserService.authenticate (used by /auth/login)."""

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
