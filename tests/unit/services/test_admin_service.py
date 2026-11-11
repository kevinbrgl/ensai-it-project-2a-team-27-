"""Unit tests for AdminService.

The DAOs are replaced by mocks: no database is needed.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest
from pytest_mock import MockerFixture

from src.dao.reviews_dao import ReviewDAO
from src.dao.users_dao import UserDAO
from src.models.users import User
from src.services.admin_service import AdminService
from src.utils.exceptions import (
    AdminModerationError,
    ReviewNotFoundError,
    SelfModerationError,
    UserNotFoundError,
)

ADMIN_ID = 1
TARGET_ID = 2
ID_REVIEW = 10
DAYS = 7


def _user(
    id_user: int,
    *,
    is_admin: bool = False,
    is_banned: bool = False,
    suspended_until: datetime | None = None,
) -> User:
    return User(
        id_user=id_user,
        username=f"user{id_user}",
        email=f"user{id_user}@ensai.fr",
        password_hash="hashed",
        is_admin=is_admin,
        is_banned=is_banned,
        suspended_until=suspended_until,
    )


@pytest.fixture
def user_dao(mocker: MockerFixture) -> Mock:
    """Return a fake UserDAO."""
    return mocker.Mock(spec=UserDAO)


@pytest.fixture
def review_dao(mocker: MockerFixture) -> Mock:
    """Return a fake ReviewDAO."""
    return mocker.Mock(spec=ReviewDAO)


@pytest.fixture
def service(user_dao: Mock, review_dao: Mock) -> AdminService:
    """Return an AdminService using the mocked DAOs."""
    return AdminService(user_dao, review_dao)


class TestSuspendUser:
    """Tests for AdminService.suspend_user."""

    def test_success(self, service: AdminService, user_dao: Mock) -> None:
        """The user is suspended for the given number of days."""
        user_dao.read.return_value = _user(TARGET_ID)
        user_dao.set_suspended_until.side_effect = (
            lambda uid, until: _user(uid, suspended_until=until)
        )
        before = datetime.now(UTC)

        result = service.suspend_user(ADMIN_ID, TARGET_ID, DAYS)

        assert result.id_user == TARGET_ID
        assert result.is_banned is False
        assert result.suspended_until is not None
        assert result.suspended_until - before >= timedelta(days=DAYS)
        user_dao.set_suspended_until.assert_called_once()

    def test_self(self, service: AdminService, user_dao: Mock) -> None:
        """An admin cannot suspend themself."""
        with pytest.raises(SelfModerationError):
            service.suspend_user(ADMIN_ID, ADMIN_ID, DAYS)
        user_dao.read.assert_not_called()

    def test_unknown_user(
        self,
        service: AdminService,
        user_dao: Mock,
    ) -> None:
        """Unknown user raises UserNotFoundError."""
        user_dao.read.return_value = None

        with pytest.raises(UserNotFoundError):
            service.suspend_user(ADMIN_ID, TARGET_ID, DAYS)
        user_dao.set_suspended_until.assert_not_called()

    def test_admin_target(
        self,
        service: AdminService,
        user_dao: Mock,
    ) -> None:
        """Another admin cannot be suspended."""
        user_dao.read.return_value = _user(TARGET_ID, is_admin=True)

        with pytest.raises(AdminModerationError):
            service.suspend_user(ADMIN_ID, TARGET_ID, DAYS)
        user_dao.set_suspended_until.assert_not_called()


class TestBanUser:
    """Tests for AdminService.ban_user."""

    def test_success(self, service: AdminService, user_dao: Mock) -> None:
        """The user is banned."""
        user_dao.read.return_value = _user(TARGET_ID)
        user_dao.set_banned.return_value = _user(TARGET_ID, is_banned=True)

        result = service.ban_user(ADMIN_ID, TARGET_ID)

        assert result.is_banned is True
        user_dao.set_banned.assert_called_once_with(TARGET_ID, banned=True)

    def test_self(self, service: AdminService, user_dao: Mock) -> None:
        """An admin cannot ban themself."""
        with pytest.raises(SelfModerationError):
            service.ban_user(ADMIN_ID, ADMIN_ID)
        user_dao.set_banned.assert_not_called()

    def test_unknown_user(
        self,
        service: AdminService,
        user_dao: Mock,
    ) -> None:
        """Unknown user raises UserNotFoundError."""
        user_dao.read.return_value = None

        with pytest.raises(UserNotFoundError):
            service.ban_user(ADMIN_ID, TARGET_ID)

    def test_admin_target(
        self,
        service: AdminService,
        user_dao: Mock,
    ) -> None:
        """Another admin cannot be banned."""
        user_dao.read.return_value = _user(TARGET_ID, is_admin=True)

        with pytest.raises(AdminModerationError):
            service.ban_user(ADMIN_ID, TARGET_ID)
        user_dao.set_banned.assert_not_called()


class TestDeleteReview:
    """Tests for AdminService.delete_review."""

    def test_success(self, service: AdminService, review_dao: Mock) -> None:
        """Any review is deleted, without author check."""
        service.delete_review(ID_REVIEW)

        review_dao.delete.assert_called_once_with(ID_REVIEW)
        review_dao.find_by_id.assert_not_called()

    def test_not_found(
        self,
        service: AdminService,
        review_dao: Mock,
    ) -> None:
        """Unknown review propagates ReviewNotFoundError."""
        review_dao.delete.side_effect = ReviewNotFoundError(ID_REVIEW)

        with pytest.raises(ReviewNotFoundError):
            service.delete_review(ID_REVIEW)
