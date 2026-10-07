"""Fixtures for integration tests, run against the real database (.env).

Every test runs inside a transaction that is rolled back at the end,
so nothing a test writes is ever saved in the database.
"""

from collections.abc import Generator
from pathlib import Path

import psycopg2
import pytest
from psycopg2.extensions import connection
from psycopg2.extras import RealDictCursor

from src.core.config import settings
from src.dao.users_dao import UserDAO

INIT_SQL = Path(__file__).resolve().parents[2] / "data" / "init.sql"


@pytest.fixture(scope="session")
def db_conn() -> Generator[connection]:
    """Open one connection to the database for the whole test session.

    Missing tables are created first. init.sql only uses
    CREATE TABLE IF NOT EXISTS, so no existing data is erased.
    """
    conn = psycopg2.connect(settings.postgres_dsn.unicode_string())
    with conn, conn.cursor() as cur:
        cur.execute(INIT_SQL.read_text(encoding="utf-8"))
    yield conn
    conn.close()


@pytest.fixture
def cursor(db_conn: connection) -> Generator[RealDictCursor]:
    """Yield a cursor, then roll back everything the test did."""
    with db_conn.cursor(cursor_factory=RealDictCursor) as cur:
        yield cur
    db_conn.rollback()


@pytest.fixture
def user_dao(cursor: RealDictCursor) -> UserDAO:
    """Return a UserDAO bound to the test cursor."""
    return UserDAO(cursor)
