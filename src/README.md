# Ex-Libris backend

This is the REST API behind Ex-Libris. It is built with FastAPI, Pydantic and PostgreSQL, and it stores readers' libraries, reviews, playlists and follows. It also searches Open Library and computes statistics, quests, achievements and recommendations. This guide is for developers working on the Python backend. To run the whole app, see the [main README](../README.md).

## Features

All endpoints are under `/api`. Every endpoint except register and login requires an `Authorization: Bearer <token>` header.

| Area | Prefix | Main capabilities |
|---|---|---|
| Auth | `/auth` | Register, sign in with form data and sign out. Sign-out revokes the token. |
| Books | `/books` | Search Open Library (`/search?q=&limit=`), browse the local catalog by `category` or `author`, and get one book with editions fetched live from Open Library |
| Library | `/library` | Add and remove books, change the reading status, set reading dates, toggle likes and favorites, list books and favorites |
| Reviews | `/books/{id}/reviews`, `/reviews/{id}`, `/users/{id}/reviews` | Rate from 1 to 5 and comment, with one review per reader per book. Edit or delete your own review. |
| Playlists | `/playlists` | Create, rename, delete and view playlists. Add and remove books. |
| Users | `/users` | Edit your profile, settings and password. Search readers, follow and unfollow them, and see followers and following. View other readers' libraries, playlists and statistics, subject to profile visibility and follow rules. Get quests, achievements and genre wheels. |
| Recommendations | `/recommendations` | Suggestions from your favorite genres, or by `genre`, sorted by `rating`, `new` or `title` |
| Admin | `/admin` | Suspend or ban an account and delete a review. Requires `is_admin`. |

Request handling details:

- **Transactions:** each request gets one cursor from a `ThreadedConnectionPool` with 1 to 5 connections. The request commits on success and rolls back on error ([api/deps.py](api/deps.py)).
- **Authentication:** passwords are hashed with bcrypt, tokens are HS256 JWTs, and revoked tokens are checked on every request. Banned or suspended accounts are rejected even if their token is still valid. Hashing and token creation are in [core/security.py](core/security.py), and the per-request checks are in [api/deps.py](api/deps.py).
- **Open Library:** [services/open_library_client.py](services/open_library_client.py) uses a 5-second timeout. It caches successful searches for 5 minutes, keeping up to 128 entries.

## Prerequisites and installation

- [uv](https://docs.astral.sh/uv/), which installs Python 3.13 or later from `pyproject.toml`
- PostgreSQL 15 or later. On Onyxia, use a PostgreSQL service.
- On Debian or Ubuntu, `libpq-dev` if building `psycopg2` fails

Run these commands from the **repository root**, where uv finds `pyproject.toml`, `uv.lock` and `.env`:

```bash
uv sync --locked
cp .env.example .env
```

## Configuration

Settings are defined in [core/config.py](core/config.py) and read from `.env` in the current working directory. Empty values are ignored.

| Variable | Required | Default | Description |
|---|---|---|---|
| `POSTGRES_HOST` | yes | — | Database host |
| `POSTGRES_PORT` | yes | — | Database port |
| `POSTGRES_DATABASE` | yes | — | Existing database name |
| `POSTGRES_USER` | yes | — | Role that can create tables |
| `POSTGRES_PASSWORD` | yes | — | Role password |
| `SECRET_KEY` | yes | — | JWT signing key |
| `ROOT_PATH` | no | `/proxy/8000` | Path prefix for Swagger. Use `/` locally and keep the default on Onyxia. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | no | `11520` | Token lifetime in minutes (8 days) |

Example `.env` on Onyxia. Replace each placeholder with the connection details of your PostgreSQL service, and leave `ROOT_PATH` unset:

```dotenv
POSTGRES_HOST=<postgresql-service-host>
POSTGRES_PORT=5432
POSTGRES_DATABASE=defaultdb
POSTGRES_USER=<postgresql-user>
POSTGRES_PASSWORD=<postgresql-password>
SECRET_KEY=<paste-generated-secret-here>
```

Generate a value for `SECRET_KEY`:

```bash
uv run python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Keep credentials in the root `.env`, which git ignores.

## Usage

### Run the API

```bash
uv run src/main.py
```

Uvicorn serves `src.main:app` on `127.0.0.1:8000` and reloads when files change. On startup the app opens the connection pool and applies [data/init.sql](../data/init.sql). The script uses `CREATE TABLE IF NOT EXISTS` and `ADD COLUMN IF NOT EXISTS`, so running it on an existing database is safe. Swagger UI is at the root URL (`/`), and ReDoc is disabled.

To debug, use the **Back-end FastAPI** configuration in [.vscode/launch.json](../.vscode/launch.json).

---

### 📦 Optional: load the sample data

> [!NOTE]
> **This step is optional.** It adds two demo readers to the configured database. Skip it if you want an empty database.

```bash
uv run python -m src.seed_demo
```

[seed_demo.py](seed_demo.py) runs [data/init.sql](../data/init.sql), then [data/seed.sql](../data/seed.sql), in one transaction. You can run it before the API has ever started.

| Content | Count |
|---|---|
| Readers (`demo_alex`, and `demo_jo` who is an administrator, password `ExLibrisDemo27`) | 2 |
| Books (*Dune*, *Frankenstein*, *The Hobbit*, *Pride and Prejudice*) | 4 |
| Library entries | 5 |
| Reviews | 3 |
| Follows (Alex follows Jo) | 1 |
| Playlists (Alex's **Book club picks**, with 2 books) | 1 |

- Books are matched by Open Library work key and other rows by their unique constraints, so a second run keeps existing rows and reader edits. [tests/integration/test_seed_demo.py](../tests/integration/test_seed_demo.py) checks this.
- If either username belongs to an account with a different email, the whole load is rolled back.
- The password is public, so use the sample data on local databases only.

---

### Follow a book search through the code

1. In Swagger, register with `POST /api/auth/register` or use a demo reader. Click **Authorize** and enter the username and password.
2. Call `GET /api/books/search?q=Dune&limit=3`. The [books route](api/routes/books_routes.py) validates the query, and [deps.py](api/deps.py) resolves the current user and a request-scoped `BookService`.
3. [BookService](services/books_service.py) asks [OpenLibraryClient](services/open_library_client.py) for matching works and maps each result to a `BookCreate` model.
4. [BookDAO](dao/books_dao.py) inserts or updates each work by its Open Library key and returns its local `id_book`. Use that ID with `POST /api/library/books` or `GET /api/books/{book_id}`.

The other areas follow the same route → service → DAO pattern.

### Grant administrator rights

No endpoint grants administrator rights. From the repository root, promote an existing account with:

```bash
uv run python -m src.make_admin <username>
```

[make_admin.py](make_admin.py) sets `is_admin` in the database configured in `.env`, and exits with an error if no account has that username. The web app reads the flag when it loads, so reload it afterwards. In the sample data, `demo_jo` is already an administrator.

## Project structure

```text
src/
├── main.py              # FastAPI app, lifespan (pool + init.sql), Uvicorn runner
├── seed_demo.py         # Optional sample-data loader
├── make_admin.py        # Grants administrator rights to an account
├── api/
│   ├── main.py          # /api router that includes every route module
│   ├── deps.py          # Cursor, service factories, current user, admin check
│   └── routes/          # auth, books, library, playlists, reviews, users, recommendations, admin
├── services/            # Business rules: one service per area, plus open_library_client.py
├── dao/                 # SQL for each table or feature (users, follows, books, library, stats…)
├── models/              # Pydantic request and response models
├── core/
│   ├── config.py        # Settings loaded from .env
│   ├── db.py            # Connection pool and path to data/init.sql
│   └── security.py      # bcrypt hashing and JWT creation
└── utils/exceptions.py  # Domain exceptions mapped to HTTP errors in routes
```

## Contributing and license

Run these commands from the repository root:

| Command | What it checks |
|---|---|
| `uv run ruff check` | Lint with every Ruff rule selected and a 79-character line length |
| `uv run mypy src tests frontend/app.py` | Types, with the Pydantic plugin |
| `uv run pytest tests/unit` | Routes and services with mocked dependencies. Needs `.env`, but not a database. |
| `uv run pytest tests/integration` | DAOs and HTTP routes against the PostgreSQL database in `.env` |
| `uv run pytest --cov=src` | Both suites with coverage |

The integration fixtures in [tests/integration/conftest.py](../tests/integration/conftest.py) apply the schema once, then roll back each test's transaction. Open Library responses are mocked, so the tests run offline. Point `.env` at a dedicated test database rather than a shared one.

When you add an endpoint, follow the existing layers: add the route in `api/routes/`, the service in `services/`, the SQL in `dao/` and the models in `models/`. Register a new route module in [api/main.py](api/main.py) and add unit tests under `tests/unit/`. [CI](../.github/workflows/ci.yml) runs Ruff, mypy and both test suites on every push and pull request.

**License:** GNU General Public License v3.0. See [LICENSE](../LICENSE).
