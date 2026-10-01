
from collections.abc import Generator
from pathlib import Path
from typing import Any

import psycopg2
import pytest
from psycopg2.extensions import connection
from psycopg2.extras import RealDictCursor

PGUSER = "test_user"
PGPASSWORD = "test_pass"
PGHOST = "localhost"
PGPORT = 5433
DBNAME = "test_db"
SCHEMA_PATH = "data/init.sql"
TABLES_LIST = "users, items"


@pytest.fixture(scope="session")
def db_conn() -> Generator[connection, Any, Any]:
    conn = psycopg2.connect(
        dbname=DBNAME,
        user=PGUSER,
        password=PGPASSWORD,
        host=PGHOST,
        port=PGPORT,
    )
    yield conn
    with conn.cursor() as cur:
        cur.execute(f"DROP TABLE IF EXISTS {TABLES_LIST};")
    conn.commit()
    conn.close()


@pytest.fixture(scope="session", autouse=True)
def setup_schema(db_conn: connection) -> None:
    with db_conn.cursor() as cur, Path(SCHEMA_PATH).open(encoding="utf8") as f:
        cur.execute(f.read())
    db_conn.commit()


@pytest.fixture
def db_cursor(db_conn: connection) -> Generator[RealDictCursor, Any, Any]:
    with db_conn.cursor(cursor_factory=RealDictCursor) as cur:
        yield cur
    db_conn.rollback()
