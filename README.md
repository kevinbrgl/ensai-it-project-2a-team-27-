# Ex-Libris 📚

Ex-Libris is a digital reading journal built with React, FastAPI, and PostgreSQL. Use it to organize your library, track your progress with reading statistics, follow other readers, and share book reviews.

## Prerequisites

- Python 3.13+ (uv installs it automatically)
- PostgreSQL 15+ (on Onyxia, a PostgreSQL service)
- uv (Python package manager)

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/kevinbrgl/ensai-it-project-2a-team-27-.git
cd ensai-it-project-2a-team-27-
```

### 2. Install uv (if it isn't already installed)

```bash
# macOS and Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 3. Sync the dependencies

```bash
uv sync --locked
```

This command creates a virtual environment and installs the exact dependency versions listed in `uv.lock`.

### 4. Configure the database

Create your `.env` file from the template at the root of the project:

```bash
cp .env.example .env
```

On Windows, run `Copy-Item .env.example .env` instead.

Then fill in `.env` with the connection details of your PostgreSQL service:

```dotenv
# PostgreSQL configuration
POSTGRES_HOST=<postgresql-host>
POSTGRES_PORT=5432
POSTGRES_DATABASE=defaultdb
POSTGRES_USER=<postgresql-user>
POSTGRES_PASSWORD=<postgresql-password>

# JWT configuration
SECRET_KEY=<generated-secret-key>

# Uncomment to open the Swagger page locally instead of through Onyxia.
# ROOT_PATH=/
```

Generate a value for `SECRET_KEY` with:

```bash
uv run python -c "import secrets; print(secrets.token_urlsafe(32))"
```

`.env` is git-ignored, so your credentials stay on your machine.

✅ **You can now go straight to [Running the application](#running-the-application), or load the sample data first (step 5).**

### 5. Optional: load the sample data

> [!NOTE]
> This step is optional. Skip it to start with an empty database and create your own account in the app.

```bash
uv run python -m src.seed_demo
```

Sign in as **`demo_alex`** or **`demo_jo`** with the password **`ExLibrisDemo27`**. Alex has finished *Dune* and *Frankenstein*, is reading *Pride and Prejudice*, follows Jo and owns the **Book club picks** playlist. Jo is an **administrator**: sign in as demo_jo to try moderation on Alex's profile and reviews.

## Running the application

Start the API, then start the web app in a second terminal:

```bash
uv run src/main.py
```

```bash
uv run python frontend/app.py
```

The web app is available at http://localhost:5000. On Onyxia, open your VS Code URL followed by `/proxy/5000/`. The database schema is created automatically when the API starts.

## Administrator rights

Administrators can suspend or ban readers and remove any review. No API endpoint grants these rights. To make an existing account an administrator, run this command from the root of the project:

```bash
uv run python -m src.make_admin <username>
```

Replace `<username>` with the account's username, then reload the web app. A moderation menu then appears on other readers' profiles and next to their reviews on book pages. In the sample data, `demo_jo` is already an administrator.

## API documentation

Once the API is running, open the interactive documentation:

- Swagger UI on Onyxia: your VS Code URL followed by `/proxy/8000/`
- Swagger UI locally (with `ROOT_PATH=/`): http://127.0.0.1:8000

## Running the tests

```bash
# All tests
uv run pytest

# With code coverage
uv run pytest --cov=src

# Specific tests
uv run pytest tests/unit/services/test_books_service.py
```

Unit tests in `tests/unit` use mocks and don't need a database. Integration tests in `tests/integration` run against the database in `.env` and roll back their changes.

## Project structure

```text
ensai-it-project-2a-team-27-/
├── src/
│   ├── main.py              # Application entry point
│   ├── seed_demo.py         # Sample data loader
│   ├── make_admin.py        # Grants administrator rights to an account
│   ├── api/                 # API layer (routes and dependencies)
│   ├── services/            # Business logic and Open Library client
│   ├── dao/                 # Data access layer
│   ├── models/              # Pydantic models
│   ├── core/                # Settings, database pool and security
│   └── utils/               # Domain exceptions
├── frontend/                # React web app (compiled in dist/, served by app.py)
├── data/                    # Database schema (init.sql) and sample data (seed.sql)
├── tests/                   # Unit and integration tests
├── .env.example             # Environment variable template
├── pyproject.toml           # Project configuration
└── README.md
```

For details, see the [backend guide](src/README.md) and the [frontend guide](frontend/README.md).

## Main features

- 🔐 JWT authentication
- 🔍 Book search through Open Library
- 📖 Personal library with reading statuses, likes and favorites
- ⭐ Ratings and reviews
- 📚 Book playlists
- 👥 Following other readers, with public and private profiles
- 📊 Reading statistics, genre wheel, quests and achievements
- ✨ Personalized book recommendations
- 🛡️ Admin moderation (suspensions, bans and review removal)

## Code quality

The project uses Ruff for linting and mypy for type checking. The CI runs both on every push:

```bash
# Check the code
uv run ruff check

# Check the types
uv run mypy src tests frontend/app.py
```

## Common issues

**The API cannot connect to PostgreSQL**
- Check that the `POSTGRES_*` values in `.env` match your PostgreSQL service
- Run every command from the root of the project, where `.env` is located

**Module import error**
- Run `uv sync --locked` to sync the dependencies
- Make sure you launch commands with `uv run`
