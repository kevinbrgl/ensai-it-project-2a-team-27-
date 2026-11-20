# 📚 Ex-Libris

Ex-Libris is a reading journal built by ENSAI 2A team 27. Search for a book, mark it as finished, review it and see how your reading changes over time. You can also organize books into playlists and follow other readers.

## Run the app

Install [uv](https://docs.astral.sh/uv/) and have a PostgreSQL 15 or later database available. The compiled React app is included in the repository. Python 3.13 and its dependencies are installed by uv.

<details>
<summary>📦 Install uv</summary>

```bash
# Mac / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

```powershell
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```
</details>

**1. Install the project.** Run these commands at the repository root on first setup. If you already have a configured `.env`, skip the copy.

```bash
uv sync --locked
cp .env.example .env
```

On Windows, use `Copy-Item .env.example .env` for the second command.

**2. Connect your database.** Fill in the five `POSTGRES_*` values in `.env` with the connection details from your PostgreSQL service. This command generates a value for `SECRET_KEY`.

```bash
uv run python -c "import secrets; print(secrets.token_urlsafe(32))"
```

For a local installation, set `ROOT_PATH=/` in `.env`. On Onyxia, keep the default proxy path. To start a database on your computer with Docker, use the [local database setup](src/README.md#local-database-with-docker).

**3. Choose your starting library.** Load the sample data from the repository root to try the demo.

```bash
uv run python -m src.seed_demo
```

Sign in as **`demo_alex`** or **`demo_jo`** with the password **`ExLibrisDemo27`**. Alex has finished *Dune* and *Frankenstein*, is reading *Pride and Prejudice*, and follows Jo. Open **My library**, **Progress** or the **Book club picks** playlist to explore. For your own empty library, skip the demo and choose **Create account** in the app.

**4. Start the API and the web app.** From the repository root, run each command in its own terminal.

```bash
uv run src/main.py
```

```bash
uv run python frontend/app.py
```

Open **http://localhost:5000**. On Onyxia, append `/proxy/5000/` to your VS Code URL. The API documentation is at **http://127.0.0.1:8000** or `/proxy/8000/` on Onyxia. The schema is created automatically on startup. Press Ctrl+C in each terminal to stop.

## Troubleshooting

| What you see | What to check |
|---|---|
| The API cannot connect to PostgreSQL | Check that the database is running and that all five `POSTGRES_*` values in the root `.env` match your connection. |
| “Cannot reach the backend” | Start the API in the first terminal. The frontend forwards requests to port 8000 by default. |
| Port 5000 is already in use | Set `FRONTEND_PORT=5001` when starting the web app, then open port 5001. |
| “Open Library service is unavailable” | Book search needs a connection to Open Library. Your existing library, reviews and reading statistics are stored in PostgreSQL. |
| Installing psycopg2 fails because headers are missing | Install the PostgreSQL development headers (`libpq-dev` on Debian/Ubuntu or `libpq` on macOS), then run `uv sync --locked` again. |

## Development

The [backend developer guide](src/README.md) covers database setup, the route-to-query workflow, tests and quality checks. The [frontend developer guide](frontend/README.md) covers React development, the Onyxia proxy and rebuilding the bundled app.
