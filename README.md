# 📚 Ex-Libris

> Reading tracker: **FastAPI + PostgreSQL** API · **React** web app
> ENSAI 2A IT project, team 27

---

## ⚡ TL;DR

```bash
uv sync                                  # install everything
cp .env.example .env                     # then fill in the DB settings
uv run src/main.py                       # backend  → :8000
cd frontend && uv run python app.py      # frontend → :5000 (2nd terminal)
uv run pytest                            # tests
```

---

## 🧰 Prerequisites

| Tool | Version | Why |
|---|---|---|
| [uv](https://docs.astral.sh/uv/) | latest | Python 3.13 and all the dependencies |
| PostgreSQL | 15+ | Database (yours, Onyxia's, or Docker) |
| [Node.js](https://nodejs.org/) | ≥ 20.19 | ✏️ **Only to edit the frontend** |

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

---

## 1️⃣ Install

From the project root:

```bash
uv sync
```

This creates `.venv/` with Python 3.13 and all the dependencies.
🔁 Run it again after any `git pull` that changes `pyproject.toml` or `uv.lock`.

---

## 2️⃣ Configure `.env`

```bash
cp .env.example .env          # Windows: Copy-Item .env.example .env
```

```ini
POSTGRES_HOST=<host>
POSTGRES_PORT=5432
POSTGRES_DATABASE=defaultdb
POSTGRES_USER=<user>
POSTGRES_PASSWORD=<password>
SECRET_KEY=<long random string>
```

Generate a `SECRET_KEY`:

```bash
uv run python -c "import secrets; print(secrets.token_urlsafe(32))"
```

> ⚠️ `.env` is git-ignored. **Never commit it.**

---

## 3️⃣ Run the backend

```bash
uv run src/main.py
```

- 🟢 API on **http://127.0.0.1:8000**, with the Swagger docs at the root
- 🗄️ Tables are created automatically from `data/init.sql`
- 🔄 Auto-reloads when you save · stop with `Ctrl+C`

> 🟣 **Onyxia:** open `<your-vscode-url>/proxy/8000/`, not the `127.0.0.1` link.

---

## 4️⃣ Run the frontend

Open a **second terminal** and keep the backend running.

```bash
cd frontend
uv run python app.py
```

➡️ **http://localhost:5000** · Onyxia: `<your-vscode-url>/proxy/5000/`

Create an account and you're in 🎉

`app.py` serves the compiled app (`frontend/dist/`) and forwards `/api/...` to the backend, so you don't need any CORS setup.

```bash
BACKEND_URL=http://127.0.0.1:8000 FRONTEND_PORT=5001 uv run python app.py   # custom port / backend
```

### 👑 Make yourself admin (moderation features)

Sign up in the app, then run this in your database:

```sql
UPDATE users SET is_admin = TRUE WHERE username = '<your-username>';
```

---

## ✏️ Editing the frontend (Node.js)

Only needed if you change files in `frontend/src/`.

<details>
<summary>📦 Install Node.js on Onyxia (no admin rights)</summary>

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
```

```bash
source ~/.bashrc && nvm install 22
```
</details>

```bash
cd frontend
npm install              # first time only
npm run dev -- --host    # live reload on http://localhost:5000
```

Onyxia: set `VITE_BASE_PATH=/absproxy/5000/` in `frontend/.env`, then open `<your-vscode-url>/absproxy/5000/`.

### 🚨 Before you commit

```bash
npm run build                  # regenerate frontend/dist/
git add frontend/src frontend/dist
```

> Always **commit `frontend/dist/` together with your changes**, or everyone else keeps running the old version.
> Merge conflict in `dist/`? Don't edit those files: merge, run `npm run build`, then commit.

<details>
<summary>⚙️ <code>frontend/.env</code> options (optional, <code>cp .env.example .env</code>)</summary>

| Variable | Default | Purpose |
|---|---|---|
| `VITE_BACKEND_URL` | `http://127.0.0.1:8000` | Where `/api` is forwarded |
| `VITE_PORT` | `5000` | Dev server port |
| `VITE_BASE_PATH` | `/` | Sub-path (Onyxia: `/absproxy/5000/`) |
| `VITE_API_URL` | *(empty)* | Leave empty |
</details>

---

## 🧪 Tests

| Command | Runs | DB needed? |
|---|---|---|
| `uv run pytest tests/unit -v` | Unit tests (services + routes, everything mocked) | ❌ |
| `uv run pytest tests/integration -v` | DAO + API tests on a real PostgreSQL | ✅ |
| `uv run pytest -v` | Everything | ✅ |
| `uv run pytest --cov=src --cov-report=term-missing` | Everything + coverage | ✅ |

Integration tests use the DB from `.env`, and **every test is rolled back**, so they leave no trace.
In VS Code: *Testing* panel 🧪 → ↻ → ▶.

### 🐳 Throwaway test database (optional)

```bash
docker compose -f docker-compose.test.yml up -d
```

Then use these values in `.env`:

```ini
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
POSTGRES_DATABASE=test_db
POSTGRES_USER=test_user
POSTGRES_PASSWORD=test_pass
```

---

## 🧹 Code quality

```bash
uv run ruff check                        # lint
uv run ruff check --fix                  # auto-fix
uv run mypy src tests frontend/app.py    # type check
cd frontend && npm run lint              # frontend lint (Node)
```

---

## 🆘 Troubleshooting

| Problem | Fix |
|---|---|
| Browser: `ECONNREFUSED ...:5000` | The frontend isn't running. Start `app.py` (step 4). |
| App: *"Cannot reach the backend"* | The backend isn't running. Run `uv run src/main.py`. |
| App doesn't show your latest frontend change | Run `npm run build` in `frontend/`, then reload. |
| `Address already in use` | Pick another port: `FRONTEND_PORT=5001 uv run python app.py`. On a Mac, port 5000 is often AirPlay. |
| *"Open Library service is unavailable"* | The backend can't reach openlibrary.org (network). |
| `uv sync` fails building **psycopg2** (`pg_config.h`) | Install the PostgreSQL headers: `sudo apt install libpq-dev` (Linux) · `brew install libpq` (Mac) |
| Local Swagger page fails to load `openapi.json` | Add `ROOT_PATH=/` to `.env` (the default `/proxy/8000` is meant for Onyxia). |
| Integration tests can't connect | Check `.env`, or start the Docker test DB. |

---

## 🗂️ Project layout

```
src/
  api/routes/   HTTP routes (auth, books, library, playlists, reviews, users, admin, recommendations)
  services/     business logic
  dao/          SQL queries
  models/       Pydantic models
  core/         config, DB pool, security
frontend/
  app.py        Python server for dist/ + /api proxy
  dist/         compiled app (committed: rebuild with npm run build)
  src/          React app source
tests/
  unit/         mocked tests
  integration/  real-DB tests
data/init.sql   database schema
```