# Ex-Libris — Web frontend

React interface for the Ex-Libris reading-tracker API (FastAPI, in `src/` at the
project root). Users can search books, keep a library, rate and review books,
organise shelves, follow other readers and track their reading progress.

Built with **React 19**, **React Router 7** and **Vite 7**. Styling uses plain
CSS Modules and a small set of design tokens: no UI framework and no extra
runtime dependencies.

---

## 1. Quick start — Python only, no Node.js

The `dist/` folder already contains the compiled app, and `serve.py` serves
it with the Python standard library. Nothing to install.

1. Start the backend, from the project root (first terminal):

   ```bash
   uv run src/main.py
   ```

2. Start the frontend, from this folder (second terminal):

   ```bash
   cd frontend
   ```
   ```bash
   uv run python app.py
   ```

3. Open the app:
   - on your computer: <http://localhost:5000>
   - on Onyxia/VSCode: your VSCode URL followed by `/proxy/5000/`
     (for example `https://user-xxxx.user.lab.sspcloud.fr/proxy/5000/`)

`serve.py` forwards every `/api` request to the backend. To change the
defaults, set environment variables, e.g.
`BACKEND_URL=http://127.0.0.1:8000 FRONTEND_PORT=5000 python app.py`.

> `dist/` is the compiled version of `src/`. If you **change the code** in
> `src/`, rebuild it with Node.js (section 2): `npm run build`. Otherwise you
> never need Node.js.

---

## 2. Development mode (Node.js) — only to change the code

Requirements:

- **Node.js 20.19 or newer** (22 LTS recommended): <https://nodejs.org>.
  On Onyxia, without admin rights:

  ```bash
  curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
  ```
  ```bash
  source ~/.bashrc && nvm install 22
  ```

- The backend running (`uv run src/main.py`).

### Install

From this `frontend/` folder:

```bash
npm install
```

### Configure (optional)

```bash
cp .env.example .env
```

| Variable | Default | Purpose |
|---|---|---|
| `VITE_BACKEND_URL` | `http://127.0.0.1:8000` | Where the FastAPI server runs. The dev server forwards every `/api` request there. |
| `VITE_API_URL` | *(empty)* | Only for a deployed build that calls a backend on another domain (needs CORS on the backend). Leave it empty. |
| `VITE_PORT` | `5173` | Port of the dev server. |
| `VITE_BASE_PATH` | `/` | Sub-path in development. On Onyxia, use `/absproxy/5173/` and open `<your VSCode URL>/absproxy/5173/`. |

### Run

```bash
npm run dev -- --host
```

Open <http://localhost:5173> (or `<VSCode URL>/absproxy/5173/` on Onyxia).
Changes in `src/` appear instantly.

| Command | What it does |
|---|---|
| `npm run build` | Rebuilds `dist/` (then `python serve.py` serves the new version) |
| `npm run preview` | Serves `dist/` with Node instead of Python |
| `npm run lint` | Checks the code with ESLint |

### Why a proxy?

The backend has no CORS middleware, so a browser page on `localhost:5173`
cannot call `localhost:8000` directly. Both `serve.py` and Vite's dev server
forward `/api/*` to the backend instead, so the browser only ever talks to one
origin.

---

## 3. Features

| Page | What you can do |
|---|---|
| **Sign in / Create account** | Validated forms; errors from the API (taken username, wrong password…) shown on the right field. |
| **Home** | Your current book with a one-click “Mark as finished”, library counts, next quests, personalised recommendations. |
| **Discover** | Search Open Library by title or author (“Show more results” loads up to 50). Without a search: recommendations by genre, sorted by rating, date or title. |
| **Catalog** | All books saved locally, filtered by genre and author (server-side), sorted and paginated. |
| **Book** | Cover, details, add to library with a status, change status, like, favorite, save to shelves, remove (with confirmation). Reviews: average rating, write / edit / delete your review. |
| **My library** | Tabs by status and favorites, genre filter, sorting, pagination, inline status change, like, favorite, remove (with confirmation). |
| **Shelves** | Create, rename, delete (with confirmation) shelves, see their covers, remove books. |
| **Readers** | Search users, follow / unfollow, see who you follow and who follows you. |
| **Reader profile** | Their library, reviews, shelves, followers, following, and stats (shown once you follow them, as the API requires). |
| **Progress** | Books finished, genre and rating breakdowns, quests with XP. |
| **Settings** | Edit username, email, bio and picture link; change password. |

Every action gives feedback (toast message, inline error or loading state),
lists have skeleton loaders, and empty and error states offer a next step.

---

## 4. Backend endpoints used

All paths are relative to `/api`. Every route except register and login needs
the `Authorization: Bearer <token>` header, which the client adds automatically.

| Method | Path | Used in |
|---|---|---|
| POST | `/auth/register` | Create account |
| POST | `/auth/login` (form data) | Sign in |
| POST | `/auth/logout` | Sign out |
| GET | `/users/me` | Session check, sidebar |
| PATCH | `/users/me` | Settings, profile |
| PUT | `/users/me/password` | Settings, password |
| GET | `/users/me/stats` | Progress, own profile |
| GET | `/users/me/quests?status=` | Home, Progress |
| GET | `/users/search?username=&limit=` | Readers |
| POST / DELETE | `/users/{id}/follow` | Follow buttons |
| GET | `/users/{id}/followers` | Readers, profile |
| GET | `/users/{id}/following` | Readers, profile |
| GET | `/users/{id}/library?status=` | Profile |
| GET | `/users/{id}/playlists` | Profile |
| GET | `/users/{id}/stats` | Profile (403 if not followed) |
| GET | `/users/{id}/reviews` | Profile |
| GET | `/books/search?q=&limit=` | Discover, sidebar search |
| GET | `/books?category=&author=` | Catalog |
| GET | `/books/{id}` | Book page |
| GET / POST | `/books/{id}/reviews` | Book page |
| PUT / DELETE | `/reviews/{id}` | Book page |
| GET | `/library/books?status=` | Library (loaded once, shared by all pages) |
| GET | `/library/favorites` | Library, favorites tab |
| POST | `/library/books` | Add to library |
| DELETE | `/library/books/{id}` | Remove from library |
| PATCH | `/library/books/{id}/status` | Change status |
| POST | `/library/books/{id}/like` | Like toggle |
| POST | `/library/books/{id}/favorite` | Favorite toggle |
| GET / POST | `/playlists` | Shelves |
| GET / PATCH / DELETE | `/playlists/{id}` | Shelf page |
| POST | `/playlists/{id}/books` | Save to shelf |
| DELETE | `/playlists/{id}/books/{bookId}` | Remove from shelf |
| GET | `/recommendations?genre=&sort=&limit=` | Home, Discover |

---

## 5. Project structure

```
frontend/
├── serve.py                Python server for dist/ (no Node.js needed)
├── dist/                   Compiled app, generated by `npm run build`
├── index.html              HTML entry, fonts
├── vite.config.js          Dev server + /api proxy
├── eslint.config.js
├── .env.example
├── public/favicon.svg
└── src/
    ├── main.jsx            Mounts the app with router and providers
    ├── App.jsx             Routes
    ├── config.js           Reads environment variables
    ├── api/                One file per backend area; all HTTP calls live here
    │   └── client.js       fetch wrapper: base URL, token, error parsing
    ├── context/            App-wide state: session, toasts, the user's library
    ├── hooks/              Reusable logic (async data, pagination, URL state…)
    ├── components/
    │   ├── ui/             Design-system pieces: Button, Field, Modal, Menu…
    │   ├── layout/         Sidebar layout, auth guard
    │   ├── books/          Covers, cards, grids, library and shelf controls
    │   ├── reviews/        Review form and review item
    │   ├── users/          Reader rows, follow button
    │   └── stats/          Bars, stats panels, quest cards
    ├── pages/              One component per screen (+ its CSS module)
    ├── styles/
    │   ├── tokens.css      Colours, type scale, spacing, radii, motion
    │   └── base.css        Global element styles
    └── utils/              Formatting, sorting, form validation
```

Conventions:

- Pages never call `fetch` directly: they use functions from `src/api/`.
- Each component has its own `*.module.css`; values come from `tokens.css`.
- Filters, sort orders and tabs are kept in the URL, so reloads and the back
  button keep them.

---

## 6. Known limitations (backend-side)

These come from the current API; the frontend does not invent endpoints for them.

- **No “get user by id” route.** Reviews and profiles only carry a user id, so a
  reader’s name is shown when the app has already seen it (search results,
  followers, following). Otherwise it reads “Reader #12”.
- **Other readers’ shelves** are listed by name only: `GET /playlists/{id}` is
  restricted to the owner.
- **Book search needs Open Library.** If the backend cannot reach
  openlibrary.org, search shows the backend’s “Open Library service is
  unavailable” error, and recommendations fall back to the best-rated local
  books.
- **Book descriptions** are not filled in by the Open Library search, so book
  pages link to the Open Library page instead.
- **Quest titles** are written in French by the backend and shown as-is.
- **No account deletion** endpoint exists, so the settings page doesn’t offer it.
- **Docker:** `docker-compose.yml` at the project root still builds the old
  Streamlit frontend; it was not changed.
