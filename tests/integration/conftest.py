"""Fixtures for integration tests against the configured PostgreSQL database.

Each test uses a cursor whose transaction is rolled back during teardown.
"""

from collections.abc import Generator
from pathlib import Path

import psycopg2
import pytest
from fastapi.testclient import TestClient
from psycopg2.extensions import connection
from psycopg2.extras import RealDictCursor

from src.api.deps import get_cursor
from src.core.config import settings
from src.dao.books_dao import BookDAO
from src.dao.users_dao import UserDAO
from src.main import app

INIT_SQL = Path(__file__).resolve().parents[2] / "data" / "init.sql"


@pytest.fixture(scope="session")
def db_conn() -> Generator[connection]:
    """Open a PostgreSQL connection for the test session.

    Initialize missing tables before the first test and close the connection
    at the end of the session.

    Yields
    ------
    connection
        Active connection to the configured test database.

    """
    conn = psycopg2.connect(settings.postgres_dsn.unicode_string())
    with conn, conn.cursor() as cur:
        cur.execute(INIT_SQL.read_text(encoding="utf-8"))
    yield conn
    conn.close()


@pytest.fixture
def cursor(db_conn: connection) -> Generator[RealDictCursor]:
    """Open a cursor for one test and roll back its transaction afterward.

    Parameters
    ----------
    db_conn : connection
        Shared database connection for the test session.

    Yields
    ------
    RealDictCursor
        Cursor that returns query results as dictionaries.

    """
    with db_conn.cursor(cursor_factory=RealDictCursor) as cur:
        yield cur
    db_conn.rollback()


@pytest.fixture
def user_dao(cursor: RealDictCursor) -> UserDAO:
    """Return a UserDAO bound to the test transaction."""
    return UserDAO(cursor)


@pytest.fixture
def book_dao(cursor: RealDictCursor) -> BookDAO:
    """Return a BookDAO bound to the test transaction."""
    return BookDAO(cursor)


@pytest.fixture
def client(cursor: RealDictCursor) -> Generator[TestClient]:
    """Provide a FastAPI test client backed by the test cursor.

    The override supplies the cursor to routes without starting the
    application's database pool. Teardown clears the dependency overrides.

    Parameters
    ----------
    cursor : RealDictCursor
        Cursor for the transaction rolled back after the test.

    Yields
    ------
    TestClient
        Client for requests to the integration test application.

    """

    def override_get_cursor() -> RealDictCursor:
        """Return the cursor for the current test transaction."""
        return cursor

    app.dependency_overrides[get_cursor] = override_get_cursor
    yield TestClient(app)
    app.dependency_overrides.clear()
