"""Main entry point for the FastAPI application.

Initializes the database connection pool, sets up the application lifespan,
and includes API routers.
"""

import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI

if __name__ == "__main__":
    root_dir = Path(__file__).parent.parent
    sys.path.insert(0, str(root_dir))

from src.api.main import api_router
from src.core.config import settings
from src.core.db import close_pool, init_pool

INIT_SQL = Path(__file__).resolve().parent.parent / "data" / "init.sql"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Open the DB pool, create missing tables, close the pool at shutdown."""
    init_pool(app)
    pool = app.state.db_pool
    conn = pool.getconn()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(INIT_SQL.read_text(encoding="utf-8"))
    finally:
        pool.putconn(conn)
    try:
        yield
    finally:
        close_pool(app)


app = FastAPI(
    title="API Ex-Libris",
    description="API REST de suivi de lecture",
    version="1.0.0",
    docs_url="/",  # Swagger UI accessible directement à la racine
    redoc_url=None,  # Désactive ReDoc
    root_path=settings.ROOT_PATH,
    lifespan=lifespan,
)

app.include_router(api_router)

if __name__ == "__main__":
    """Run the FastAPI application with Uvicorn when executed as a script."""
    uvicorn.run("src.main:app", host="127.0.0.1", port=8000, reload=True)
