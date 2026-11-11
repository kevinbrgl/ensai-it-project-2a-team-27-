"""Unit tests for the settings and account-status parts of UserService."""

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest
from pytest_mock import MockerFixture

from src.dao.users_dao import UserDAO
from src.models.users import User, UserSettingsUpdate
from src.services.users_service import UserService
from src.utils.exceptions import (
    AccountBannedError,
    AccountSuspendedError,
    UserNotFoundError,
)

ID_USER = 1


def _user(**kwargs: object) -> User:
    return User(
        id_user=ID_USER,
        username="alice",
        email="alice@ensai.fr",
        password_hash="hashed",
        **kwargs,
    )


@pytest.fixture
def dao(mocker: MockerFixture) -> Mock:
    """Return a fake UserDAO."""
    return mocker.Mock(spec=UserDAO)


@pytest.fixture
def service(dao: Mock) -> UserService:
    """Return a UserService using the mocked DAO."""
    return UserService(dao)


class TestEnsureActive:
    """Tests for UserService.ensure_active."""

    def test_active_user(self) -> None:
        """A normal user passes."""
        UserService.ensure_active(_user())

    def test_banned(self) -> None:
        """A banned user is refused."""
        with pytest.raises(AccountBannedError):
            UserService.ensure_active(_user(is_banned=True))

    def test_suspended(self) -> None:
        """A running suspension is refused."""
        until = datetime.now(UTC) + timedelta(days=1)
        with pytest.raises(AccountSuspendedError):
            UserService.ensure_active(_user(suspended_until=until))

    def test_suspension_over(self) -> None:
        """An expired suspension no longer blocks the user."""
        until = datetime.now(UTC) - timedelta(days=1)
        UserService.ensure_active(_user(suspended_until=until))


class TestLoginBlocked:
    """Login of banned or suspended users."""

    def test_banned_cannot_login(
        self,
        service: UserService,
        dao: Mock,
        mocker: MockerFixture,
    ) -> None:
        """Right password but banned account raises AccountBannedError."""
        mocker.patch(
            "src.services.users_service.verify_password",
            return_value=True,
        )
        dao.read_by_username.return_value = _user(is_banned=True)

        with pytest.raises(AccountBannedError):
            service.login("alice", "password123")

    def test_suspended_cannot_login(
        self,
        service: UserService,
        dao: Mock,
        mocker: MockerFixture,
    ) -> None:
        """Right password but suspended account raises the error."""
        mocker.patch(
            "src.services.users_service.verify_password",
            return_value=True,
        )
        until = datetime.now(UTC) + timedelta(days=3)
        dao.read_by_username.return_value = _user(suspended_until=until)

        with pytest.raises(AccountSuspendedError):
            service.login("alice", "password123")


class TestUpdateSettings:
    """Tests for UserService.update_settings."""

    def test_success(self, service: UserService, dao: Mock) -> None:
        """The DAO is called and the updated user returned."""
        body = UserSettingsUpdate(theme="night")
        dao.update_settings.return_value = _user(theme="night")

        result = service.update_settings(ID_USER, body)

        assert result.theme == "night"
        dao.update_settings.assert_called_once_with(ID_USER, body)

    def test_nothing_to_update(
        self,
        service: UserService,
        dao: Mock,
    ) -> None:
        """An empty body raises ValueError without calling the DAO."""
        with pytest.raises(ValueError, match="Nothing to update"):
            service.update_settings(ID_USER, UserSettingsUpdate())
        dao.update_settings.assert_not_called()

    def test_user_not_found(self, service: UserService, dao: Mock) -> None:
        """Unknown user raises UserNotFoundError."""
        dao.update_settings.return_value = None

        with pytest.raises(UserNotFoundError):
            service.update_settings(
                ID_USER,
                UserSettingsUpdate(profile_visibility="private"),
            )
