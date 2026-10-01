"""Main entry point for the FastAPI application.

Initializes the database connection pool, sets up the application lifespan,
and includes API routers.
"""

import sys
# from collections.abc import AsyncGenerator
# from contextlib import asynccontextmanager
from pathlib import Path
# from typing import TYPE_CHECKING, Any

import uvicorn
from fastapi import FastAPI

if __name__ == "__main__":
    root_dir = Path(__file__).parent.parent
    sys.path.insert(0, str(root_dir))

from src.api.main import api_router
from src.core.config import settings
# from src.core.db import init_pool

# if TYPE_CHECKING:
#     from psycopg2.pool import SimpleConnectionPool


# @asynccontextmanager
# async def lifespan(  # noqa: RUF029
#     app: FastAPI,
# ) -> AsyncGenerator[Any, Any]:
#     """Application lifespan context manager.

#     Initializes the database connection pool and executes the SQL init script.
#     Cleans up connections on shutdown.

#     :param app: FastAPI application instance
#     :yields: Async generator for FastAPI lifespan
#     """
#     init_pool(app)
#     pool: SimpleConnectionPool = app.state.db_pool
#     conn = pool.getconn()
#     try:
#         with conn.cursor() as cur:
#             content = Path("data/init.sql").read_text(encoding="utf8")
#             cur.execute(content)
#         conn.commit()
#     finally:
#         pool.putconn(conn)

#     yield

#     pool.closeall()


app = FastAPI(
    title="API Ex-libris",
    description="API REST pour gérer une bibliothèque de films",
    version="1.0.0",
    docs_url="/",  # Swagger UI accessible directement à la racine
    root_path=settings.ROOT_PATH,
    redoc_url=None,  # Désactive ReDoc
)

app.include_router(api_router)

if __name__ == "__main__":
    """Run the FastAPI application with Uvicorn when executed as a script."""
    uvicorn.run("src.main:app", host="127.0.0.1", port=8000, reload=True)
