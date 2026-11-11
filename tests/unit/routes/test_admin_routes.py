"""Unit tests for the admin routes, with mocked dependencies."""

from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from src.api.deps import get_admin_service, get_user
from src.core.config import settings
from src.main import app
from src.models.admin import ModerationStatus
from src.models.users import User
from src.services.admin_service import AdminService
from src.utils.exceptions import (
    AdminModerationError,
    DAOError,
    ReviewNotFoundError,
    SelfModerationError,
    UserNotFoundError,
)

ADMIN_ID = 1
TARGET_ID = 2
ID_REVIEW = 7
DAYS = 7
SUSPEND_URL = f"{settings.API_STR}/admin/users/{TARGET_ID}/suspend"
BAN_URL = f"{settings.API_STR}/admin/users/{TARGET_ID}/ban"
REVIEW_URL = f"{settings.API_STR}/admin/reviews/{ID_REVIEW}"


def _user(*, is_admin: bool) -> User:
    return User(
        id_user=ADMIN_ID,
        username="boss",
        email="boss@ensai.fr",
        password_hash="hashed",
        is_admin=is_admin,
    )


@pytest.fixture
def mock_service() -> Mock:
    """Return a mocked AdminService."""
    return Mock(spec=AdminService)


def _client(mock_service: Mock, user: User) -> Generator[TestClient]:
    app.dependency_overrides[get_admin_service] = lambda: mock_service
    app.dependency_overrides[get_user] = lambda: user
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def client(mock_service: Mock) -> Generator[TestClient]:
    """TestClient authenticated as an admin."""
    yield from _client(mock_service, _user(is_admin=True))


@pytest.fixture
def non_admin_client(mock_service: Mock) -> Generator[TestClient]:
    """TestClient authenticated as a normal user."""
    yield from _client(mock_service, _user(is_admin=False))


class TestSuspendRoute:
    """Unit tests for POST /admin/users/{user_id}/suspend."""

    def test_success(self, client: TestClient, mock_service: Mock) -> None:
        """Admin gets 200 with the new status."""
        until = datetime.now(UTC) + timedelta(days=DAYS)
        mock_service.suspend_user.return_value = ModerationStatus(
            id_user=TARGET_ID,
            username="bob",
            is_banned=False,
            suspended_until=until,
        )

        response = client.post(SUSPEND_URL, json={"days": DAYS})

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["suspended_until"] is not None
        mock_service.suspend_user.assert_called_once_with(
            ADMIN_ID,
            TARGET_ID,
            DAYS,
        )

    @pytest.mark.parametrize("days", [0, 366])
    def test_invalid_days(
        self,
        client: TestClient,
        mock_service: Mock,
        days: int,
    ) -> None:
        """Duration outside 1-365 returns 422."""
        response = client.post(SUSPEND_URL, json={"days": days})

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        mock_service.suspend_user.assert_not_called()

    def test_not_admin(
        self,
        non_admin_client: TestClient,
        mock_service: Mock,
    ) -> None:
        """A normal user gets 403."""
        response = non_admin_client.post(SUSPEND_URL, json={"days": DAYS})

        assert response.status_code == status.HTTP_403_FORBIDDEN
        mock_service.suspend_user.assert_not_called()

    @pytest.mark.parametrize(
        ("error", "expected"),
        [
            (SelfModerationError(), status.HTTP_400_BAD_REQUEST),
            (AdminModerationError(), status.HTTP_403_FORBIDDEN),
            (UserNotFoundError(user_id=TARGET_ID), status.HTTP_404_NOT_FOUND),
            (DAOError(), status.HTTP_500_INTERNAL_SERVER_ERROR),
        ],
    )
    def test_errors(
        self,
        client: TestClient,
        mock_service: Mock,
        error: Exception,
        expected: int,
    ) -> None:
        """Service errors are translated into HTTP errors."""
        mock_service.suspend_user.side_effect = error

        response = client.post(SUSPEND_URL, json={"days": DAYS})

        assert response.status_code == expected


class TestBanRoute:
    """Unit tests for POST /admin/users/{user_id}/ban."""

    def test_success(self, client: TestClient, mock_service: Mock) -> None:
        """Admin gets 200 with is_banned true."""
        mock_service.ban_user.return_value = ModerationStatus(
            id_user=TARGET_ID,
            username="bob",
            is_banned=True,
        )

        response = client.post(BAN_URL)

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["is_banned"] is True
        mock_service.ban_user.assert_called_once_with(ADMIN_ID, TARGET_ID)

    def test_not_admin(
        self,
        non_admin_client: TestClient,
        mock_service: Mock,
    ) -> None:
        """A normal user gets 403."""
        response = non_admin_client.post(BAN_URL)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        mock_service.ban_user.assert_not_called()

    @pytest.mark.parametrize(
        ("error", "expected"),
        [
            (SelfModerationError(), status.HTTP_400_BAD_REQUEST),
            (AdminModerationError(), status.HTTP_403_FORBIDDEN),
            (UserNotFoundError(user_id=TARGET_ID), status.HTTP_404_NOT_FOUND),
            (DAOError(), status.HTTP_500_INTERNAL_SERVER_ERROR),
        ],
    )
    def test_errors(
        self,
        client: TestClient,
        mock_service: Mock,
        error: Exception,
        expected: int,
    ) -> None:
        """Service errors are translated into HTTP errors."""
        mock_service.ban_user.side_effect = error

        response = client.post(BAN_URL)

        assert response.status_code == expected


class TestModerateReviewRoute:
    """Unit tests for DELETE /admin/reviews/{review_id}."""

    def test_success(self, client: TestClient, mock_service: Mock) -> None:
        """Admin gets 204 with an empty body."""
        response = client.delete(REVIEW_URL)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not response.content
        mock_service.delete_review.assert_called_once_with(ID_REVIEW)

    def test_not_admin(
        self,
        non_admin_client: TestClient,
        mock_service: Mock,
    ) -> None:
        """A normal user gets 403."""
        response = non_admin_client.delete(REVIEW_URL)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        mock_service.delete_review.assert_not_called()

    def test_not_found(self, client: TestClient, mock_service: Mock) -> None:
        """Unknown review returns 404."""
        mock_service.delete_review.side_effect = ReviewNotFoundError(
            ID_REVIEW,
        )

        response = client.delete(REVIEW_URL)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_dao_error(self, client: TestClient, mock_service: Mock) -> None:
        """Database error returns 500."""
        mock_service.delete_review.side_effect = DAOError()

        response = client.delete(REVIEW_URL)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
