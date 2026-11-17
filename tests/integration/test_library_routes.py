"""Integration tests for the library routes.

The routes are called through FastAPI's TestClient, with the real database
from the .env file. The request cursor is replaced by the test cursor, so
every change made during a test is rolled back afterwards.
"""

from collections.abc import Generator
from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from psycopg2.extras import RealDictCursor

from src.api.deps import get_cursor
from src.core.config import settings
from src.main import app

LIBRARY_BOOKS_URL = f"{settings.API_STR}/library/books"
FAVORITES_URL = f"{settings.API_STR}/library/favorites"
REGISTER_URL = f"{settings.API_STR}/auth/register"
LOGIN_URL = f"{settings.API_STR}/auth/login"
USERS_URL = f"{settings.API_STR}/users"
ME_URL = f"{settings.API_STR}/users/me"
PASSWORD = "password123"
START = "2026-01-05"
END = "2026-01-20"
BEFORE_START = "2026-01-01"


@pytest.fixture
def client(cursor: RealDictCursor) -> Generator[TestClient]:
    """Return a TestClient bound to the rolled-back test cursor."""

    def override_get_cursor() -> RealDictCursor:
        return cursor

    app.dependency_overrides[get_cursor] = override_get_cursor
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(client: TestClient) -> dict[str, str]:
    """Register and log in a temporary test user and return auth headers."""
    uname = f"libuser_{uuid4().hex[:8]}"
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
def other_auth_headers(client: TestClient) -> dict[str, str]:
    """Register and log in a second test user and return auth headers."""
    uname = f"libother_{uuid4().hex[:8]}"
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
def id_book(cursor: RealDictCursor) -> int:
    """Insert a test book in the database and return its ID."""
    cursor.execute(
        """
        INSERT INTO books (id_book_api, title)
        VALUES ('openlib_test_route', 'Test Book API')
        RETURNING id_book
        """,
    )
    row = cursor.fetchone()
    assert row is not None
    return row["id_book"]


@pytest.fixture
def id_other_book(cursor: RealDictCursor) -> int:
    """Insert a second test book in the database and return its ID."""
    cursor.execute(
        """
        INSERT INTO books (id_book_api, title)
        VALUES ('openlib_test_route_2', 'Other Test Book API')
        RETURNING id_book
        """,
    )
    row = cursor.fetchone()
    assert row is not None
    return row["id_book"]


class TestAddBookRoute:
    """Integration tests for POST /api/library/books."""

    def test_add_book_success(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        id_book: int,
    ) -> None:
        """Valid request: returns 201 Created and the book data."""
        payload = {"id_book": id_book, "state": "READING"}
        response = client.post(
            LIBRARY_BOOKS_URL,
            headers=auth_headers,
            json=payload,
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["id_book"] == id_book
        assert data["state"] == "READING"
        assert data["is_favorite"] is False
        assert data["started_at"] is None
        assert data["finished_at"] is None

    def test_add_book_abandoned(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        id_book: int,
    ) -> None:
        """The ABANDONED state is accepted: 201 Created."""
        response = client.post(
            LIBRARY_BOOKS_URL,
            headers=auth_headers,
            json={"id_book": id_book, "state": "ABANDONED"},
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["state"] == "ABANDONED"

    def test_unauthorized(self, client: TestClient, id_book: int) -> None:
        """Missing token: the authentication dependency rejects with 401."""
        payload = {"id_book": id_book, "state": "READING"}
        response = client.post(LIBRARY_BOOKS_URL, json=payload)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_book_not_found(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Unknown book ID: Exception is mapped to 404 Not Found."""
        payload = {"id_book": 999_999_999, "state": "READING"}
        response = client.post(
            LIBRARY_BOOKS_URL,
            headers=auth_headers,
            json=payload,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_book_already_in_library(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        id_book: int,
    ) -> None:
        """Adding the same book twice: Exception is mapped to 409 Conflict."""
        payload = {"id_book": id_book, "state": "READING"}

        client.post(LIBRARY_BOOKS_URL, headers=auth_headers, json=payload)

        response = client.post(
            LIBRARY_BOOKS_URL,
            headers=auth_headers,
            json=payload,
        )

        assert response.status_code == status.HTTP_409_CONFLICT

    def test_invalid_state(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        id_book: int,
    ) -> None:
        """Invalid state: 422 Unprocessable Content."""
        payload = {"id_book": id_book, "state": "EN_COURS"}
        response = client.post(
            LIBRARY_BOOKS_URL,
            headers=auth_headers,
            json=payload,
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


class TestRemoveBookRoute:
    """Integration tests for DELETE /api/library/books/{id_book}."""

    def test_remove_book_success(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        id_book: int,
    ) -> None:
        """Book in library: returns 204 No Content with an empty body."""
        client.post(
            LIBRARY_BOOKS_URL,
            headers=auth_headers,
            json={"id_book": id_book, "state": "READING"},
        )

        response = client.delete(
            f"{LIBRARY_BOOKS_URL}/{id_book}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert response.content == b""

    def test_book_not_in_library(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        id_book: int,
    ) -> None:
        """Book not in library: Exception is mapped to 404 Not Found."""
        response = client.delete(
            f"{LIBRARY_BOOKS_URL}/{id_book}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_remove_twice(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        id_book: int,
    ) -> None:
        """Second delete of the same book: 404, it is already gone."""
        client.post(
            LIBRARY_BOOKS_URL,
            headers=auth_headers,
            json={"id_book": id_book, "state": "READING"},
        )
        url = f"{LIBRARY_BOOKS_URL}/{id_book}"
        client.delete(url, headers=auth_headers)

        response = client.delete(url, headers=auth_headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_unauthorized(self, client: TestClient, id_book: int) -> None:
        """Missing token: the authentication dependency rejects with 401."""
        response = client.delete(f"{LIBRARY_BOOKS_URL}/{id_book}")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_invalid_id(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Non-integer book ID: 422 Unprocessable Content."""
        response = client.delete(
            f"{LIBRARY_BOOKS_URL}/abc",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


class TestToggleLikeRoute:
    """Integration tests for POST /api/library/books/{id_book}/like."""

    def test_like(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        id_book: int,
    ) -> None:
        """Book in library: returns 200 OK and the book is liked."""
        client.post(
            LIBRARY_BOOKS_URL,
            headers=auth_headers,
            json={"id_book": id_book, "state": "READING"},
        )

        response = client.post(
            f"{LIBRARY_BOOKS_URL}/{id_book}/like",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id_book"] == id_book
        assert data["is_liked"] is True

    def test_like_then_unlike(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        id_book: int,
    ) -> None:
        """Second call on the same book: the like is removed."""
        client.post(
            LIBRARY_BOOKS_URL,
            headers=auth_headers,
            json={"id_book": id_book, "state": "READING"},
        )
        url = f"{LIBRARY_BOOKS_URL}/{id_book}/like"
        client.post(url, headers=auth_headers)

        response = client.post(url, headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["is_liked"] is False

    def test_book_not_in_library(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        id_book: int,
    ) -> None:
        """Book not in library: Exception is mapped to 404 Not Found."""
        response = client.post(
            f"{LIBRARY_BOOKS_URL}/{id_book}/like",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_unauthorized(self, client: TestClient, id_book: int) -> None:
        """Missing token: the authentication dependency rejects with 401."""
        response = client.post(f"{LIBRARY_BOOKS_URL}/{id_book}/like")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_invalid_id(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Non-integer book ID: 422 Unprocessable Content."""
        response = client.post(
            f"{LIBRARY_BOOKS_URL}/abc/like",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_other_user_cannot_toggle(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        id_book: int,
    ) -> None:
        """Another user gets 404 and does not change my like."""
        url = f"{LIBRARY_BOOKS_URL}/{id_book}/like"
        client.post(
            LIBRARY_BOOKS_URL,
            headers=auth_headers,
            json={"id_book": id_book, "state": "READING"},
        )
        client.post(url, headers=auth_headers)

        other = f"libuser_{uuid4().hex[:8]}"
        client.post(
            REGISTER_URL,
            json={
                "username": other,
                "email": f"{other}@ensai.fr",
                "password": PASSWORD,
            },
        )
        login_resp = client.post(
            LOGIN_URL,
            data={"username": other, "password": PASSWORD},
        )
        other_token = login_resp.json()["access_token"]
        other_headers = {"Authorization": f"Bearer {other_token}"}

        response = client.post(url, headers=other_headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND

        mine = client.post(url, headers=auth_headers)
        assert mine.json()["is_liked"] is False


class TestToggleFavoriteRoute:
    """Integration tests for POST /api/library/books/{id_book}/favorite."""

    def test_favorite(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        id_book: int,
    ) -> None:
        """Book in library: returns 200 OK and the book is a favorite."""
        client.post(
            LIBRARY_BOOKS_URL,
            headers=auth_headers,
            json={"id_book": id_book, "state": "READING"},
        )

        response = client.post(
            f"{LIBRARY_BOOKS_URL}/{id_book}/favorite",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id_book"] == id_book
        assert data["is_favorite"] is True

    def test_favorite_then_unfavorite(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        id_book: int,
    ) -> None:
        """Second call on the same book: the favorite is removed."""
        client.post(
            LIBRARY_BOOKS_URL,
            headers=auth_headers,
            json={"id_book": id_book, "state": "READING"},
        )
        url = f"{LIBRARY_BOOKS_URL}/{id_book}/favorite"
        client.post(url, headers=auth_headers)

        response = client.post(url, headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["is_favorite"] is False

    def test_book_not_in_library(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        id_book: int,
    ) -> None:
        """Book not in library: Exception is mapped to 404 Not Found."""
        response = client.post(
            f"{LIBRARY_BOOKS_URL}/{id_book}/favorite",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_unauthorized(self, client: TestClient, id_book: int) -> None:
        """Missing token: the authentication dependency rejects with 401."""
        response = client.post(f"{LIBRARY_BOOKS_URL}/{id_book}/favorite")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_invalid_id(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Non-integer book ID: 422 Unprocessable Content."""
        response = client.post(
            f"{LIBRARY_BOOKS_URL}/abc/favorite",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_other_user_cannot_toggle(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        id_book: int,
    ) -> None:
        """Another user gets 404 and does not change my favorite."""
        url = f"{LIBRARY_BOOKS_URL}/{id_book}/favorite"
        client.post(
            LIBRARY_BOOKS_URL,
            headers=auth_headers,
            json={"id_book": id_book, "state": "READING"},
        )
        client.post(url, headers=auth_headers)

        other = f"libuser_{uuid4().hex[:8]}"
        client.post(
            REGISTER_URL,
            json={
                "username": other,
                "email": f"{other}@ensai.fr",
                "password": PASSWORD,
            },
        )
        login_resp = client.post(
            LOGIN_URL,
            data={"username": other, "password": PASSWORD},
        )
        other_token = login_resp.json()["access_token"]
        other_headers = {"Authorization": f"Bearer {other_token}"}

        response = client.post(url, headers=other_headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND

        mine = client.post(url, headers=auth_headers)
        assert mine.json()["is_favorite"] is False


class TestListFavoritesRoute:
    """Integration tests for GET /api/library/favorites."""

    def test_no_favorites(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """No favorites: returns 200 OK and an empty list."""
        response = client.get(FAVORITES_URL, headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    def test_favorite_listed(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        id_book: int,
    ) -> None:
        """A book added to favorites is listed."""
        client.post(
            LIBRARY_BOOKS_URL,
            headers=auth_headers,
            json={"id_book": id_book, "state": "READING"},
        )
        client.post(
            f"{LIBRARY_BOOKS_URL}/{id_book}/favorite",
            headers=auth_headers,
        )

        response = client.get(FAVORITES_URL, headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["id_book"] == id_book
        assert data[0]["is_favorite"] is True
        assert data[0]["title"] == "Test Book API"

    def test_unauthorized(self, client: TestClient) -> None:
        """Missing token: the authentication dependency rejects with 401."""
        response = client.get(FAVORITES_URL)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_not_favorite_not_listed(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        id_book: int,
    ) -> None:
        """A book in the library but not in favorites is not listed."""
        client.post(
            LIBRARY_BOOKS_URL,
            headers=auth_headers,
            json={"id_book": id_book, "state": "READING"},
        )

        response = client.get(FAVORITES_URL, headers=auth_headers)

        assert response.json() == []

    def test_unfavorite_removes_from_list(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        id_book: int,
    ) -> None:
        """A book removed from favorites is no longer listed."""
        client.post(
            LIBRARY_BOOKS_URL,
            headers=auth_headers,
            json={"id_book": id_book, "state": "READING"},
        )
        url = f"{LIBRARY_BOOKS_URL}/{id_book}/favorite"
        client.post(url, headers=auth_headers)
        client.post(url, headers=auth_headers)

        response = client.get(FAVORITES_URL, headers=auth_headers)

        assert response.json() == []

    def test_other_user_favorites_not_listed(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        other_auth_headers: dict[str, str],
        id_book: int,
    ) -> None:
        """The favorites of another user are never listed."""
        client.post(
            LIBRARY_BOOKS_URL,
            headers=other_auth_headers,
            json={"id_book": id_book, "state": "READING"},
        )
        client.post(
            f"{LIBRARY_BOOKS_URL}/{id_book}/favorite",
            headers=other_auth_headers,
        )

        mine = client.get(FAVORITES_URL, headers=auth_headers)
        theirs = client.get(FAVORITES_URL, headers=other_auth_headers)

        assert mine.json() == []
        assert len(theirs.json()) == 1


class TestListBooksRoute:
    """Integration tests for GET /api/library/books."""

    def test_filter_abandoned(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        id_book: int,
        id_other_book: int,
    ) -> None:
        """The ABANDONED filter keeps only the abandoned books."""
        books = ((id_book, "ABANDONED"), (id_other_book, "READING"))
        for book, state in books:
            client.post(
                LIBRARY_BOOKS_URL,
                headers=auth_headers,
                json={"id_book": book, "state": state},
            )

        response = client.get(
            LIBRARY_BOOKS_URL,
            headers=auth_headers,
            params={"status": "ABANDONED"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert [book["id_book"] for book in data] == [id_book]
        assert data[0]["state"] == "ABANDONED"

    def test_invalid_status(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Unknown status value: 422 Unprocessable Content."""
        response = client.get(
            LIBRARY_BOOKS_URL,
            headers=auth_headers,
            params={"status": "FINISHED"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_new_book_has_no_dates(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        id_book: int,
    ) -> None:
        """A book just added is listed with both dates set to null."""
        client.post(
            LIBRARY_BOOKS_URL,
            headers=auth_headers,
            json={"id_book": id_book, "state": "READING"},
        )

        data = client.get(LIBRARY_BOOKS_URL, headers=auth_headers).json()

        assert data[0]["started_at"] is None
        assert data[0]["finished_at"] is None


class TestUpdateBookStatusRoute:
    """Integration tests for PATCH /api/library/books/{id_book}/status."""

    def test_update_status_success(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        id_book: int,
    ) -> None:
        """Book in library: returns 200 OK and the updated status."""
        client.post(
            LIBRARY_BOOKS_URL,
            headers=auth_headers,
            json={"id_book": id_book, "state": "READING"},
        )

        response = client.patch(
            f"{LIBRARY_BOOKS_URL}/{id_book}/status",
            headers=auth_headers,
            json={"state": "COMPLETED"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id_book"] == id_book
        assert data["state"] == "COMPLETED"

    def test_update_status_abandoned(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        id_book: int,
    ) -> None:
        """A book can be marked as abandoned: 200 OK."""
        client.post(
            LIBRARY_BOOKS_URL,
            headers=auth_headers,
            json={"id_book": id_book, "state": "READING"},
        )

        response = client.patch(
            f"{LIBRARY_BOOKS_URL}/{id_book}/status",
            headers=auth_headers,
            json={"state": "ABANDONED"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["state"] == "ABANDONED"

    def test_invalid_state_rejected(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        id_book: int,
    ) -> None:
        """Invalid state in payload: 422 Unprocessable Content."""
        client.post(
            LIBRARY_BOOKS_URL,
            headers=auth_headers,
            json={"id_book": id_book, "state": "READING"},
        )

        response = client.patch(
            f"{LIBRARY_BOOKS_URL}/{id_book}/status",
            headers=auth_headers,
            json={"state": "FINISHED"},  # Not in regex pattern
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_book_not_in_library(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        id_book: int,
    ) -> None:
        """Book not in library: Exception is mapped to 404 Not Found."""
        response = client.patch(
            f"{LIBRARY_BOOKS_URL}/{id_book}/status",
            headers=auth_headers,
            json={"state": "COMPLETED"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_unauthorized(self, client: TestClient, id_book: int) -> None:
        """Missing token: the authentication dependency rejects with 401."""
        response = client.patch(
            f"{LIBRARY_BOOKS_URL}/{id_book}/status",
            json={"state": "COMPLETED"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_other_user_cannot_update(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        other_auth_headers: dict[str, str],
        id_book: int,
    ) -> None:
        """Another user gets 404 and does not change my reading status."""
        client.post(
            LIBRARY_BOOKS_URL,
            headers=auth_headers,
            json={"id_book": id_book, "state": "READING"},
        )

        response = client.patch(
            f"{LIBRARY_BOOKS_URL}/{id_book}/status",
            headers=other_auth_headers,
            json={"state": "COMPLETED"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

        mine = client.get(LIBRARY_BOOKS_URL, headers=auth_headers)
        assert mine.json()[0]["state"] == "READING"


class TestUpdateBookDatesRoute:
    """Integration tests for PATCH /api/library/books/{id_book}/dates."""

    def test_update_dates_success(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        id_book: int,
    ) -> None:
        """Book in library: returns 200 OK and both dates."""
        client.post(
            LIBRARY_BOOKS_URL,
            headers=auth_headers,
            json={"id_book": id_book, "state": "COMPLETED"},
        )

        response = client.patch(
            f"{LIBRARY_BOOKS_URL}/{id_book}/dates",
            headers=auth_headers,
            json={"started_at": START, "finished_at": END},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id_book"] == id_book
        assert data["state"] == "COMPLETED"
        assert data["started_at"] == START
        assert data["finished_at"] == END

    def test_partial_update(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        id_book: int,
    ) -> None:
        """Only the field that is sent changes, the other one is kept."""
        url = f"{LIBRARY_BOOKS_URL}/{id_book}/dates"
        client.post(
            LIBRARY_BOOKS_URL,
            headers=auth_headers,
            json={"id_book": id_book, "state": "READING"},
        )
        first = client.patch(
            url,
            headers=auth_headers,
            json={"started_at": START},
        )
        assert first.status_code == status.HTTP_200_OK
        assert first.json()["started_at"] == START
        assert first.json()["finished_at"] is None

        response = client.patch(
            url,
            headers=auth_headers,
            json={"finished_at": END},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["started_at"] == START
        assert data["finished_at"] == END

    def test_null_erases_a_date(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        id_book: int,
    ) -> None:
        """A date sent as null is erased, the other one is kept."""
        url = f"{LIBRARY_BOOKS_URL}/{id_book}/dates"
        client.post(
            LIBRARY_BOOKS_URL,
            headers=auth_headers,
            json={"id_book": id_book, "state": "READING"},
        )
        client.patch(
            url,
            headers=auth_headers,
            json={"started_at": START, "finished_at": END},
        )

        response = client.patch(
            url,
            headers=auth_headers,
            json={"finished_at": None},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["started_at"] == START
        assert data["finished_at"] is None

    def test_book_not_in_library(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        id_book: int,
    ) -> None:
        """Book not in library: Exception is mapped to 404 Not Found."""
        response = client.patch(
            f"{LIBRARY_BOOKS_URL}/{id_book}/dates",
            headers=auth_headers,
            json={"started_at": START},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Book is not in the library."

    def test_end_before_start(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        id_book: int,
    ) -> None:
        """End date before start date: 400, and nothing is saved."""
        client.post(
            LIBRARY_BOOKS_URL,
            headers=auth_headers,
            json={"id_book": id_book, "state": "COMPLETED"},
        )

        response = client.patch(
            f"{LIBRARY_BOOKS_URL}/{id_book}/dates",
            headers=auth_headers,
            json={"started_at": END, "finished_at": START},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["detail"] == (
            "The end date cannot be before the start date."
        )
        mine = client.get(LIBRARY_BOOKS_URL, headers=auth_headers).json()
        assert mine[0]["started_at"] is None
        assert mine[0]["finished_at"] is None

    def test_end_before_stored_start(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        id_book: int,
    ) -> None:
        """Only the end is sent, before the stored start date: 400."""
        url = f"{LIBRARY_BOOKS_URL}/{id_book}/dates"
        client.post(
            LIBRARY_BOOKS_URL,
            headers=auth_headers,
            json={"id_book": id_book, "state": "COMPLETED"},
        )
        client.patch(url, headers=auth_headers, json={"started_at": START})

        response = client.patch(
            url,
            headers=auth_headers,
            json={"finished_at": BEFORE_START},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        mine = client.get(LIBRARY_BOOKS_URL, headers=auth_headers).json()
        assert mine[0]["started_at"] == START
        assert mine[0]["finished_at"] is None

    def test_empty_body(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        id_book: int,
    ) -> None:
        """Nothing to update: 400 Bad Request."""
        client.post(
            LIBRARY_BOOKS_URL,
            headers=auth_headers,
            json={"id_book": id_book, "state": "READING"},
        )

        response = client.patch(
            f"{LIBRARY_BOOKS_URL}/{id_book}/dates",
            headers=auth_headers,
            json={},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["detail"] == "Nothing to update."

    def test_invalid_date(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        id_book: int,
    ) -> None:
        """Badly formatted date: 422 Unprocessable Content."""
        client.post(
            LIBRARY_BOOKS_URL,
            headers=auth_headers,
            json={"id_book": id_book, "state": "READING"},
        )

        response = client.patch(
            f"{LIBRARY_BOOKS_URL}/{id_book}/dates",
            headers=auth_headers,
            json={"started_at": "05/01/2026"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_unauthorized(self, client: TestClient, id_book: int) -> None:
        """Missing token: the authentication dependency rejects with 401."""
        response = client.patch(
            f"{LIBRARY_BOOKS_URL}/{id_book}/dates",
            json={"started_at": START},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_other_user_cannot_update(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        other_auth_headers: dict[str, str],
        id_book: int,
    ) -> None:
        """Another user gets 404 and does not change my reading dates."""
        client.post(
            LIBRARY_BOOKS_URL,
            headers=auth_headers,
            json={"id_book": id_book, "state": "READING"},
        )

        response = client.patch(
            f"{LIBRARY_BOOKS_URL}/{id_book}/dates",
            headers=other_auth_headers,
            json={"started_at": START},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

        mine = client.get(LIBRARY_BOOKS_URL, headers=auth_headers)
        assert mine.json()[0]["started_at"] is None

    def test_dates_listed_everywhere(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        other_auth_headers: dict[str, str],
        id_book: int,
    ) -> None:
        """The dates appear in my library, my favorites and my profile."""
        client.post(
            LIBRARY_BOOKS_URL,
            headers=auth_headers,
            json={"id_book": id_book, "state": "COMPLETED"},
        )
        client.post(
            f"{LIBRARY_BOOKS_URL}/{id_book}/favorite",
            headers=auth_headers,
        )
        client.patch(
            f"{LIBRARY_BOOKS_URL}/{id_book}/dates",
            headers=auth_headers,
            json={"started_at": START, "finished_at": END},
        )
        my_id = client.get(ME_URL, headers=auth_headers).json()["id_user"]

        responses = (
            client.get(LIBRARY_BOOKS_URL, headers=auth_headers),
            client.get(FAVORITES_URL, headers=auth_headers),
            client.get(
                f"{USERS_URL}/{my_id}/library",
                headers=other_auth_headers,
            ),
        )

        for response in responses:
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data) == 1
            assert data[0]["id_book"] == id_book
            assert data[0]["started_at"] == START
            assert data[0]["finished_at"] == END
