"""Integration tests for the routes showing another user's data.

Covers GET /api/users/{user_id}/library and GET /api/users/{user_id}/playlists.
The routes are called through FastAPI's TestClient (fixture "client" from
conftest.py), with the real database from the .env file. Every change made
during a test is rolled back afterwards.
"""

from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from src.core.config import settings
from src.dao.books_dao import BookDAO
from src.models.books import BookCreate

USERS_URL = f"{settings.API_STR}/users"
REGISTER_URL = f"{settings.API_STR}/auth/register"
LOGIN_URL = f"{settings.API_STR}/auth/login"
LIBRARY_BOOKS_URL = f"{settings.API_STR}/library/books"
PLAYLISTS_URL = f"{settings.API_STR}/playlists"
PASSWORD = "motdepasse123"
UNKNOWN_ID = 999999999


def register_and_login(
    client: TestClient,
    prefix: str,
) -> tuple[dict[str, str], int]:
    """Register and log in a new user.

    :param client: Test client
    :param prefix: Beginning of the username (a random suffix is added)
    :return: The user's auth headers and ID
    """
    name = f"{prefix}_{uuid4().hex[:8]}"
    registered = client.post(
        REGISTER_URL,
        json={
            "username": name,
            "email": f"{name}@ensai.fr",
            "password": PASSWORD,
        },
    )
    assert registered.status_code == status.HTTP_201_CREATED
    response = client.post(
        LOGIN_URL,
        data={"username": name, "password": PASSWORD},
    )
    assert response.status_code == status.HTTP_200_OK
    headers = {"Authorization": f"Bearer {response.json()['access_token']}"}
    return headers, registered.json()["id_user"]


@pytest.fixture
def me(client: TestClient) -> tuple[dict[str, str], int]:
    """Return the auth headers and ID of the user making the requests."""
    return register_and_login(client, "viewer")


@pytest.fixture
def friend(client: TestClient) -> tuple[dict[str, str], int]:
    """Return the auth headers and ID of the user whose data is viewed."""
    return register_and_login(client, "friend")


class TestGetUserLibraryRoute:
    """Integration tests for GET /api/users/{user_id}/library."""

    def test_view_library(
        self,
        client: TestClient,
        book_dao: BookDAO,
        me: tuple[dict[str, str], int],
        friend: tuple[dict[str, str], int],
    ) -> None:
        """I can see the books of another user's library."""
        friend_headers, friend_id = friend
        id_dune = book_dao.create(BookCreate(title="Dune")).id_book
        id_anna = book_dao.create(BookCreate(title="Anna Karenine")).id_book
        for id_book, state in ((id_dune, "READING"), (id_anna, "COMPLETED")):
            client.post(
                LIBRARY_BOOKS_URL,
                headers=friend_headers,
                json={"id_book": id_book, "state": state},
            )

        response = client.get(
            f"{USERS_URL}/{friend_id}/library",
            headers=me[0],
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert {book["id_book"] for book in data} == {id_dune, id_anna}
        assert all(book["id_user"] == friend_id for book in data)

    def test_filter_by_status(
        self,
        client: TestClient,
        book_dao: BookDAO,
        me: tuple[dict[str, str], int],
        friend: tuple[dict[str, str], int],
    ) -> None:
        """The optional status filter works on another user's library."""
        friend_headers, friend_id = friend
        id_dune = book_dao.create(BookCreate(title="Dune")).id_book
        id_anna = book_dao.create(BookCreate(title="Anna Karenine")).id_book
        for id_book, state in ((id_dune, "READING"), (id_anna, "COMPLETED")):
            client.post(
                LIBRARY_BOOKS_URL,
                headers=friend_headers,
                json={"id_book": id_book, "state": state},
            )

        response = client.get(
            f"{USERS_URL}/{friend_id}/library",
            headers=me[0],
            params={"status": "COMPLETED"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert [book["id_book"] for book in response.json()] == [id_anna]

    def test_empty_library(
        self,
        client: TestClient,
        me: tuple[dict[str, str], int],
        friend: tuple[dict[str, str], int],
    ) -> None:
        """A user without books: 200 OK and an empty list."""
        response = client.get(
            f"{USERS_URL}/{friend[1]}/library",
            headers=me[0],
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    def test_does_not_show_my_books(
        self,
        client: TestClient,
        book_dao: BookDAO,
        me: tuple[dict[str, str], int],
        friend: tuple[dict[str, str], int],
    ) -> None:
        """The books of the user making the request are not listed."""
        my_headers, _ = me
        id_dune = book_dao.create(BookCreate(title="Dune")).id_book
        client.post(
            LIBRARY_BOOKS_URL,
            headers=my_headers,
            json={"id_book": id_dune, "state": "READING"},
        )

        response = client.get(
            f"{USERS_URL}/{friend[1]}/library",
            headers=my_headers,
        )

        assert response.json() == []

    def test_invalid_status(
        self,
        client: TestClient,
        me: tuple[dict[str, str], int],
        friend: tuple[dict[str, str], int],
    ) -> None:
        """Unknown status value: 422 (validation error)."""
        response = client.get(
            f"{USERS_URL}/{friend[1]}/library",
            headers=me[0],
            params={"status": "FINISHED"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_user_not_found(
        self,
        client: TestClient,
        me: tuple[dict[str, str], int],
    ) -> None:
        """Unknown user: 404 Not Found."""
        response = client.get(
            f"{USERS_URL}/{UNKNOWN_ID}/library",
            headers=me[0],
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_unauthorized(
        self,
        client: TestClient,
        friend: tuple[dict[str, str], int],
    ) -> None:
        """Missing token: 401 Unauthorized."""
        response = client.get(f"{USERS_URL}/{friend[1]}/library")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestGetUserPlaylistsRoute:
    """Integration tests for GET /api/users/{user_id}/playlists."""

    def test_view_playlists(
        self,
        client: TestClient,
        me: tuple[dict[str, str], int],
        friend: tuple[dict[str, str], int],
    ) -> None:
        """I can see another user's playlists, in creation order."""
        friend_headers, friend_id = friend
        for name in ("Romans", "Polars"):
            client.post(
                PLAYLISTS_URL,
                headers=friend_headers,
                json={"name": name},
            )

        response = client.get(
            f"{USERS_URL}/{friend_id}/playlists",
            headers=me[0],
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert [p["name"] for p in data] == ["Romans", "Polars"]
        assert all(p["id_user"] == friend_id for p in data)

    def test_empty_playlists(
        self,
        client: TestClient,
        me: tuple[dict[str, str], int],
        friend: tuple[dict[str, str], int],
    ) -> None:
        """A user without playlists: 200 OK and an empty list."""
        response = client.get(
            f"{USERS_URL}/{friend[1]}/playlists",
            headers=me[0],
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    def test_does_not_show_my_playlists(
        self,
        client: TestClient,
        me: tuple[dict[str, str], int],
        friend: tuple[dict[str, str], int],
    ) -> None:
        """The playlists of the user making the request are not listed."""
        my_headers, _ = me
        client.post(PLAYLISTS_URL, headers=my_headers, json={"name": "Polars"})

        response = client.get(
            f"{USERS_URL}/{friend[1]}/playlists",
            headers=my_headers,
        )

        assert response.json() == []

    def test_user_not_found(
        self,
        client: TestClient,
        me: tuple[dict[str, str], int],
    ) -> None:
        """Unknown user: 404 Not Found."""
        response = client.get(
            f"{USERS_URL}/{UNKNOWN_ID}/playlists",
            headers=me[0],
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_unauthorized(
        self,
        client: TestClient,
        friend: tuple[dict[str, str], int],
    ) -> None:
        """Missing token: 401 Unauthorized."""
        response = client.get(f"{USERS_URL}/{friend[1]}/playlists")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
