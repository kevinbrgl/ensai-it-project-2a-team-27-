"""Integration tests for the user routes.

The routes are called through FastAPI's TestClient (fixture "client" from
conftest.py), with the real database from the .env file. Every change made
during a test is rolled back afterwards.
"""

from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from src.core.config import settings
from src.services.users_service import UserService
from src.utils.exceptions import DAOError

REGISTER_URL = f"{settings.API_STR}/auth/register"
LOGIN_URL = f"{settings.API_STR}/auth/login"
ME_URL = f"{settings.API_STR}/users/me"
SEARCH_URL = f"{settings.API_STR}/users/search"
USERS_URL = f"{settings.API_STR}/users"
PASSWORD_URL = f"{settings.API_STR}/users/me/password"
PASSWORD = "motdepasse123"
NEW_PASSWORD = "nouveaumdp456"
PUBLIC_FIELDS = {"id_user", "username", "email", "bio", "profile_picture"}


@pytest.fixture
def username(client: TestClient) -> str:
    """Register a new user through the API and return its username.

    A random suffix avoids conflicts with users already in the database.
    """
    name = f"me_{uuid4().hex[:8]}"
    response = client.post(
        REGISTER_URL,
        json={
            "username": name,
            "email": f"{name}@ensai.fr",
            "password": PASSWORD,
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    return name


@pytest.fixture
def auth_headers(client: TestClient, username: str) -> dict[str, str]:
    """Log the user in and return the header that carries its token.

    Reused by every test of a protected route (GET, PATCH, PUT).
    """
    response = client.post(
        LOGIN_URL,
        data={"username": username, "password": PASSWORD},
    )
    assert response.status_code == status.HTTP_200_OK
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def other_username(client: TestClient) -> str:
    """Register a second user, to test conflicts on username and email."""
    name = f"other_{uuid4().hex[:8]}"
    response = client.post(
        REGISTER_URL,
        json={
            "username": name,
            "email": f"{name}@ensai.fr",
            "password": PASSWORD,
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    return name


class TestReadSelf:
    """Integration tests for GET /api/users/me."""

    def test_valid(
        self,
        client: TestClient,
        username: str,
        auth_headers: dict[str, str],
    ) -> None:
        """Valid token: 200 with the logged-in user's profile."""
        response = client.get(ME_URL, headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["username"] == username
        assert body["email"] == f"{username}@ensai.fr"
        assert body["bio"] is None
        assert body["profile_picture"] is None

    def test_only_public_fields(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """The response holds the public fields only, never the password."""
        body = client.get(ME_URL, headers=auth_headers).json()

        assert set(body) == PUBLIC_FIELDS
        assert "password_hash" not in body

    def test_no_token(self, client: TestClient) -> None:
        """No token: 401."""
        response = client.get(ME_URL)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_invalid_token(self, client: TestClient) -> None:
        """Invented token: 403."""
        response = client.get(
            ME_URL,
            headers={"Authorization": "Bearer not-a-real-token"},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestSearchUsersRoute:
    """Integration tests for GET /api/users/search."""

    def test_search_unauthenticated(self, client: TestClient) -> None:
        """Route requires authentication: 401 without token."""
        response = client.get(SEARCH_URL, params={"username": "alice"})
        assert response.status_code in {
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        }

    def test_search_missing_username(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Missing username query param returns 422."""
        response = client.get(SEARCH_URL, headers=auth_headers)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_search_empty_username(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Empty username query param returns 422."""
        response = client.get(
            SEARCH_URL,
            params={"username": ""},
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_search_success(
        self,
        client: TestClient,
        username: str,
        auth_headers: dict[str, str],
    ) -> None:
        """Search returns 200 and a list of matching users."""
        response = client.get(
            SEARCH_URL,
            params={"username": username},
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        found = next((u for u in data if u["username"] == username), None)
        assert found is not None
        assert set(found.keys()) == PUBLIC_FIELDS
        assert "password" not in found
        assert "password_hash" not in found

    def test_search_no_results(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Searching for an unknown username returns an empty list."""
        response = client.get(
            SEARCH_URL,
            params={"username": "nonexistent_reader_xyz"},
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    def test_search_database_error(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        mocker: MockerFixture,
    ) -> None:
        """Database error in DAO returns 500."""
        mocker.patch.object(
            UserService,
            "search_users",
            side_effect=DAOError("Database error"),
        )
        response = client.get(
            SEARCH_URL,
            params={"username": "alice"},
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json()["detail"] == "Could not search users."


class TestFollowUserRoute:
    """Integration tests for POST /api/users/{user_id}/follow."""

    def test_follow_user_success(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        other_username: str,
    ) -> None:
        """Following another user returns 204."""
        search_res = client.get(
            SEARCH_URL,
            params={"username": other_username},
            headers=auth_headers,
        )
        assert search_res.status_code == status.HTTP_200_OK
        target_id = search_res.json()[0]["id_user"]

        response = client.post(
            f"{USERS_URL}/{target_id}/follow",
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_follow_user_self_rejected(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Following oneself returns 400 Bad Request."""
        me_res = client.get(ME_URL, headers=auth_headers)
        my_id = me_res.json()["id_user"]

        response = client.post(
            f"{USERS_URL}/{my_id}/follow",
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["detail"] == "Users cannot follow themselves."

    def test_follow_user_not_found(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Following a nonexistent user returns 404 Not Found."""
        response = client.post(
            f"{USERS_URL}/999999999/follow",
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "User not found."

    def test_follow_user_already_following(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        other_username: str,
    ) -> None:
        """Following the same user twice returns 409 Conflict."""
        search_res = client.get(
            SEARCH_URL,
            params={"username": other_username},
            headers=auth_headers,
        )
        target_id = search_res.json()[0]["id_user"]

        resp1 = client.post(
            f"{USERS_URL}/{target_id}/follow",
            headers=auth_headers,
        )
        assert resp1.status_code == status.HTTP_204_NO_CONTENT

        resp2 = client.post(
            f"{USERS_URL}/{target_id}/follow",
            headers=auth_headers,
        )
        assert resp2.status_code == status.HTTP_409_CONFLICT
        assert resp2.json()["detail"] == "Already following this user."

    def test_follow_user_unauthenticated(
        self,
        client: TestClient,
    ) -> None:
        """Unauthenticated follow request returns 401."""
        response = client.post(f"{USERS_URL}/2/follow")
        assert response.status_code in {
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        }


class TestUnfollowUserRoute:
    """Integration tests for DELETE /api/users/{user_id}/follow."""

    def test_unfollow_user_success(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        other_username: str,
    ) -> None:
        """Unfollowing a followed user returns 204."""
        search_res = client.get(
            SEARCH_URL,
            params={"username": other_username},
            headers=auth_headers,
        )
        assert search_res.status_code == status.HTTP_200_OK
        target_id = search_res.json()[0]["id_user"]

        follow_res = client.post(
            f"{USERS_URL}/{target_id}/follow",
            headers=auth_headers,
        )
        assert follow_res.status_code == status.HTTP_204_NO_CONTENT

        response = client.delete(
            f"{USERS_URL}/{target_id}/follow",
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_unfollow_user_self_rejected(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Unfollowing oneself returns 400 Bad Request."""
        me_res = client.get(ME_URL, headers=auth_headers)
        my_id = me_res.json()["id_user"]

        response = client.delete(
            f"{USERS_URL}/{my_id}/follow",
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["detail"] == "Users cannot unfollow themselves."

    def test_unfollow_user_not_found(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Unfollowing a nonexistent user returns 404 Not Found."""
        response = client.delete(
            f"{USERS_URL}/999999999/follow",
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "User not found."

    def test_unfollow_user_not_following(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        other_username: str,
    ) -> None:
        """Unfollowing a user that is not followed returns 404 Not Found."""
        search_res = client.get(
            SEARCH_URL,
            params={"username": other_username},
            headers=auth_headers,
        )
        target_id = search_res.json()[0]["id_user"]

        response = client.delete(
            f"{USERS_URL}/{target_id}/follow",
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Not following this user."

    def test_unfollow_user_unauthenticated(
        self,
        client: TestClient,
    ) -> None:
        """Unauthenticated unfollow request returns 401."""
        response = client.delete(f"{USERS_URL}/2/follow")
        assert response.status_code in {
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        }


class TestGetFollowersRoute:
    """Integration tests for GET /api/users/{user_id}/followers."""

    def test_get_followers_success(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        other_username: str,
    ) -> None:
        """Retrieving followers returns 200 with list of follower users."""
        search_res = client.get(
            SEARCH_URL,
            params={"username": other_username},
            headers=auth_headers,
        )
        assert search_res.status_code == status.HTTP_200_OK
        target_id = search_res.json()[0]["id_user"]

        follow_res = client.post(
            f"{USERS_URL}/{target_id}/follow",
            headers=auth_headers,
        )
        assert follow_res.status_code == status.HTTP_204_NO_CONTENT

        response = client.get(
            f"{USERS_URL}/{target_id}/followers",
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        followers = response.json()
        assert len(followers) >= 1
        follower_usernames = [f["username"] for f in followers]
        me_res = client.get(ME_URL, headers=auth_headers)
        my_username = me_res.json()["username"]
        assert my_username in follower_usernames
        assert "password_hash" not in followers[0]

    def test_get_followers_empty(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        other_username: str,
    ) -> None:
        """User with no followers returns 200 with empty list."""
        search_res = client.get(
            SEARCH_URL,
            params={"username": other_username},
            headers=auth_headers,
        )
        assert search_res.status_code == status.HTTP_200_OK
        target_id = search_res.json()[0]["id_user"]

        response = client.get(
            f"{USERS_URL}/{target_id}/followers",
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    def test_get_followers_not_found(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Retrieving followers for nonexistent user returns 404."""
        response = client.get(
            f"{USERS_URL}/999999999/followers",
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "User not found."

    def test_get_followers_unauthenticated(
        self,
        client: TestClient,
    ) -> None:
        """Unauthenticated request returns 401."""
        response = client.get(f"{USERS_URL}/2/followers")
        assert response.status_code in {
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        }


class TestUpdateSelf:
    """Integration tests for PATCH /api/users/me."""

    def test_update_bio(
        self,
        client: TestClient,
        username: str,
        auth_headers: dict[str, str],
    ) -> None:
        """Only the bio is sent: it changes, the other fields stay."""
        response = client.patch(
            ME_URL,
            headers=auth_headers,
            json={"bio": "Fan de romans policiers"},
        )

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["bio"] == "Fan de romans policiers"
        assert body["username"] == username
        assert body["email"] == f"{username}@ensai.fr"

    def test_update_is_saved(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """The change is saved: GET /users/me returns the new value."""
        client.patch(
            ME_URL,
            headers=auth_headers,
            json={"bio": "Nouvelle bio"},
        )

        response = client.get(ME_URL, headers=auth_headers)

        assert response.json()["bio"] == "Nouvelle bio"

    def test_update_username(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """A free username can be taken."""
        new_name = f"new_{uuid4().hex[:8]}"

        response = client.patch(
            ME_URL,
            headers=auth_headers,
            json={"username": new_name},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["username"] == new_name

    def test_username_already_taken(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        other_username: str,
    ) -> None:
        """Username of another user: 409."""
        response = client.patch(
            ME_URL,
            headers=auth_headers,
            json={"username": other_username},
        )

        assert response.status_code == status.HTTP_409_CONFLICT

    def test_email_already_taken(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        other_username: str,
    ) -> None:
        """Email of another user: 409."""
        response = client.patch(
            ME_URL,
            headers=auth_headers,
            json={"email": f"{other_username}@ensai.fr"},
        )

        assert response.status_code == status.HTTP_409_CONFLICT

    def test_invalid_email(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Badly formatted email: 422 (validation error)."""
        response = client.patch(
            ME_URL,
            headers=auth_headers,
            json={"email": "pas-un-email"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_username_too_short(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Username shorter than 3 characters: 422 (validation error)."""
        response = client.patch(
            ME_URL,
            headers=auth_headers,
            json={"username": "ab"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_no_token(self, client: TestClient) -> None:
        """No token: 401."""
        response = client.patch(ME_URL, json={"bio": "Pirate"})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_empty_body(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Nothing to update: 400."""
        response = client.patch(ME_URL, headers=auth_headers, json={})

        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestUpdatePassword:
    """Integration tests for PUT /api/users/me/password."""

    def test_change_password(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Right current password and a new one: 200, public fields only."""
        response = client.put(
            PASSWORD_URL,
            headers=auth_headers,
            json={
                "current_password": PASSWORD,
                "new_password": NEW_PASSWORD,
            },
        )

        assert response.status_code == status.HTTP_200_OK
        assert set(response.json()) == PUBLIC_FIELDS

    def test_login_with_new_password(
        self,
        client: TestClient,
        username: str,
        auth_headers: dict[str, str],
    ) -> None:
        """After the change, the new password opens a session."""
        client.put(
            PASSWORD_URL,
            headers=auth_headers,
            json={
                "current_password": PASSWORD,
                "new_password": NEW_PASSWORD,
            },
        )

        response = client.post(
            LOGIN_URL,
            data={"username": username, "password": NEW_PASSWORD},
        )

        assert response.status_code == status.HTTP_200_OK

    def test_old_password_rejected(
        self,
        client: TestClient,
        username: str,
        auth_headers: dict[str, str],
    ) -> None:
        """After the change, the old password no longer works."""
        client.put(
            PASSWORD_URL,
            headers=auth_headers,
            json={
                "current_password": PASSWORD,
                "new_password": NEW_PASSWORD,
            },
        )

        response = client.post(
            LOGIN_URL,
            data={"username": username, "password": PASSWORD},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_wrong_current_password(
        self,
        client: TestClient,
        username: str,
        auth_headers: dict[str, str],
    ) -> None:
        """Wrong current password: 403, and the password is not changed."""
        response = client.put(
            PASSWORD_URL,
            headers=auth_headers,
            json={
                "current_password": "mauvaismdp123",
                "new_password": NEW_PASSWORD,
            },
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        login = client.post(
            LOGIN_URL,
            data={"username": username, "password": PASSWORD},
        )
        assert login.status_code == status.HTTP_200_OK

    def test_same_password(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """New password identical to the current one: 400."""
        response = client.put(
            PASSWORD_URL,
            headers=auth_headers,
            json={
                "current_password": PASSWORD,
                "new_password": PASSWORD,
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_new_password_too_short(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """New password shorter than 8 characters: 422 (validation error)."""
        response = client.put(
            PASSWORD_URL,
            headers=auth_headers,
            json={
                "current_password": PASSWORD,
                "new_password": "court",
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_no_token(self, client: TestClient) -> None:
        """No token: 401."""
        response = client.put(
            PASSWORD_URL,
            json={
                "current_password": PASSWORD,
                "new_password": NEW_PASSWORD,
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
