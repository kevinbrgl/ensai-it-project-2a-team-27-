"""Load the sample reading journals into the configured PostgreSQL database."""

import sys
from contextlib import closing

import psycopg2
from psycopg2.extensions import cursor

from src.core.config import settings
from src.core.db import INIT_SQL


def load_demo(cur: cursor) -> None:
    """Apply the schema and sample data using the caller's transaction."""
    cur.execute(INIT_SQL.read_text(encoding="utf-8"))
    cur.execute(INIT_SQL.with_name("seed.sql").read_text(encoding="utf-8"))


def main() -> None:
    """Create the schema and load the demo in one transaction."""
    dsn = settings.postgres_dsn.unicode_string()
    with closing(psycopg2.connect(dsn)) as conn, conn, conn.cursor() as cur:
        load_demo(cur)
    sys.stdout.write("Demo ready. Sign in as demo_alex or demo_jo.\n")


if __name__ == "__main__":
    main()
