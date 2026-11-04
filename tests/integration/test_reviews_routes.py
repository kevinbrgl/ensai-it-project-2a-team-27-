"""Integration tests for the review routes.

The routes are called through FastAPI's TestClient, with the real database
from the .env file. The request cursor is replaced by the test cursor
(client fixture of conftest.py), so every change is rolled back afterwards.
"""

from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from psycopg2.extras import RealDictCursor

from src.core.config import settings

REGISTER_URL = f"{settings.API_STR}/auth/register"
LOGIN_URL = f"{settings.API_STR}/auth/login"
PASSWORD = "password123"
UNKNOWN_ID = 999_999_999
NB_REVIEWS = 2
NEW_RATING = 5


def _register_and_login(client: TestClient, prefix: str) -> dict[str, str]:
    """Create a temporary user, log in and return the auth headers."""
    uname = f"{prefix}_{uuid4().hex[:8]}"
    client.post(
        REGISTER_URL,
        json={
            "username": uname,
            "email": f"{uname}@ensai.fr",
            "password": PASSWORD,
        },
    )
    login_resp = client.post(
        LOGIN_URL,
        data={"username": uname, "password": PASSWORD},
    )
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers(client: TestClient) -> dict[str, str]:
    """Auth headers of a first test user (the author)."""
    return _register_and_login(client, "revuser")


@pytest.fixture
def other_auth_headers(client: TestClient) -> dict[str, str]:
    """Auth headers of a second test user."""
    return _register_and_login(client, "revother")


@pytest.fixture
def id_book(cursor: RealDictCursor) -> int:
    """Insert a test book in the database and return its ID."""
    cursor.execute(
        """
        INSERT INTO books (id_book_api, title)
        VALUES (%s, 'Test Book Reviews')
        RETURNING id_book
        """,
        (f"openlib_review_{uuid4().hex[:8]}",),
    )
    row = cursor.fetchone()
    assert row is not None
    return row["id_book"]


def _book_reviews_url(id_book: int) -> str:
    return f"{settings.API_STR}/books/{id_book}/reviews"


def _review_url(id_review: int) -> str:
    return f"{settings.API_STR}/reviews/{id_review}"


def _user_reviews_url(id_user: int) -> str:
    return f"{settings.API_STR}/users/{id_user}/reviews"


class TestReviewsScenario:
    """Full scenario: create, read, edit and delete reviews."""

    def test_full_scenario(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        other_auth_headers: dict[str, str],
        id_book: int,
    ) -> None:
        """Run every review endpoint with two different users."""
        url = _book_reviews_url(id_book)

        # 18: A and B review the same book
        resp_a = client.post(
            url,
            headers=auth_headers,
            json={"rating": 3, "comment": "Not bad"},
        )
        assert resp_a.status_code == status.HTTP_201_CREATED
        review_a = resp_a.json()

        resp_b = client.post(
            url,
            headers=other_auth_headers,
            json={"rating": 4},
        )
        assert resp_b.status_code == status.HTTP_201_CREATED

        # 18: A cannot review the same book twice
        resp = client.post(url, headers=auth_headers, json={"rating": 5})
        assert resp.status_code == status.HTTP_409_CONFLICT

        # 17: average of 3 and 4
        resp = client.get(url, headers=auth_headers)
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["average_rating"] == pytest.approx(3.5)
        assert data["review_count"] == NB_REVIEWS

        # 19: B cannot edit A's review, A can
        review_url = _review_url(review_a["id_review"])
        resp = client.put(
            review_url,
            headers=other_auth_headers,
            json={"rating": 1},
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

        resp = client.put(
            review_url,
            headers=auth_headers,
            json={"rating": NEW_RATING, "comment": "Finally great"},
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["rating"] == NEW_RATING

        # 21: A's reviews
        id_user_a = review_a["id_user"]
        resp = client.get(_user_reviews_url(id_user_a), headers=auth_headers)
        assert resp.status_code == status.HTTP_200_OK
        assert [r["id_review"] for r in resp.json()] == [
            review_a["id_review"],
        ]

        # 20: B cannot delete A's review, A can, only once
        resp = client.delete(review_url, headers=other_auth_headers)
        assert resp.status_code == status.HTTP_403_FORBIDDEN

        resp = client.delete(review_url, headers=auth_headers)
        assert resp.status_code == status.HTTP_204_NO_CONTENT

        resp = client.delete(review_url, headers=auth_headers)
        assert resp.status_code == status.HTTP_404_NOT_FOUND

        resp = client.get(_user_reviews_url(id_user_a), headers=auth_headers)
        assert resp.json() == []


class TestReviewsErrors:
    """Error cases that do not need a full scenario."""

    def test_get_reviews_unknown_book(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Unknown book returns 404."""
        resp = client.get(_book_reviews_url(UNKNOWN_ID), headers=auth_headers)
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_get_reviews_without_reviews(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        id_book: int,
    ) -> None:
        """Book without reviews: no average and an empty list."""
        resp = client.get(_book_reviews_url(id_book), headers=auth_headers)
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["average_rating"] is None
        assert data["review_count"] == 0
        assert data["reviews"] == []

    def test_create_review_unknown_book(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Reviewing an unknown book returns 404."""
        resp = client.post(
            _book_reviews_url(UNKNOWN_ID),
            headers=auth_headers,
            json={"rating": 4},
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_list_reviews_unknown_user(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Unknown user returns 404."""
        resp = client.get(_user_reviews_url(UNKNOWN_ID), headers=auth_headers)
        assert resp.status_code == status.HTTP_404_NOT_FOUND
