"""Main entry point for the FastAPI application.

Initializes the database connection pool, sets up the application lifespan,
and includes API routers.
"""

import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

if __name__ == "__main__":
    root_dir = Path(__file__).parent.parent
    sys.path.insert(0, str(root_dir))

from src.api.main import api_router
from src.core.config import settings
from src.core.db import INIT_SQL, close_pool, init_pool


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Manage the database connection pool over the application lifespan.

    Run the database initialization script before serving requests and
    close the pool when the application shuts down.

    Parameters
    ----------
    app : FastAPI
        Application whose state holds the connection pool.

    Yields
    ------
    None
        Control to FastAPI once database initialization is complete.

    """
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
    title="Ex-Libris API",
    description="REST API for tracking your reading",
    version="1.0.0",
    docs_url="/",  # Serve Swagger UI at the root URL
    redoc_url=None,  # Disable ReDoc
    root_path=settings.ROOT_PATH,
    lifespan=lifespan,
)

app.include_router(api_router)


@app.exception_handler(RequestValidationError)
async def handle_request_validation_error(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Keep field errors without echoing submitted request body values."""
    errors = [
        {key: value for key, value in error.items() if key != "input"}
        if error["loc"] and error["loc"][0] == "body"
        else error
        for error in exc.errors()
    ]
    return await request_validation_exception_handler(
        request,
        RequestValidationError(errors),
    )


if __name__ == "__main__":
    # Run the application with Uvicorn when executed as a script.
    uvicorn.run("src.main:app", host="127.0.0.1", port=8000, reload=True)
