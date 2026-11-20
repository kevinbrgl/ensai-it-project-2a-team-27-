"""Database connection pool initialization for FastAPI."""

from pathlib import Path

from fastapi import FastAPI
from psycopg2.pool import ThreadedConnectionPool

from src.core.config import settings

INIT_SQL = Path(__file__).resolve().parents[2] / "data" / "init.sql"


def init_pool(app: FastAPI) -> None:
    """Initialize the PostgreSQL connection pool and attach it to the app.

    Parameters
    ----------
    app : FastAPI
        Application whose state will hold the connection pool.

    """
    app.state.db_pool = ThreadedConnectionPool(
        minconn=1,
        maxconn=5,
        dsn=settings.postgres_dsn.unicode_string(),
    )


def close_pool(app: FastAPI) -> None:
    """Close all connections in the application's PostgreSQL pool.

    Parameters
    ----------
    app : FastAPI
        Application whose connection pool will be closed.

    """
    app.state.db_pool.closeall()
