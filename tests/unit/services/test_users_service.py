"""Unit tests for UserService.
"""
import pytest
from pytest_mock import MockerFixture
from unittest.mock import Mock

import importlib

from src.core.security import get_password_hash, verify_password
from src.dao.users_dao import UserDAO
from src.models import User, UserRegister, UserCreate, UserRead, UserUpdate, UserUpdatePassword
from src.services.users_service import UserService
from src.utils.exceptions import UserNotFoundError, SamePasswordError, IncorrectPasswordError, UserAlreadyExistsError, AuthError
from tests.mocks import mock_user_dao as mock_dao



@pytest.fixture
def service(mock_dao: Mock) -> UserService:
    """Fixture for UserService instance."""
    return UserService(mock_dao)


class TestAuthenticate:

    def test_valid(self,
                   service: UserService,
                   mock_dao: Mock,
                   mocker: MockerFixture):
        expected = User(id=1, username="johndoe", hashed_password="hashedpwd")
        mock_dao.read_by_username.return_value = expected

        # mocker.patch.object(importlib.import_module("src.dao.u"), "verify_password", return_value=True)
        mocker.patch("src.services.users.verify_password", return_value=True)

        user = service.authenticate("johndoe", "pwd")

        assert user == expected
        mock_dao.read_by_username.assert_called_once_with("johndoe")

    def test_user_not_found(self, service: UserService, mock_dao: Mock):
        mock_dao.read_by_username.return_value = None

        with pytest.raises(UserNotFoundError) as exc:
            service.authenticate("johndoe", "pwd")
        
        # assert exc.value.username == "johndoe"
        mock_dao.read_by_username.assert_called_once_with("johndoe")

    def test_wrong_password(self,
                            service: UserService,
                            mock_dao: Mock, 
                            mocker: MockerFixture):
        user = User(id=1, username="johndoe", hashed_password="hashedpwd")
        mock_dao.read_by_username.return_value = user

        mocker.patch("src.services.users.verify_password", return_value=False)

        with pytest.raises(AuthError):
            service.authenticate("johndoe", "badpwd")


class TestRegister:
    
    def test_valid(self, service: UserService, mock_dao: Mock):
        user_in = UserRegister(username="johndoe", password="pw")
        expected_user = User(
            id=1, username="johndoe", hashed_password=get_password_hash("pw")
        )

        mock_dao.create.return_value = expected_user
        user = service.register(user_in)

        user_create: UserCreate = mock_dao.create.call_args[0][0]

        assert user_create.username == "johndoe"
        assert verify_password("pw", user.hashed_password)
        assert user == expected_user

