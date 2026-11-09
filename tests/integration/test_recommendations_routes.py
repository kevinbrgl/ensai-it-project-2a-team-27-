"""Integration tests for the recommendation routes.

Uses the rolled-back test cursor (tests/integration/conftest.py).
Open Library is mocked.
"""

from collections.abc import Callable
from typing import Any
from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from psycopg2.extras import RealDictCursor
from pytest_mock import MockerFixture

from src.core.config import settings
from src.dao.books_dao import BookDAO
from src.dao.users_dao import UserDAO
from src.models.books import Book, BookCreate
from src.models.users import UserCreate
from src.services.books_service import BookService
from src.utils.exceptions import ExternalServiceError

RECOMMENDATIONS_URL = f"{settings.API_STR}/recommendations"
LIBRARY_URL = f"{settings.API_STR}/library/books"
ME_URL = f"{settings.API_STR}/users/me"
REGISTER_URL = f"{settings.API_STR}/auth/register"
LOGIN_URL = f"{settings.API_STR}/auth/login"
PASSWORD = "password123"


def unique_category() -> str:
    """Return a category that no other book uses."""
    return f"Genre {uuid4().hex[:10]}"


def unique_key() -> str:
    """Return an Open Library key that no other book uses."""
    return f"/works/OL{uuid4().hex[:10]}W"


def ol_doc(
    key: str,
    title: str,
    category: str,
    rating: float | None = None,
) -> dict[str, Any]:
    """Build an Open Library search document."""
    doc: dict[str, Any] = {
        "key": key,
        "title": title,
        "author_name": ["Test Author"],
        "subject": [category],
        "first_publish_year": 2000,
    }
    if rating is not None:
        doc["ratings_average"] = rating
    return doc


def add_review(
    cursor: RealDictCursor,
    id_user: int,
    id_book: int,
    rating: int,
) -> None:
    """Insert a review."""
    cursor.execute(
        "INSERT INTO reviews (id_user, id_book, rating) VALUES (%s, %s, %s)",
        (id_user, id_book, rating),
    )


@pytest.fixture
def auth_headers(client: TestClient) -> dict[str, str]:
    """Register and log in a temporary test user and return auth headers."""
    uname = f"reco_{uuid4().hex[:8]}"
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
def other_user_id(user_dao: UserDAO) -> int:
    """Insert another user (review author) and return its ID."""
    name = f"reco_{uuid4().hex[:8]}"
    return user_dao.create(
        UserCreate(
            username=name,
            email=f"{name}@ensai.fr",
            password_hash="fakehash",
        ),
    ).id_user


@pytest.fixture
def rate_as_other(
    cursor: RealDictCursor,
    other_user_id: int,
) -> Callable[[int, int], None]:
    """Return a function inserting a review written by another user."""

    def rate(id_book: int, rating: int) -> None:
        add_review(cursor, other_user_id, id_book, rating)

    return rate


def add_to_my_library(
    client: TestClient,
    headers: dict[str, str],
    id_book: int,
    state: str = "COMPLETED",
) -> None:
    """Add a book to the authenticated user's library."""
    response = client.post(
        LIBRARY_URL,
        json={"id_book": id_book, "state": state},
        headers=headers,
    )
    assert response.status_code == status.HTTP_201_CREATED


def mock_open_library(
    mocker: MockerFixture,
    docs: list[dict[str, Any]] | None = None,
    error: Exception | None = None,
) -> Any:  # ruff: ignore[any-type]
    """Patch BookService._fetch_open_library."""
    if error is not None:
        return mocker.patch.object(
            BookService,
            "_fetch_open_library",
            side_effect=error,
        )
    return mocker.patch.object(
        BookService,
        "_fetch_open_library",
        return_value={"docs": docs or []},
    )


class TestRecommendationsAuthAndValidation:
    """Authentication and validation of GET /api/recommendations."""

    def test_unauthenticated(self, client: TestClient) -> None:
        """Route requires authentication."""
        response = client.get(RECOMMENDATIONS_URL)
        assert response.status_code in {
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        }

    @pytest.mark.parametrize(
        "params",
        [{"sort": "popularity"}, {"limit": 0}, {"limit": 51}, {"genre": ""}],
    )
    def test_invalid_parameters_422(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        params: dict[str, str | int],
    ) -> None:
        """Invalid query parameters return 422."""
        response = client.get(
            RECOMMENDATIONS_URL,
            params=params,
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


class TestRecommendationsOpenLibrary:
    """Recommendations built from Open Library."""

    def test_requested_genre(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        book_dao: BookDAO,
        mocker: MockerFixture,
    ) -> None:
        """Books are saved, scored and sorted, with a reason."""
        category = unique_category()
        low_key, high_key = unique_key(), unique_key()
        fetch = mock_open_library(
            mocker,
            [
                ol_doc(low_key, "Low", category, 3.5),
                ol_doc(high_key, "High", category, 4.5),
            ],
        )

        response = client.get(
            RECOMMENDATIONS_URL,
            params={"genre": category},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert [r["book"]["id_book_api"] for r in data] == [
            high_key,
            low_key,
        ]
        assert [r["score"] for r in data] == [4.5, 3.5]
        assert {r["reason"] for r in data} == {f"Popular in {category}"}
        fetch.assert_called_once_with(
            limit=20,
            subject=category,
            sort="rating",
        )
        for rec in data:
            saved = book_dao.read_by_api_id(rec["book"]["id_book_api"])
            assert saved is not None
            assert saved.id_book == rec["book"]["id_book"]

    def test_history_genre(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        book_dao: BookDAO,
        mocker: MockerFixture,
    ) -> None:
        """Without genre, the library's category is used."""
        category = unique_category()
        owned = book_dao.create(BookCreate(title="Read", category=category))
        add_to_my_library(client, auth_headers, owned.id_book)
        new_key = unique_key()
        fetch = mock_open_library(
            mocker,
            [ol_doc(new_key, "New", category, 4.0)],
        )

        response = client.get(RECOMMENDATIONS_URL, headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        assert fetch.call_args.kwargs["subject"] == category
        assert [
            (r["book"]["id_book_api"], r["reason"]) for r in response.json()
        ] == [(new_key, f"Because you like {category}")]

    def test_rated_genre_used_as_history(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        cursor: RealDictCursor,
        book_dao: BookDAO,
        mocker: MockerFixture,
    ) -> None:
        """A genre rated 4 or more is used even outside the library."""
        category = unique_category()
        me = client.get(ME_URL, headers=auth_headers).json()["id_user"]
        rated = book_dao.create(BookCreate(title="Loved", category=category))
        add_review(cursor, me, rated.id_book, 5)
        fetch = mock_open_library(
            mocker,
            [ol_doc(unique_key(), "New", category, 4.0)],
        )

        response = client.get(RECOMMENDATIONS_URL, headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        assert fetch.call_args.kwargs["subject"] == category

    def test_excludes_library_books(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        book_dao: BookDAO,
        mocker: MockerFixture,
    ) -> None:
        """A book already in the library is not recommended."""
        category = unique_category()
        owned_key, new_key = unique_key(), unique_key()
        owned = book_dao.upsert(
            BookCreate(
                title="Owned",
                category=category,
                id_book_api=owned_key,
            ),
        )
        add_to_my_library(client, auth_headers, owned.id_book, "WANT_TO_READ")
        mock_open_library(
            mocker,
            [
                ol_doc(owned_key, "Owned", category, 5.0),
                ol_doc(new_key, "New", category, 3.0),
            ],
        )

        response = client.get(
            RECOMMENDATIONS_URL,
            params={"genre": category},
            headers=auth_headers,
        )

        keys = [r["book"]["id_book_api"] for r in response.json()]
        assert keys == [new_key]

    def test_duplicates_removed(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        mocker: MockerFixture,
    ) -> None:
        """The same Open Library key is returned once."""
        category = unique_category()
        key = unique_key()
        mock_open_library(
            mocker,
            [ol_doc(key, "Dup", category), ol_doc(key, "Dup", category)],
        )

        response = client.get(
            RECOMMENDATIONS_URL,
            params={"genre": category},
            headers=auth_headers,
        )

        assert [r["book"]["id_book_api"] for r in response.json()] == [key]

    def test_local_rating_overrides_open_library(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        book_dao: BookDAO,
        rate_as_other: Callable[[int, int], None],
        mocker: MockerFixture,
    ) -> None:
        """The local average is used when the book has reviews."""
        category = unique_category()
        key = unique_key()
        known = book_dao.upsert(
            BookCreate(title="Known", category=category, id_book_api=key),
        )
        rate_as_other(known.id_book, 2)
        mock_open_library(mocker, [ol_doc(key, "Known", category, 4.8)])

        response = client.get(
            RECOMMENDATIONS_URL,
            params={"genre": category},
            headers=auth_headers,
        )

        assert [r["score"] for r in response.json()] == [2.0]

    def test_limit_and_sort_title(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        mocker: MockerFixture,
    ) -> None:
        """Limit keeps the best books, then sort orders them."""
        category = unique_category()
        mock_open_library(
            mocker,
            [
                ol_doc(unique_key(), "Zeta", category, 5.0),
                ol_doc(unique_key(), "Alpha", category, 1.0),
                ol_doc(unique_key(), "Beta", category, 4.0),
            ],
        )

        response = client.get(
            RECOMMENDATIONS_URL,
            params={"genre": category, "limit": 2, "sort": "rating"},
            headers=auth_headers,
        )

        assert [r["book"]["title"] for r in response.json()] == [
            "Zeta",
            "Beta",
        ]

        response = client.get(
            RECOMMENDATIONS_URL,
            params={"genre": category, "sort": "title"},
            headers=auth_headers,
        )

        assert [r["book"]["title"] for r in response.json()] == [
            "Alpha",
            "Beta",
            "Zeta",
        ]

    def test_recommended_book_can_be_added_to_library(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        mocker: MockerFixture,
    ) -> None:
        """The returned id_book works with POST /library/books."""
        category = unique_category()
        mock_open_library(mocker, [ol_doc(unique_key(), "New", category)])

        rec = client.get(
            RECOMMENDATIONS_URL,
            params={"genre": category},
            headers=auth_headers,
        ).json()[0]

        add_to_my_library(
            client,
            auth_headers,
            rec["book"]["id_book"],
            "WANT_TO_READ",
        )


class TestRecommendationsFallback:
    """Fallback on our own reviews."""

    @pytest.fixture
    def reviewed_book(
        self,
        book_dao: BookDAO,
        rate_as_other: Callable[[int, int], None],
    ) -> Book:
        """Insert a book of a unique category reviewed 5 by another user."""
        book = book_dao.create(
            BookCreate(title="Classic", category=unique_category()),
        )
        rate_as_other(book.id_book, 5)
        return book

    def test_open_library_down(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        reviewed_book: Book,
        mocker: MockerFixture,
    ) -> None:
        """If Open Library is down, top rated local books are returned."""
        mock_open_library(mocker, error=ExternalServiceError())

        response = client.get(
            RECOMMENDATIONS_URL,
            params={"genre": reviewed_book.category},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        assert [
            (r["book"]["id_book"], r["score"], r["reason"])
            for r in response.json()
        ] == [
            (
                reviewed_book.id_book,
                5.0,
                f"Top rated in {reviewed_book.category}",
            ),
        ]

    def test_open_library_down_excludes_library(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        reviewed_book: Book,
        mocker: MockerFixture,
    ) -> None:
        """The fallback also excludes books of the library."""
        add_to_my_library(client, auth_headers, reviewed_book.id_book)
        mock_open_library(mocker, error=ExternalServiceError())

        response = client.get(
            RECOMMENDATIONS_URL,
            params={"genre": reviewed_book.category},
            headers=auth_headers,
        )

        assert response.json() == []

    def test_no_history_no_genre(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        reviewed_book: Book,
        mocker: MockerFixture,
    ) -> None:
        """A new user gets top rated books without calling Open Library."""
        fetch = mock_open_library(mocker)

        response = client.get(
            RECOMMENDATIONS_URL,
            params={"limit": 50},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        fetch.assert_not_called()
        data = response.json()
        assert {r["reason"] for r in data} <= {"Top rated"}
        scores = [r["score"] for r in data]
        assert scores == sorted(scores, reverse=True)
        assert reviewed_book.id_book is not None

    def test_empty_open_library_result(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        reviewed_book: Book,
        mocker: MockerFixture,
    ) -> None:
        """No Open Library candidate falls back on local reviews."""
        mock_open_library(mocker, [])

        response = client.get(
            RECOMMENDATIONS_URL,
            params={"genre": reviewed_book.category},
            headers=auth_headers,
        )

        assert [r["book"]["id_book"] for r in response.json()] == [
            reviewed_book.id_book,
        ]
