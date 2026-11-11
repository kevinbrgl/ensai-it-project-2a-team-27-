"""Integration tests for the admin routes (real database, rolled back)."""

from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from psycopg2.extras import RealDictCursor

from src.core.config import settings

API = settings.API_STR
REGISTER_URL = f"{API}/auth/register"
LOGIN_URL = f"{API}/auth/login"
ME_URL = f"{API}/users/me"
PASSWORD = "password123"
UNKNOWN_ID = 999_999_999

Account = tuple[dict[str, str], int, str]


def _create_account(client: TestClient, prefix: str) -> Account:
    """Register and log in a user; return (headers, id_user, username)."""
    uname = f"{prefix}_{uuid4().hex[:8]}"
    client.post(
        REGISTER_URL,
        json={
            "username": uname,
            "email": f"{uname}@ensai.fr",
            "password": PASSWORD,
        },
    )
    token = client.post(
        LOGIN_URL,
        data={"username": uname, "password": PASSWORD},
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    id_user = client.get(ME_URL, headers=headers).json()["id_user"]
    return headers, id_user, uname


def _make_admin(cursor: RealDictCursor, id_user: int) -> None:
    cursor.execute(
        "UPDATE users SET is_admin = TRUE WHERE id_user = %s",
        (id_user,),
    )


def _login(client: TestClient, username: str) -> int:
    return client.post(
        LOGIN_URL,
        data={"username": username, "password": PASSWORD},
    ).status_code


@pytest.fixture
def admin(client: TestClient, cursor: RealDictCursor) -> Account:
    """Create an administrator account."""
    account = _create_account(client, "admin")
    _make_admin(cursor, account[1])
    return account


@pytest.fixture
def target(client: TestClient) -> Account:
    """Create a normal account to moderate."""
    return _create_account(client, "target")


class TestSuspend:
    """POST /admin/users/{user_id}/suspend."""

    def test_suspended_user_is_locked_out(
        self,
        client: TestClient,
        admin: Account,
        target: Account,
    ) -> None:
        """After a suspension, the old token and the login are refused."""
        target_headers, target_id, target_name = target

        response = client.post(
            f"{API}/admin/users/{target_id}/suspend",
            headers=admin[0],
            json={"days": 3},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["suspended_until"] is not None

        me = client.get(ME_URL, headers=target_headers)
        assert me.status_code == status.HTTP_403_FORBIDDEN
        assert me.json()["detail"].startswith("This account is suspended")
        assert _login(client, target_name) == status.HTTP_403_FORBIDDEN

    def test_non_admin_forbidden(
        self,
        client: TestClient,
        target: Account,
    ) -> None:
        """A normal user cannot suspend anyone."""
        other_headers, _, _ = _create_account(client, "other")

        response = client.post(
            f"{API}/admin/users/{target[1]}/suspend",
            headers=other_headers,
            json={"days": 3},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_self(self, client: TestClient, admin: Account) -> None:
        """An admin cannot suspend themself."""
        response = client.post(
            f"{API}/admin/users/{admin[1]}/suspend",
            headers=admin[0],
            json={"days": 3},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_unknown_user(self, client: TestClient, admin: Account) -> None:
        """Unknown user returns 404."""
        response = client.post(
            f"{API}/admin/users/{UNKNOWN_ID}/suspend",
            headers=admin[0],
            json={"days": 3},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestBan:
    """POST /admin/users/{user_id}/ban."""

    def test_banned_user_is_locked_out(
        self,
        client: TestClient,
        admin: Account,
        target: Account,
    ) -> None:
        """After a ban, the old token and the login are refused."""
        target_headers, target_id, target_name = target

        response = client.post(
            f"{API}/admin/users/{target_id}/ban",
            headers=admin[0],
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["is_banned"] is True
        me = client.get(ME_URL, headers=target_headers)
        assert me.status_code == status.HTTP_403_FORBIDDEN
        assert me.json()["detail"] == "This account has been banned."
        assert _login(client, target_name) == status.HTTP_403_FORBIDDEN

    def test_cannot_ban_admin(
        self,
        client: TestClient,
        cursor: RealDictCursor,
        admin: Account,
        target: Account,
    ) -> None:
        """An admin cannot ban another admin."""
        _make_admin(cursor, target[1])

        response = client.post(
            f"{API}/admin/users/{target[1]}/ban",
            headers=admin[0],
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestModerateReview:
    """DELETE /admin/reviews/{review_id}."""

    def test_admin_removes_any_review(
        self,
        client: TestClient,
        cursor: RealDictCursor,
        admin: Account,
        target: Account,
    ) -> None:
        """An admin deletes a review written by someone else."""
        cursor.execute(
            """
            INSERT INTO books (id_book_api, title)
            VALUES (%s, 'Moderated Book')
            RETURNING id_book
            """,
            (f"openlib_mod_{uuid4().hex[:8]}",),
        )
        row = cursor.fetchone()
        assert row is not None
        id_book = row["id_book"]
        created = client.post(
            f"{API}/books/{id_book}/reviews",
            headers=target[0],
            json={"rating": 1, "comment": "spam"},
        )
        id_review = created.json()["id_review"]

        response = client.delete(
            f"{API}/admin/reviews/{id_review}",
            headers=admin[0],
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        reviews = client.get(
            f"{API}/books/{id_book}/reviews",
            headers=admin[0],
        ).json()
        assert reviews["review_count"] == 0

    def test_unknown_review(self, client: TestClient, admin: Account) -> None:
        """Unknown review returns 404."""
        response = client.delete(
            f"{API}/admin/reviews/{UNKNOWN_ID}",
            headers=admin[0],
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_non_admin_forbidden(
        self,
        client: TestClient,
        target: Account,
    ) -> None:
        """A normal user gets 403."""
        response = client.delete(
            f"{API}/admin/reviews/{UNKNOWN_ID}",
            headers=target[0],
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
