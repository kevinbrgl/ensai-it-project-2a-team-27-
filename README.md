# Ex-Libris — Reading Tracker API

ENSAI 2nd-year IT project — team 27.

Ex-Libris is a REST API (FastAPI + PostgreSQL) that lets users find books
(through Open Library), add them to their library, track their reading,
and rate and review them.

---

## 1. Install uv

[uv](https://docs.astral.sh/uv/) installs Python and all the project's dependencies.

Windows (PowerShell):

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Mac / Linux (Terminal):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Close and reopen the terminal, then check:

```bash
uv --version
```

---

## 2. Install the dependencies

From the project root:

```bash
uv sync
```

`uv sync` creates the `.venv` folder and installs Python 3.13 and every dependency
listed in `pyproject.toml`. Run it again after any `git pull` that changes
`pyproject.toml` or `uv.lock`.

---

## 3. Create the `.env` file

The `.env` file holds settings and passwords. It is **ignored by Git**:
never commit it. It is read by `src/core/config.py`.

Create it from the template.

Windows (PowerShell):

```powershell
Copy-Item .env.example .env
```

Mac / Linux:

```bash
cp .env.example .env
```

Then fill it in with your PostgreSQL database details:

```ini
POSTGRES_HOST=<database host>
POSTGRES_PORT=5432
POSTGRES_DATABASE=defaultdb
POSTGRES_USER=<user>
POSTGRES_PASSWORD=<password>

SECRET_KEY=<a long random string>
```

**Generate a `SECRET_KEY`** (same command everywhere):

```bash
uv run python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## 4. Run the API and open the documentation

From the project root (same command everywhere):

```bash
uv run src/main.py
```

On startup, the API automatically creates any missing tables from
`data/init.sql`. It restarts by itself every time you save a file.
Stop it with `Ctrl+C`.

:warning: On Onyxia, don't click the `127.0.0.1` link that VSCode suggests: use
your VSCode URL followed by `/proxy/8000/`.

---

## 5. Available endpoints

All routes are prefixed with `/api`. For overall progress, see the
`ex_libris_endpoints.xlsx` spreadsheet in the drive.

| Method | Route | Auth | Status |
|---|---|---|---|
| `POST` | `/api/auth/register` | no | :white_check_mark: done and tested |

### `POST /api/auth/register` — create an account

**Request body**

```json
{
  "username": "yazid",
  "email": "yazid@ensai.fr",
  "password": "motdepasse123"
}
```

| Field | Rule |
|---|---|
| `username` | 3 to 30 characters, unique |
| `email` | valid email format, unique |
| `password` | 8 to 72 characters (72 is bcrypt's limit) |

**Responses**

| Code | When | Body |
|---|---|---|
| `201` | account created | `{"id_user": 1, "username": "yazid", "email": "yazid@ensai.fr", "bio": null, "profile_picture": null}` |
| `409` | username already taken | `{"detail": "Username already used."}` |
| `409` | email already used | `{"detail": "Email already used."}` |
| `422` | invalid data (email, length…) | Pydantic error details |
| `500` | database error | `{"detail": "Could not register user."}` (full cause in the terminal) |

The password is hashed with **bcrypt** before being stored, and **neither the password
nor its hash is ever returned** (filtered by `response_model=UserRead`).

---

## 6. Tests

| Folder | Type | Database | Count |
|---|---|---|---|
| `tests/unit/` | **service** tests, the DAO is replaced by a mock | no | 7 |
| `tests/integration/` | **DAO** tests on a real database | yes (the one in `.env`) | 12 |

Commands (same everywhere):

```bash
uv run pytest tests/unit -v          # fast, no database needed
uv run pytest tests/integration -v   # needs a running PostgreSQL database
uv run pytest -v                     # everything
```

**Integration tests leave no trace**: each test runs inside a transaction
that is rolled back at the end (see `tests/integration/conftest.py`).

**From the VSCode interface**: *Testing* panel (flask icon) → ↻ button, then ▶.

---

## 7. Code quality (ruff, mypy)

```bash
uv run ruff check src tests          # analyse
uv run ruff check src tests --fix    # fix what can be fixed automatically
uv run mypy src                      # type checking
```

---

## 8. Adding a new endpoint: the recipe

### Before you start: create your own branch

Never work directly on `main`. Each endpoint gets its own branch, so your work
doesn't break anyone else's and can be reviewed in a Pull Request.

Same commands on Windows, Mac and Linux:

```bash
git checkout main                    # go back to the main branch
git pull                             # get the latest version of the project
git checkout -b feature/books-search # create your branch and switch to it
```

Name the branch after what you build: `feature/<short-description>`,
for example `feature/auth-login` or `feature/library-add-book`.

Check which branch you are on at any time with `git branch`
(the current one has a `*`).

### The steps

Example with books. Work in this order, from the bottom layer up:

1. **Table**: add `CREATE TABLE IF NOT EXISTS books (...)` at the end of `data/init.sql`.
   :warning: **Never use `DROP TABLE`**: this file runs every time the API starts.
2. **Models**: `src/models/books.py` (input, output, database row).
3. **Exceptions**: add yours to `src/utils/exceptions.py`.
4. **DAO**: `src/dao/books_dao.py`, class `BookDAO(cursor)`.
   Always use `%s` parameters, **never f-strings** with user-provided values.
5. **Service**: `src/services/books_service.py`, class `BookService(dao)`.
6. **Unit tests**: `tests/unit/services/test_books_service.py` (mocked DAO).
7. **Dependency**: at the end of `src/api/deps.py`:

```python
   def get_book_service(cursor: CursorDep) -> BookService:
       """Build a BookService bound to the request cursor."""
       return BookService(BookDAO(cursor))


   BookServiceDep = Annotated[BookService, Depends(get_book_service)]
```

8. **Route**: `src/api/routes/books_routes.py`, then plug it into `src/api/main.py`
   (`api_router.include_router(books_routes.router)`).
9. **Protected route?** Just add the `current_user: CurrentUser` parameter.
10. **Integration tests**: `tests/integration/dao/test_books_dao.py`
    (the `cursor` fixture from the conftest is reusable).
11. Test in `/docs`, run `ruff` and `pytest`.

`auth_routes.py`, `users_service.py`, `users_dao.py` and their tests are a complete example.

### When you're done: commit, push and open a Pull Request

Commit regularly while you work, not only at the end:

```bash
git add -A
git status                           # check that .env is NOT in the list
git commit -m "feat(books): add GET /books/search endpoint"
```

The first time, push your branch to GitHub:

```bash
git push -u origin feature/books-search
```

After that, a simple `git push` is enough.

Then, on GitHub:

1. Click **Compare & pull request** (or go to *Pull requests* → *New pull request*).
2. Choose your branch → `main`.
3. In the description, explain what you did and write `Closes #<issue number>`
   so the issue closes automatically when the PR is merged.
4. Ask a teammate to review it before merging.

**If `main` changed while you were working**, bring those changes into your branch
before opening the PR:

```bash
git checkout main
git pull
git checkout feature/books-search
git merge main
```