"""Integration tests for the reading statistics routes.

Covers GET /api/users/me/stats and GET /api/users/{user_id}/stats.
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
from src.dao.books_dao import BookDAO
from src.dao.users_dao import UserDAO
from src.models.books import BookCreate
from src.models.users import UserCreate

STATS_URL = f"{settings.API_STR}/users/me/stats"
USERS_URL = f"{settings.API_STR}/users"
REGISTER_URL = f"{settings.API_STR}/auth/register"
LOGIN_URL = f"{settings.API_STR}/auth/login"
LIBRARY_BOOKS_URL = f"{settings.API_STR}/library/books"
PASSWORD = "motdepasse123"
NO_RATINGS = [{"rating": rating, "count": 0} for rating in range(1, 6)]
SHORT_BOOK_PAGES = 120
LONG_BOOK_PAGES = 480


def register_and_login(client: TestClient) -> tuple[dict[str, str], int]:
    """Register and log in a new user.

    :param client: Test client
    :return: The user's auth headers and ID
    """
    name = f"stats_{uuid4().hex[:8]}"
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
    """Register and log in a new user, return its auth headers and ID."""
    return register_and_login(client)


def add_review(
    cursor: RealDictCursor,
    book_dao: BookDAO,
    id_user: int,
    rating: int,
) -> None:
    """Create a book and insert a review of it with the given rating.

    :param cursor: Test cursor
    :param book_dao: DAO used to create the book
    :param id_user: ID of the author of the review
    :param rating: Rating of the review, from 1 to 5
    """
    book = book_dao.create(BookCreate(title="Reviewed book"))
    cursor.execute(
        "INSERT INTO reviews (id_user, id_book, rating) VALUES (%s, %s, %s)",
        (id_user, book.id_book, rating),
    )


def add_library_book(
    client: TestClient,
    book_dao: BookDAO,
    headers: dict[str, str],
    state: str,
    num_pages: int | None = None,
) -> None:
    """Create a book and add it to a user's library through the API.

    :param client: Test client
    :param book_dao: DAO used to create the book
    :param headers: Auth headers of the user
    :param state: Reading state of the book
    :param num_pages: Number of pages of the book
    """
    book = book_dao.create(BookCreate(title="Book", num_pages=num_pages))
    response = client.post(
        LIBRARY_BOOKS_URL,
        headers=headers,
        json={"id_book": book.id_book, "state": state},
    )
    assert response.status_code == status.HTTP_201_CREATED


class TestReadMyStatsRoute:
    """Integration tests for GET /api/users/me/stats."""

    def test_new_user(
        self,
        client: TestClient,
        me: tuple[dict[str, str], int],
    ) -> None:
        """New user: 200 OK, nothing finished, no genre, five 0 ratings."""
        response = client.get(STATS_URL, headers=me[0])

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "books_finished": 0,
            "pages_read": 0,
            "genres": [],
            "ratings": NO_RATINGS,
        }

    def test_stats_from_library(
        self,
        client: TestClient,
        book_dao: BookDAO,
        me: tuple[dict[str, str], int],
    ) -> None:
        """Books finished and genres come from the user's library."""
        books = (
            ("Fantasy", "COMPLETED"),
            ("Fantasy", "READING"),
            ("Sci-Fi", "COMPLETED"),
            ("Sci-Fi", "WANT_TO_READ"),
        )
        for category, state in books:
            book = book_dao.create(BookCreate(title="Book", category=category))
            client.post(
                LIBRARY_BOOKS_URL,
                headers=me[0],
                json={"id_book": book.id_book, "state": state},
            )

        data = client.get(STATS_URL, headers=me[0]).json()

        states = [state for _, state in books]
        assert data["books_finished"] == states.count("COMPLETED")
        assert data["genres"] == [
            {"category": "Fantasy", "count": 2},
            {"category": "Sci-Fi", "count": 1},
        ]

    def test_pages_read_counts_completed_books(
        self,
        client: TestClient,
        book_dao: BookDAO,
        me: tuple[dict[str, str], int],
    ) -> None:
        """The pages of the completed books are added up."""
        for num_pages in (SHORT_BOOK_PAGES, LONG_BOOK_PAGES):
            add_library_book(client, book_dao, me[0], "COMPLETED", num_pages)

        data = client.get(STATS_URL, headers=me[0]).json()

        assert data["pages_read"] == SHORT_BOOK_PAGES + LONG_BOOK_PAGES

    @pytest.mark.parametrize(
        "state",
        ["READING", "WANT_TO_READ", "ABANDONED"],
    )
    def test_pages_read_ignores_non_completed_books(
        self,
        client: TestClient,
        book_dao: BookDAO,
        me: tuple[dict[str, str], int],
        state: str,
    ) -> None:
        """A book that is not completed does not count."""
        add_library_book(client, book_dao, me[0], state, LONG_BOOK_PAGES)

        data = client.get(STATS_URL, headers=me[0]).json()

        assert data["pages_read"] == 0

    def test_pages_read_book_without_page_count(
        self,
        client: TestClient,
        book_dao: BookDAO,
        me: tuple[dict[str, str], int],
    ) -> None:
        """A completed book without a page count counts as 0."""
        add_library_book(client, book_dao, me[0], "COMPLETED")
        add_library_book(
            client,
            book_dao,
            me[0],
            "COMPLETED",
            SHORT_BOOK_PAGES,
        )

        data = client.get(STATS_URL, headers=me[0]).json()

        assert data["books_finished"] == len(("no pages", "short"))
        assert data["pages_read"] == SHORT_BOOK_PAGES

    def test_ratings_from_reviews(
        self,
        client: TestClient,
        cursor: RealDictCursor,
        book_dao: BookDAO,
        me: tuple[dict[str, str], int],
    ) -> None:
        """The rating distribution comes from the user's reviews."""
        for rating in (4, 4, 5):
            add_review(cursor, book_dao, me[1], rating)

        data = client.get(STATS_URL, headers=me[0]).json()

        assert data["ratings"] == [
            {"rating": 1, "count": 0},
            {"rating": 2, "count": 0},
            {"rating": 3, "count": 0},
            {"rating": 4, "count": 2},
            {"rating": 5, "count": 1},
        ]

    def test_other_user_data_not_counted(
        self,
        client: TestClient,
        cursor: RealDictCursor,
        book_dao: BookDAO,
        user_dao: UserDAO,
        me: tuple[dict[str, str], int],
    ) -> None:
        """The reviews and books of another user are not counted."""
        other = user_dao.create(
            UserCreate(
                username=f"other_{uuid4().hex[:8]}",
                email=f"other_{uuid4().hex[:8]}@ensai.fr",
                password_hash="fakehash",
            ),
        )
        add_review(cursor, book_dao, other.id_user, 5)

        response = client.get(STATS_URL, headers=me[0])

        assert response.json()["ratings"] == NO_RATINGS

    def test_unauthorized(self, client: TestClient) -> None:
        """Missing token: 401 Unauthorized."""
        response = client.get(STATS_URL)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestGetUserStatsRoute:
    """Integration tests for GET /api/users/{user_id}/stats."""

    def test_friend_stats_include_pages_read(
        self,
        client: TestClient,
        book_dao: BookDAO,
        me: tuple[dict[str, str], int],
    ) -> None:
        """The pages read by a user I follow are returned."""
        friend_headers, friend_id = register_and_login(client)
        add_library_book(
            client,
            book_dao,
            friend_headers,
            "COMPLETED",
            LONG_BOOK_PAGES,
        )
        add_library_book(
            client,
            book_dao,
            friend_headers,
            "READING",
            SHORT_BOOK_PAGES,
        )
        followed = client.post(
            f"{USERS_URL}/{friend_id}/follow",
            headers=me[0],
        )
        assert followed.status_code == status.HTTP_204_NO_CONTENT

        response = client.get(
            f"{USERS_URL}/{friend_id}/stats",
            headers=me[0],
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["books_finished"] == 1
        assert data["pages_read"] == LONG_BOOK_PAGES
        mine = client.get(STATS_URL, headers=me[0]).json()
        assert mine["pages_read"] == 0

    def test_not_following(
        self,
        client: TestClient,
        me: tuple[dict[str, str], int],
    ) -> None:
        """A user I do not follow: 403 Forbidden."""
        _, stranger_id = register_and_login(client)

        response = client.get(
            f"{USERS_URL}/{stranger_id}/stats",
            headers=me[0],
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
