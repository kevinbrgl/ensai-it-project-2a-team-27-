# Ex-Libris — Web frontend

React interface for the Ex-Libris reading-tracker API (FastAPI, in `src/` at the
project root). Users can search books, keep a library, rate and review books,
organise shelves, follow other readers and track their reading progress.

Built with **React 19**, **React Router 7** and **Vite 7**. Styling uses plain
CSS Modules and a small set of design tokens: no UI framework and no extra
runtime dependencies.

---

## 1. Quick start — Python only, no Node.js

The `dist/` folder already contains the compiled app, and `app.py` serves
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

`app.py` forwards every `/api` request to the backend. To change the
defaults, set environment variables, e.g.
`BACKEND_URL=http://127.0.0.1:8000 FRONTEND_PORT=5001 uv run python app.py`.

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
| `VITE_PORT` | `5000` | Port of the dev server (stop `app.py` first, it uses the same port). |
| `VITE_BASE_PATH` | `/` | Sub-path in development. On Onyxia, use `/absproxy/5000/` and open `<your VSCode URL>/absproxy/5000/`. |

### Run

```bash
npm run dev -- --host
```

Open <http://localhost:5000> (or `<VSCode URL>/absproxy/5000/` on Onyxia).
Changes in `src/` appear instantly.

| Command | What it does |
|---|---|
| `npm run build` | Rebuilds `dist/` (then `uv run python app.py` serves the new version) |
| `npm run preview` | Serves `dist/` with Node instead of Python |
| `npm run lint` | Checks the code with ESLint |

### Why a proxy?

The backend has no CORS middleware, so a browser page on `localhost:5000`
cannot call `localhost:8000` directly. Both `app.py` and Vite's dev server
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
| **Reader profile** | Their name, bio and picture, library, reviews, shelves, followers, following, and stats (shown once you follow them, as the API requires). A private profile only shows its reviews and followers to others. Admins can suspend or ban the reader. |
| **Progress** | Books finished, genre and rating breakdowns, quests with XP. |
| **Settings** | Edit username, email, bio and picture link; change password; day or night theme; public or private profile. |

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
| GET | `/users/me/settings` | Session check, sidebar, theme |
| PATCH | `/users/me/settings` | Settings, theme and profile visibility |
| PATCH | `/users/me` | Settings, profile |
| PUT | `/users/me/password` | Settings, password |
| GET | `/users/me/stats` | Progress, own profile |
| GET | `/users/me/quests?status=` | Home, Progress |
| GET | `/users/search?username=&limit=` | Readers |
| GET | `/users/{id}` | Profile (name, bio, picture, visibility) |
| POST / DELETE | `/users/{id}/follow` | Follow buttons |
| GET | `/users/{id}/followers` | Readers, profile |
| GET | `/users/{id}/following` | Readers, profile |
| GET | `/users/{id}/library?status=` | Profile (403 if private) |
| GET | `/users/{id}/playlists` | Profile (403 if private) |
| GET | `/users/{id}/stats` | Profile (403 if not followed or private) |
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
| PATCH | `/library/books/{id}/dates` | Reading dates |
| POST | `/library/books/{id}/like` | Like toggle |
| POST | `/library/books/{id}/favorite` | Favorite toggle |
| GET / POST | `/playlists` | Shelves |
| GET / PATCH / DELETE | `/playlists/{id}` | Shelf page |
| POST | `/playlists/{id}/books` | Save to shelf |
| DELETE | `/playlists/{id}/books/{bookId}` | Remove from shelf |
| GET | `/recommendations?genre=&sort=&limit=` | Home, Discover |
| POST | `/admin/users/{id}/suspend`, `/admin/users/{id}/ban` | Profile, moderation menu (admins) |
| DELETE | `/admin/reviews/{id}` | Book page, moderation (admins) |

---

## 5. Project structure

```
frontend/
├── app.py                  Python server for dist/ (no Node.js needed)
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

- **Review authors** are only given by their id, so a reviewer’s name is shown
  when the app has already seen that reader (search results, followers, a
  visited profile). Otherwise it reads “Reader #12”.
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
