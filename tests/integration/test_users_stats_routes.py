"""Integration tests for GET /api/users/me/stats.

The route is called through FastAPI's TestClient (fixture "client" from
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
REGISTER_URL = f"{settings.API_STR}/auth/register"
LOGIN_URL = f"{settings.API_STR}/auth/login"
LIBRARY_BOOKS_URL = f"{settings.API_STR}/library/books"
PASSWORD = "motdepasse123"
NO_RATINGS = [{"rating": rating, "count": 0} for rating in range(1, 6)]


@pytest.fixture
def me(client: TestClient) -> tuple[dict[str, str], int]:
    """Register and log in a new user, return its auth headers and ID."""
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