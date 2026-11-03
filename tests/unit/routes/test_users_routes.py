"""Unit tests for user routes.

Uses FastAPI TestClient with mocked dependencies.
No database or external network access is required.
"""

from collections.abc import Generator
from unittest.mock import Mock

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from src.api.deps import get_cursor, get_user, get_user_service
from src.core.config import settings
from src.main import app
from src.models.users import User
from src.services.users_service import UserService
from src.utils.exceptions import (
    AlreadyFollowingError,
    DAOError,
    NotFollowingError,
    SelfFollowError,
    SelfUnfollowError,
    UserNotFoundError,
)

USERS_URL = f"{settings.API_STR}/users"
PUBLIC_FIELDS = {"id_user", "username", "email", "bio", "profile_picture"}


@pytest.fixture
def mock_service() -> Mock:
    """Return a mocked UserService."""
    return Mock(spec=UserService)


@pytest.fixture
def fake_user() -> User:
    """Return a fake authenticated User."""
    return User(
        id_user=1,
        username="alice",
        email="alice@ensai.fr",
        password_hash="hashed_pw",
        bio="Passionnée de lecture",
        profile_picture="https://example.com/avatar.png",
    )


@pytest.fixture
def fake_matched_user() -> User:
    """Return a fake matching User for search results."""
    return User(
        id_user=2,
        username="alicia",
        email="alicia@ensai.fr",
        password_hash="hashed_pw_2",
        bio=None,
        profile_picture=None,
    )


@pytest.fixture
def client(
    mock_service: Mock,
    fake_user: User,
) -> Generator[TestClient]:
    """Yield a TestClient with service and auth dependencies overridden."""
    app.dependency_overrides[get_user_service] = lambda: mock_service
    app.dependency_overrides[get_user] = lambda: fake_user
    yield TestClient(app)
    app.dependency_overrides.clear()


class TestSearchUsersUnitRoute:
    """Unit tests for GET /api/users/search."""

    def test_search_users_success(
        self,
        client: TestClient,
        mock_service: Mock,
        fake_matched_user: User,
    ) -> None:
        """Successful search returns 200 with list of matching users."""
        mock_service.search_users.return_value = [fake_matched_user]

        response = client.get(
            f"{USERS_URL}/search",
            params={"username": "ali", "limit": 10},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["id_user"] == 2  # ruff: ignore[magic-value-comparison]
        assert data[0]["username"] == "alicia"
        assert set(data[0].keys()) == PUBLIC_FIELDS
        assert "password" not in data[0]
        assert "password_hash" not in data[0]
        mock_service.search_users.assert_called_once_with(
            username="ali",
            limit=10,
        )

    def test_search_users_empty_results(
        self,
        client: TestClient,
        mock_service: Mock,
    ) -> None:
        """Search with no matching users returns 200 and empty list."""
        mock_service.search_users.return_value = []

        response = client.get(
            f"{USERS_URL}/search",
            params={"username": "nobody"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    def test_search_users_missing_param_422(
        self,
        client: TestClient,
    ) -> None:
        """Missing username query parameter returns 422."""
        response = client.get(f"{USERS_URL}/search")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_search_users_empty_string_422(
        self,
        client: TestClient,
    ) -> None:
        """Empty username query parameter returns 422."""
        response = client.get(
            f"{USERS_URL}/search",
            params={"username": ""},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_search_users_dao_error_500(
        self,
        client: TestClient,
        mock_service: Mock,
    ) -> None:
        """DAOError during search returns 500."""
        mock_service.search_users.side_effect = DAOError("DB error")

        response = client.get(
            f"{USERS_URL}/search",
            params={"username": "error"},
        )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json()["detail"] == "Could not search users."

    def test_search_users_unauthenticated(
        self,
        mock_service: Mock,
    ) -> None:
        """Unauthenticated request is rejected with 401 or 403."""

        def dummy_cursor() -> Generator[Mock]:
            yield Mock()

        app.dependency_overrides[get_cursor] = dummy_cursor
        app.dependency_overrides[get_user_service] = lambda: mock_service
        try:
            unauth_client = TestClient(app)
            response = unauth_client.get(
                f"{USERS_URL}/search",
                params={"username": "ali"},
            )
            assert response.status_code in {
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
            }
        finally:
            app.dependency_overrides.clear()


class TestFollowUserUnitRoute:
    """Unit tests for POST /api/users/{user_id}/follow."""

    def test_follow_user_success_204(
        self,
        client: TestClient,
        mock_service: Mock,
    ) -> None:
        """Following another user returns 204 No Content."""
        mock_service.follow_user.return_value = None

        response = client.post(f"{USERS_URL}/2/follow")

        assert response.status_code == status.HTTP_204_NO_CONTENT
        mock_service.follow_user.assert_called_once_with(
            follower_id=1,
            following_id=2,
        )

    def test_follow_user_self_400(
        self,
        client: TestClient,
        mock_service: Mock,
    ) -> None:
        """Attempting to follow oneself returns 400 Bad Request."""
        mock_service.follow_user.side_effect = SelfFollowError

        response = client.post(f"{USERS_URL}/1/follow")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["detail"] == "Users cannot follow themselves."

    def test_follow_user_not_found_404(
        self,
        client: TestClient,
        mock_service: Mock,
    ) -> None:
        """Following a nonexistent user returns 404 Not Found."""
        mock_service.follow_user.side_effect = UserNotFoundError(user_id=999)

        response = client.post(f"{USERS_URL}/999/follow")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "User not found."

    def test_follow_user_already_following_409(
        self,
        client: TestClient,
        mock_service: Mock,
    ) -> None:
        """Following an already followed user returns 409 Conflict."""
        mock_service.follow_user.side_effect = AlreadyFollowingError

        response = client.post(f"{USERS_URL}/2/follow")

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.json()["detail"] == "Already following this user."

    def test_follow_user_dao_error_500(
        self,
        client: TestClient,
        mock_service: Mock,
    ) -> None:
        """DAOError during follow returns 500."""
        mock_service.follow_user.side_effect = DAOError("DB error")

        response = client.post(f"{USERS_URL}/2/follow")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json()["detail"] == "Could not follow user."

    def test_follow_user_unauthenticated(
        self,
        mock_service: Mock,
    ) -> None:
        """Unauthenticated request is rejected with 401 or 403."""

        def dummy_cursor() -> Generator[Mock]:
            yield Mock()

        app.dependency_overrides[get_cursor] = dummy_cursor
        app.dependency_overrides[get_user_service] = lambda: mock_service
        try:
            unauth_client = TestClient(app)
            response = unauth_client.post(f"{USERS_URL}/2/follow")
            assert response.status_code in {
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
            }
        finally:
            app.dependency_overrides.clear()


class TestUnfollowUserUnitRoute:
    """Unit tests for DELETE /users/{userId}/follow."""

    def test_unfollow_user_success_204(
        self,
        client: TestClient,
        mock_service: Mock,
    ) -> None:
        """Unfollowing an existing user returns 204 No Content."""
        mock_service.unfollow_user.return_value = None

        response = client.delete(f"{USERS_URL}/2/follow")

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not response.text
        mock_service.unfollow_user.assert_called_once_with(
            follower_id=1,
            following_id=2,
        )

    def test_unfollow_user_self_400(
        self,
        client: TestClient,
        mock_service: Mock,
    ) -> None:
        """Attempting to unfollow oneself returns 400 Bad Request."""
        mock_service.unfollow_user.side_effect = SelfUnfollowError

        response = client.delete(f"{USERS_URL}/1/follow")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["detail"] == "Users cannot unfollow themselves."

    def test_unfollow_user_not_found_404(
        self,
        client: TestClient,
        mock_service: Mock,
    ) -> None:
        """Unfollowing a nonexistent user returns 404 Not Found."""
        mock_service.unfollow_user.side_effect = UserNotFoundError(user_id=999)

        response = client.delete(f"{USERS_URL}/999/follow")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "User not found."

    def test_unfollow_user_not_following_404(
        self,
        client: TestClient,
        mock_service: Mock,
    ) -> None:
        """Unfollowing a user not followed returns 404 Not Found."""
        mock_service.unfollow_user.side_effect = NotFollowingError

        response = client.delete(f"{USERS_URL}/2/follow")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Not following this user."

    def test_unfollow_user_dao_error_500(
        self,
        client: TestClient,
        mock_service: Mock,
    ) -> None:
        """DAOError during unfollow returns 500."""
        mock_service.unfollow_user.side_effect = DAOError("DB error")

        response = client.delete(f"{USERS_URL}/2/follow")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json()["detail"] == "Could not unfollow user."

    def test_unfollow_user_unauthenticated(
        self,
        mock_service: Mock,
    ) -> None:
        """Unauthenticated request is rejected with 401 or 403."""

        def dummy_cursor() -> Generator[Mock]:
            yield Mock()

        app.dependency_overrides[get_cursor] = dummy_cursor
        app.dependency_overrides[get_user_service] = lambda: mock_service
        try:
            unauth_client = TestClient(app)
            response = unauth_client.delete(f"{USERS_URL}/2/follow")
            assert response.status_code in {
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
            }
        finally:
            app.dependency_overrides.clear()


class TestGetFollowersUnitRoute:
    """Unit tests for GET /users/{userId}/followers."""

    def test_get_followers_success_200(
        self,
        client: TestClient,
        mock_service: Mock,
    ) -> None:
        """Retrieving followers returns 200 with UserRead payload."""
        follower = User(
            id_user=2,
            username="bob",
            email="bob@ensai.fr",
            password_hash="secret_hash",
            bio="My bio",
            profile_picture="https://example.com/pic.png",
        )
        mock_service.get_followers.return_value = [follower]

        response = client.get(f"{USERS_URL}/1/followers")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["id_user"] == follower.id_user
        assert data[0]["username"] == "bob"
        assert data[0]["email"] == "bob@ensai.fr"
        assert "password_hash" not in data[0]
        assert set(data[0].keys()) == PUBLIC_FIELDS
        mock_service.get_followers.assert_called_once_with(1)

    def test_get_followers_empty_200(
        self,
        client: TestClient,
        mock_service: Mock,
    ) -> None:
        """User with no followers returns 200 with empty list."""
        mock_service.get_followers.return_value = []

        response = client.get(f"{USERS_URL}/1/followers")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []
        mock_service.get_followers.assert_called_once_with(1)

    def test_get_followers_not_found_404(
        self,
        client: TestClient,
        mock_service: Mock,
    ) -> None:
        """Retrieving followers of nonexistent user returns 404."""
        mock_service.get_followers.side_effect = UserNotFoundError(user_id=999)

        response = client.get(f"{USERS_URL}/999/followers")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "User not found."

    def test_get_followers_dao_error_500(
        self,
        client: TestClient,
        mock_service: Mock,
    ) -> None:
        """DAOError returns 500 Internal Server Error."""
        mock_service.get_followers.side_effect = DAOError("DB error")

        response = client.get(f"{USERS_URL}/1/followers")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json()["detail"] == "Could not retrieve followers."

    def test_get_followers_unauthenticated(
        self,
        mock_service: Mock,
    ) -> None:
        """Unauthenticated request is rejected with 401 or 403."""

        def dummy_cursor() -> Generator[Mock]:
            yield Mock()

        app.dependency_overrides[get_cursor] = dummy_cursor
        app.dependency_overrides[get_user_service] = lambda: mock_service
        try:
            unauth_client = TestClient(app)
            response = unauth_client.get(f"{USERS_URL}/1/followers")
            assert response.status_code in {
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
            }
        finally:
            app.dependency_overrides.clear()


class TestGetFollowingUnitRoute:
    """Unit tests for GET /users/{userId}/following."""

    def test_get_following_success_200(
        self,
        client: TestClient,
        mock_service: Mock,
    ) -> None:
        """Retrieving followed users returns 200 with UserRead payload."""
        followed = User(
            id_user=2,
            username="bob",
            email="bob@ensai.fr",
            password_hash="secret_hash",
            bio="My bio",
            profile_picture="https://example.com/pic.png",
        )
        mock_service.get_following.return_value = [followed]

        response = client.get(f"{USERS_URL}/1/following")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["id_user"] == followed.id_user
        assert data[0]["username"] == "bob"
        assert data[0]["email"] == "bob@ensai.fr"
        assert "password_hash" not in data[0]
        assert set(data[0].keys()) == PUBLIC_FIELDS
        mock_service.get_following.assert_called_once_with(1)

    def test_get_following_empty_200(
        self,
        client: TestClient,
        mock_service: Mock,
    ) -> None:
        """User following nobody returns 200 with empty list."""
        mock_service.get_following.return_value = []

        response = client.get(f"{USERS_URL}/1/following")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []
        mock_service.get_following.assert_called_once_with(1)

    def test_get_following_not_found_404(
        self,
        client: TestClient,
        mock_service: Mock,
    ) -> None:
        """Retrieving following of nonexistent user returns 404."""
        mock_service.get_following.side_effect = UserNotFoundError(user_id=999)

        response = client.get(f"{USERS_URL}/999/following")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "User not found."

    def test_get_following_dao_error_500(
        self,
        client: TestClient,
        mock_service: Mock,
    ) -> None:
        """DAOError returns 500 Internal Server Error."""
        mock_service.get_following.side_effect = DAOError("DB error")

        response = client.get(f"{USERS_URL}/1/following")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert (
            response.json()["detail"] == "Could not retrieve followed users."
        )

    def test_get_following_unauthenticated(
        self,
        mock_service: Mock,
    ) -> None:
        """Unauthenticated request is rejected with 401 or 403."""

        def dummy_cursor() -> Generator[Mock]:
            yield Mock()

        app.dependency_overrides[get_cursor] = dummy_cursor
        app.dependency_overrides[get_user_service] = lambda: mock_service
        try:
            unauth_client = TestClient(app)
            response = unauth_client.get(f"{USERS_URL}/1/following")
            assert response.status_code in {
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
            }
        finally:
            app.dependency_overrides.clear()
