# Ex-Libris backend developer guide

The API uses FastAPI, Pydantic and PostgreSQL. Run the commands below from the repository root, where uv finds `pyproject.toml`, `uv.lock` and the application's `.env`.

## Local database with Docker

The supplied Compose file starts PostgreSQL 15 on port 5433.

```bash
docker compose -f docker-compose.test.yml up -d
docker compose -f docker-compose.test.yml exec test_postgres pg_isready -U test_user -d test_db
```

Once PostgreSQL reports that it is accepting connections, run `uv sync --locked` and copy `.env.example` to `.env` on first setup. Use these values for the Docker database.

```dotenv
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5433
POSTGRES_DATABASE=test_db
POSTGRES_USER=test_user
POSTGRES_PASSWORD=test_pass
ROOT_PATH=/
```

Set `SECRET_KEY` to the output of `uv run python -c "import secrets; print(secrets.token_urlsafe(32))"`. For an existing PostgreSQL database, use its connection details. On Onyxia, the default `ROOT_PATH=/proxy/8000` serves Swagger through the VS Code proxy. Keep credentials in the git-ignored root `.env`.

## Schema and demo data

`uv run src/main.py` starts the API with auto-reload on port 8000. On startup the application opens its connection pool and applies [init.sql](../data/init.sql). The configured database must already exist and the configured role must be able to create its tables.

Run the demo loader from the repository root.

```bash
uv run python -m src.seed_demo
```

The command applies the schema and [sample data](../data/seed.sql) in one transaction. It can run before the API starts. It uses Open Library work keys and the database's uniqueness constraints to reuse existing records when run again. The demo includes two regular readers, four books, five library entries, three reviews, a follow and a playlist. Both readers (`demo_alex` and `demo_jo`) use the local demo password `ExLibrisDemo27`.

To try moderation on a development database, sign up with your own account and run the following SQL with your chosen username.

```sql
UPDATE users SET is_admin = TRUE WHERE username = '<your-username>';
```

## Follow a book search through the code

1. In the Swagger UI, register a user with `POST /api/auth/register` or use a demo reader. Click **Authorize** and enter the username and password.
2. Call `GET /api/books/search?q=Dune&limit=3`. The [books route](api/routes/books_routes.py) validates the query. FastAPI resolves the authenticated reader and the request-scoped service through [deps.py](api/deps.py).
3. [BookService](services/books_service.py) asks [OpenLibraryClient](services/open_library_client.py) for matching works. The client handles HTTP and remote errors. The service maps each result to a `BookCreate` model, including its author, first subject, publication year and page count.
4. [BookDAO](dao/books_dao.py) inserts or updates the work by its Open Library key and returns its local `id_book`. The request commits on success and rolls back on error. Use the returned ID with `POST /api/library/books` or `GET /api/books/{book_id}`.

Other domains follow the same directory layout. The [user DAO](dao/users_dao.py) handles accounts and settings. It delegates follow queries to [FollowDAO](dao/follows_dao.py) using the same request cursor.

## Tests and code quality

| Command | What it checks |
|---|---|
| `uv run pytest tests/unit` | Services and routes with mocked dependencies. The settings in `.env` are needed at import time. |
| `uv run pytest tests/integration` | DAO queries and HTTP routes against the configured PostgreSQL instance. |
| `uv run pytest --cov=src` | Both suites and Python statement coverage. |
| `uv run ruff check` | Python lint rules. |
| `uv run mypy src tests frontend/app.py` | Types for the backend, tests and Python frontend server. |

Integration tests use the database configured in `.env`. The fixtures apply the schema once and roll back the transaction for each test. External Open Library responses are mocked so the tests can run offline after dependencies are installed. Stop the local database with `docker compose -f docker-compose.test.yml stop`.
