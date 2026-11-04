"""Integration tests for the playlist routes.

The routes are called through FastAPI's TestClient (fixture "client" from
conftest.py), with the real database from the .env file. Every change made
during a test is rolled back afterwards.
"""

from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from psycopg2.extras import RealDictCursor

from src.core.config import settings

PLAYLISTS_URL = f"{settings.API_STR}/playlists"
REGISTER_URL = f"{settings.API_STR}/auth/register"
LOGIN_URL = f"{settings.API_STR}/auth/login"
ME_URL = f"{settings.API_STR}/users/me"
PASSWORD = "motdepasse123"
MAX_NAME_LENGTH = 100


def login_new_user(client: TestClient, prefix: str) -> dict[str, str]:
    """Register and log in a new user, then return its auth headers.

    :param client: Test client
    :param prefix: Beginning of the username (a random suffix is added)
    :return: The header that carries the user's token
    """
    name = f"{prefix}_{uuid4().hex[:8]}"
    client.post(
        REGISTER_URL,
        json={
            "username": name,
            "email": f"{name}@ensai.fr",
            "password": PASSWORD,
        },
    )
    response = client.post(
        LOGIN_URL,
        data={"username": name, "password": PASSWORD},
    )
    assert response.status_code == status.HTTP_200_OK
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_playlist(
    client: TestClient,
    headers: dict[str, str],
    name: str,
) -> int:
    """Create a playlist through the API and return its ID.

    :param client: Test client
    :param headers: Auth headers of the owner
    :param name: Name of the playlist
    :return: ID of the created playlist
    """
    response = client.post(PLAYLISTS_URL, headers=headers, json={"name": name})
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()["id_playlist"]


def create_book(cursor: RealDictCursor, title: str) -> int:
    """Insert a test book with a unique API ID and return its ID.

    :param cursor: Test cursor
    :param title: Title of the book
    :return: ID of the created book
    """
    cursor.execute(
        """
        INSERT INTO books (id_book_api, title)
        VALUES (%s, %s)
        RETURNING id_book
        """,
        (f"test_{uuid4().hex[:8]}", title),
    )
    row = cursor.fetchone()
    assert row is not None
    return row["id_book"]


@pytest.fixture
def auth_headers(client: TestClient) -> dict[str, str]:
    """Return the auth headers of a new logged-in user."""
    return login_new_user(client, "pluser")


@pytest.fixture
def other_auth_headers(client: TestClient) -> dict[str, str]:
    """Return the auth headers of a second logged-in user."""
    return login_new_user(client, "plother")


@pytest.fixture
def id_book(cursor: RealDictCursor) -> int:
    """Insert a test book in the database and return its ID."""
    return create_book(cursor, "Dune")


class TestCreatePlaylistRoute:
    """Integration tests for POST /api/playlists."""

    def test_create_success(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Valid name: 201 Created, owned by the logged-in user."""
        response = client.post(
            PLAYLISTS_URL,
            headers=auth_headers,
            json={"name": "Polars"},
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "Polars"
        assert data["id_playlist"] > 0
        me = client.get(ME_URL, headers=auth_headers).json()
        assert data["id_user"] == me["id_user"]

    def test_duplicate_name(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Same name twice for the same user: 409 Conflict."""
        client.post(
            PLAYLISTS_URL,
            headers=auth_headers,
            json={"name": "Polars"},
        )

        response = client.post(
            PLAYLISTS_URL,
            headers=auth_headers,
            json={"name": "Polars"},
        )

        assert response.status_code == status.HTTP_409_CONFLICT

    def test_same_name_other_user(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        other_auth_headers: dict[str, str],
    ) -> None:
        """Two different users can use the same playlist name."""
        mine = client.post(
            PLAYLISTS_URL,
            headers=auth_headers,
            json={"name": "Polars"},
        )
        theirs = client.post(
            PLAYLISTS_URL,
            headers=other_auth_headers,
            json={"name": "Polars"},
        )

        assert mine.status_code == status.HTTP_201_CREATED
        assert theirs.status_code == status.HTTP_201_CREATED
        assert mine.json()["id_user"] != theirs.json()["id_user"]

    def test_unauthorized(self, client: TestClient) -> None:
        """Missing token: 401 Unauthorized."""
        response = client.post(PLAYLISTS_URL, json={"name": "Polars"})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_empty_name(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Empty name: 422 (validation error)."""
        response = client.post(
            PLAYLISTS_URL,
            headers=auth_headers,
            json={"name": ""},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_name_too_long(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Name longer than 100 characters: 422 (validation error)."""
        response = client.post(
            PLAYLISTS_URL,
            headers=auth_headers,
            json={"name": "a" * (MAX_NAME_LENGTH + 1)},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_missing_name(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Body without name: 422 (validation error)."""
        response = client.post(PLAYLISTS_URL, headers=auth_headers, json={})

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


class TestListPlaylistsRoute:
    """Integration tests for GET /api/playlists."""

    def test_no_playlists(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """No playlists: 200 OK and an empty list."""
        response = client.get(PLAYLISTS_URL, headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    def test_lists_my_playlists(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Created playlists are listed, in creation order."""
        for name in ("Romans", "Polars"):
            client.post(
                PLAYLISTS_URL,
                headers=auth_headers,
                json={"name": name},
            )

        response = client.get(PLAYLISTS_URL, headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        assert [p["name"] for p in response.json()] == ["Romans", "Polars"]

    def test_other_user_not_listed(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        other_auth_headers: dict[str, str],
    ) -> None:
        """The playlists of another user are never listed."""
        client.post(
            PLAYLISTS_URL,
            headers=other_auth_headers,
            json={"name": "Polars"},
        )

        mine = client.get(PLAYLISTS_URL, headers=auth_headers)
        theirs = client.get(PLAYLISTS_URL, headers=other_auth_headers)

        assert mine.json() == []
        assert len(theirs.json()) == 1

    def test_unauthorized(self, client: TestClient) -> None:
        """Missing token: 401 Unauthorized."""
        response = client.get(PLAYLISTS_URL)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestRenamePlaylistRoute:
    """Integration tests for PATCH /api/playlists/{id_playlist}."""

    def test_rename_success(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Valid new name: 200 OK, and the new name is saved."""
        id_playlist = create_playlist(client, auth_headers, "Polars")

        response = client.patch(
            f"{PLAYLISTS_URL}/{id_playlist}",
            headers=auth_headers,
            json={"name": "Thrillers"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["name"] == "Thrillers"
        listed = client.get(PLAYLISTS_URL, headers=auth_headers).json()
        assert [p["name"] for p in listed] == ["Thrillers"]

    def test_not_found(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Unknown playlist: 404 Not Found."""
        response = client.patch(
            f"{PLAYLISTS_URL}/999999999",
            headers=auth_headers,
            json={"name": "Thrillers"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_other_user_cannot_rename(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        other_auth_headers: dict[str, str],
    ) -> None:
        """Another user gets 404 and my playlist keeps its name."""
        id_playlist = create_playlist(client, auth_headers, "Polars")

        response = client.patch(
            f"{PLAYLISTS_URL}/{id_playlist}",
            headers=other_auth_headers,
            json={"name": "Pirate"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        listed = client.get(PLAYLISTS_URL, headers=auth_headers).json()
        assert [p["name"] for p in listed] == ["Polars"]

    def test_name_already_used(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """New name already used by another of my playlists: 409."""
        id_playlist = create_playlist(client, auth_headers, "Polars")
        create_playlist(client, auth_headers, "Romans")

        response = client.patch(
            f"{PLAYLISTS_URL}/{id_playlist}",
            headers=auth_headers,
            json={"name": "Romans"},
        )

        assert response.status_code == status.HTTP_409_CONFLICT

    def test_empty_name(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Empty new name: 422 (validation error)."""
        id_playlist = create_playlist(client, auth_headers, "Polars")

        response = client.patch(
            f"{PLAYLISTS_URL}/{id_playlist}",
            headers=auth_headers,
            json={"name": ""},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_invalid_id(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Non-integer playlist ID: 422 (validation error)."""
        response = client.patch(
            f"{PLAYLISTS_URL}/abc",
            headers=auth_headers,
            json={"name": "Thrillers"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_unauthorized(self, client: TestClient) -> None:
        """Missing token: 401 Unauthorized."""
        response = client.patch(
            f"{PLAYLISTS_URL}/1",
            json={"name": "Thrillers"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestDeletePlaylistRoute:
    """Integration tests for DELETE /api/playlists/{id_playlist}."""

    def test_delete_success(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Existing playlist: 204 No Content, and it is no longer listed."""
        id_playlist = create_playlist(client, auth_headers, "Polars")

        response = client.delete(
            f"{PLAYLISTS_URL}/{id_playlist}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert client.get(PLAYLISTS_URL, headers=auth_headers).json() == []

    def test_not_found(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Unknown playlist: 404 Not Found."""
        response = client.delete(
            f"{PLAYLISTS_URL}/999999999",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_twice(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Second deletion of the same playlist: 404 Not Found."""
        id_playlist = create_playlist(client, auth_headers, "Polars")
        url = f"{PLAYLISTS_URL}/{id_playlist}"
        client.delete(url, headers=auth_headers)

        response = client.delete(url, headers=auth_headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_other_user_cannot_delete(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        other_auth_headers: dict[str, str],
    ) -> None:
        """Another user gets 404 and my playlist is kept."""
        id_playlist = create_playlist(client, auth_headers, "Polars")

        response = client.delete(
            f"{PLAYLISTS_URL}/{id_playlist}",
            headers=other_auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert len(client.get(PLAYLISTS_URL, headers=auth_headers).json()) == 1

    def test_unauthorized(self, client: TestClient) -> None:
        """Missing token: 401 Unauthorized."""
        response = client.delete(f"{PLAYLISTS_URL}/1")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestAddBookToPlaylistRoute:
    """Integration tests for POST /api/playlists/{id_playlist}/books."""

    def test_add_success(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        id_book: int,
    ) -> None:
        """Book of the catalog: 201 Created."""
        id_playlist = create_playlist(client, auth_headers, "Polars")

        response = client.post(
            f"{PLAYLISTS_URL}/{id_playlist}/books",
            headers=auth_headers,
            json={"id_book": id_book},
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.json() == {
            "id_playlist": id_playlist,
            "id_book": id_book,
        }

    def test_duplicate(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        id_book: int,
    ) -> None:
        """Same book twice in the same playlist: 409 Conflict."""
        id_playlist = create_playlist(client, auth_headers, "Polars")
        url = f"{PLAYLISTS_URL}/{id_playlist}/books"
        client.post(url, headers=auth_headers, json={"id_book": id_book})

        response = client.post(
            url,
            headers=auth_headers,
            json={"id_book": id_book},
        )

        assert response.status_code == status.HTTP_409_CONFLICT

    def test_book_not_found(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Book missing from the local catalog: 404 Not Found."""
        id_playlist = create_playlist(client, auth_headers, "Polars")

        response = client.post(
            f"{PLAYLISTS_URL}/{id_playlist}/books",
            headers=auth_headers,
            json={"id_book": 999999999},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_playlist_not_found(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        id_book: int,
    ) -> None:
        """Unknown playlist: 404 Not Found."""
        response = client.post(
            f"{PLAYLISTS_URL}/999999999/books",
            headers=auth_headers,
            json={"id_book": id_book},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_other_user_cannot_add(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        other_auth_headers: dict[str, str],
        id_book: int,
    ) -> None:
        """Another user gets 404 and my playlist stays empty."""
        id_playlist = create_playlist(client, auth_headers, "Polars")

        response = client.post(
            f"{PLAYLISTS_URL}/{id_playlist}/books",
            headers=other_auth_headers,
            json={"id_book": id_book},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        mine = client.get(
            f"{PLAYLISTS_URL}/{id_playlist}",
            headers=auth_headers,
        )
        assert mine.json()["books"] == []

    def test_missing_book_id(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Body without id_book: 422 (validation error)."""
        id_playlist = create_playlist(client, auth_headers, "Polars")

        response = client.post(
            f"{PLAYLISTS_URL}/{id_playlist}/books",
            headers=auth_headers,
            json={},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_unauthorized(self, client: TestClient) -> None:
        """Missing token: 401 Unauthorized."""
        response = client.post(
            f"{PLAYLISTS_URL}/1/books",
            json={"id_book": 1},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestGetPlaylistRoute:
    """Integration tests for GET /api/playlists/{id_playlist}."""

    def test_empty_playlist(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """New playlist: 200 OK, its name and an empty list of books."""
        id_playlist = create_playlist(client, auth_headers, "Polars")

        response = client.get(
            f"{PLAYLISTS_URL}/{id_playlist}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id_playlist"] == id_playlist
        assert data["name"] == "Polars"
        assert data["books"] == []

    def test_books_with_details(
        self,
        client: TestClient,
        cursor: RealDictCursor,
        auth_headers: dict[str, str],
    ) -> None:
        """Books are listed with their details, sorted by title."""
        id_playlist = create_playlist(client, auth_headers, "Polars")
        url = f"{PLAYLISTS_URL}/{id_playlist}"
        for title in ("Dune", "Anna Karenine"):
            client.post(
                f"{url}/books",
                headers=auth_headers,
                json={"id_book": create_book(cursor, title)},
            )

        response = client.get(url, headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        books = response.json()["books"]
        assert [b["title"] for b in books] == ["Anna Karenine", "Dune"]
        assert {"id_book", "author", "cover_image"} <= set(books[0])

    def test_not_found(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Unknown playlist: 404 Not Found."""
        response = client.get(
            f"{PLAYLISTS_URL}/999999999",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_other_user_cannot_read(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        other_auth_headers: dict[str, str],
    ) -> None:
        """Another user's playlist: 404 Not Found."""
        id_playlist = create_playlist(client, auth_headers, "Polars")

        response = client.get(
            f"{PLAYLISTS_URL}/{id_playlist}",
            headers=other_auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_unauthorized(self, client: TestClient) -> None:
        """Missing token: 401 Unauthorized."""
        response = client.get(f"{PLAYLISTS_URL}/1")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestRemoveBookFromPlaylistRoute:
    """Integration tests for DELETE /api/playlists/{id}/books/{id_book}."""

    def test_remove_success(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        id_book: int,
    ) -> None:
        """Book in the playlist: 204 No Content, and it is no longer listed."""
        id_playlist = create_playlist(client, auth_headers, "Polars")
        url = f"{PLAYLISTS_URL}/{id_playlist}"
        client.post(
            f"{url}/books",
            headers=auth_headers,
            json={"id_book": id_book},
        )

        response = client.delete(
            f"{url}/books/{id_book}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert client.get(url, headers=auth_headers).json()["books"] == []

    def test_book_not_in_playlist(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        id_book: int,
    ) -> None:
        """Book not in the playlist: 404 Not Found."""
        id_playlist = create_playlist(client, auth_headers, "Polars")

        response = client.delete(
            f"{PLAYLISTS_URL}/{id_playlist}/books/{id_book}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_playlist_not_found(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        id_book: int,
    ) -> None:
        """Unknown playlist: 404 Not Found."""
        response = client.delete(
            f"{PLAYLISTS_URL}/999999999/books/{id_book}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_other_user_cannot_remove(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        other_auth_headers: dict[str, str],
        id_book: int,
    ) -> None:
        """Another user gets 404 and the book stays in my playlist."""
        id_playlist = create_playlist(client, auth_headers, "Polars")
        url = f"{PLAYLISTS_URL}/{id_playlist}"
        client.post(
            f"{url}/books",
            headers=auth_headers,
            json={"id_book": id_book},
        )

        response = client.delete(
            f"{url}/books/{id_book}",
            headers=other_auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        books = client.get(url, headers=auth_headers).json()["books"]
        assert len(books) == 1

    def test_unauthorized(self, client: TestClient) -> None:
        """Missing token: 401 Unauthorized."""
        response = client.delete(f"{PLAYLISTS_URL}/1/books/1")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
