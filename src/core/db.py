"""Database connection pool initialization for FastAPI."""

from fastapi import FastAPI
from psycopg2.pool import ThreadedConnectionPool

from src.core.config import settings


def init_pool(app: FastAPI) -> None:
    """Initialize the PostgreSQL connection pool and attach it to the app.

    :param app: FastAPI application instance
    """
    app.state.db_pool = ThreadedConnectionPool(
        minconn=1,
        maxconn=5,
        dsn=settings.postgres_dsn.unicode_string(),
    )


def close_pool(app: FastAPI) -> None:
    """Close all connections of the pool.

    :param app: FastAPI application instance
    """
    app.state.db_pool.closeall()
