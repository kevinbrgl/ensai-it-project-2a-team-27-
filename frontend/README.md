# Ex-Libris web frontend

This is the React interface for the Ex-Libris reading-tracker API in [../src/](../src/). Readers use it to search books, keep a library, rate and review books, organize playlists, follow other readers and track their progress. It is built with React 19, React Router 7 and Vite 7, and styled with CSS Modules and design tokens, without a UI framework. The compiled app in `dist/` is committed, and [app.py](app.py) serves it, so running the app requires only Python. Node.js is needed only to change the code.

## Features

| Page | Route | What you can do |
|---|---|---|
| **Sign in / Create account** | `/login`, `/register` | Fill in validated forms. API errors such as a taken username appear next to the relevant field. |
| **Home** | `/` | See your current book with a one-click “Mark as finished”, library counts, your next quests and recommendations. |
| **Discover** | `/discover` | Search Open Library by title or author. “Show more results” loads up to 50. Without a search, browse recommendations by genre, sorted by rating, date or title. |
| **Book** | `/books/:bookId` | Browse editions and other titles by the author. Add the book to your library or a playlist, change its status, and publish or edit a review. |
| **My library** | `/library` | Use status and favorites tabs, a genre filter, sorting and pagination. Change a status inline, like, favorite, or remove a book with confirmation. |
| **Playlists** | `/playlists`, `/playlists/:playlistId` | Create, rename and delete playlists, view their covers and remove books. |
| **Readers** | `/readers` | Search readers by username, see their genre wheels, follow them and see who follows you. |
| **Reader profile** | `/users/:userId` | View a public reader's library, playlists and genre wheel. Reviews and follow lists stay visible on private profiles. Statistics are visible only to the reader's followers. Admins can suspend or ban the reader. |
| **Progress** | `/progress` | View reading totals and a genre wheel, achievements by tier, and active quests with XP. |
| **Settings** | `/settings` | Edit your username, email, bio and picture link. Change your password, choose a day or night theme, and set your profile to public or private. |

Every action shows feedback as a toast, an inline error or a loading state. Lists show skeleton loaders while they load, and empty and error states suggest what to do next. Filters, sort orders and tabs are stored in the URL, so they survive a reload and work with the back button. Every page except sign-in and registration requires authentication.

## Prerequisites and installation

**To run the bundled app**, follow the [main installation guide](../README.md#installation) and start the backend. `app.py` uses the Python standard library.

**To change the code:** you also need **Node.js 20.19 or later**, as set in `package.json` `engines`. On Onyxia, without admin rights, you can install it with nvm:

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
source ~/.bashrc && nvm install 22
```

Then install the dependencies from this `frontend/` folder:

```bash
npm install
```

## Configuration

### `app.py`: serves the bundled app

`app.py` reads these variables from the process environment. It does not read `.env`.

| Variable | Default | Purpose |
|---|---|---|
| `BACKEND_URL` | `http://127.0.0.1:8000` | Where `/api` requests are forwarded. It must start with `http://` or `https://`. |
| `FRONTEND_PORT` | `5000` | Listening port. The server binds to all interfaces so the Onyxia proxy can reach it. |

### Vite: development server and build

Copy the example file, then edit it if needed:

```bash
cp .env.example .env
```

| Variable | Default | Purpose |
|---|---|---|
| `VITE_BACKEND_URL` | `http://127.0.0.1:8000` | FastAPI address. The dev and preview servers forward `/api` requests to it. |
| `VITE_API_URL` | *(empty)* | Full API URL for a build served elsewhere. The backend has no CORS middleware, so leave this empty. |
| `VITE_PORT` | `5000` for dev, `4173` for preview | Server port. Stop `app.py` first if it uses the same port. |
| `VITE_BASE_PATH` | `/` | Base path in development. On Onyxia, use `/absproxy/5000/`. It must start and end with `/`. |

Production builds use relative asset paths. At runtime, a script in [index.html](index.html) detects a `/proxy/<port>/` or `/absproxy/<port>/` prefix, so the same `dist/` works at the site root and behind Onyxia.

## Usage

Start the backend first, in its own terminal at the repository root:

```bash
uv run src/main.py
```

### Run the bundled app (Python only)

From the repository root, run:

```bash
uv run python frontend/app.py
```

Open **http://localhost:5000**. On Onyxia, open your VS Code URL followed by `/proxy/5000/`. To change the defaults, set the variables when you start the server:

```bash
BACKEND_URL=http://127.0.0.1:8000 FRONTEND_PORT=5001 uv run python frontend/app.py
```

Paths that don't match a file in `dist/`, such as `/books/12`, return `index.html` so that client-side routing works. If the backend is down, `/api` calls return `502` with the message “Cannot reach the backend. Is it running?”.

### Development mode (Node.js)

From `frontend/`, run:

```bash
npm run dev -- --host
```

Open **http://localhost:5000**. On Onyxia, open your VS Code URL followed by `/absproxy/5000/` and set `VITE_BASE_PATH=/absproxy/5000/`. Changes in `src/` reload instantly.

| Command | What it does |
|---|---|
| `npm run dev` | Starts the Vite dev server with an `/api` proxy |
| `npm run build` | Rebuilds `dist/`, which `app.py` then serves |
| `npm run preview` | Serves `dist/` with Vite instead of Python |
| `npm run lint` | Runs ESLint |

---

### 📦 Optional: load the sample data

> [!NOTE]
> **This step is optional.** The frontend stores no data of its own. Demo content is loaded into the backend database.

From the **repository root**, run:

```bash
uv run python -m src.seed_demo
```

Then sign in as **`demo_alex`** or **`demo_jo`** with the password **`ExLibrisDemo27`**. Alex has the richest account: open **My library**, **Progress** or the **Book club picks** playlist. Jo is an administrator, so Jo sees the moderation menu on Alex's profile and reviews. The [backend guide](../src/README.md#-optional-load-the-sample-data) lists everything the demo loads.

---

### Why the proxy?

The backend has no CORS middleware, so a page on `localhost:5000` cannot call `localhost:8000` directly. `app.py`, the Vite dev server and the preview server all forward `/api/*` to the backend, so the browser talks to a single origin.

### Known limitations

These limitations come from the current API. The frontend does not add endpoints to work around them.

- **Review authors** are identified only by ID. A reviewer's name appears only if the app has already loaded that reader, for example from search results, follower lists or a visited profile. Otherwise it shows “Reader #12”.
- **Other readers' playlists** are listed by name only, because `GET /playlists/{id}` is restricted to the owner.
- **Book search** needs the backend to reach openlibrary.org. When it can't, recommendations fall back to the best-rated local books.
- **Book descriptions** are not included in search results, so book pages link to Open Library instead.
- **Account deletion** is not available, because the API has no endpoint for it.

## Project structure

```text
frontend/
├── app.py               # Python server for dist/ with an /api proxy (no Node.js needed)
├── dist/                # Compiled app, generated by `npm run build` and committed
├── index.html           # HTML entry and base-path detection
├── vite.config.js       # Dev and preview servers, /api proxy, relative build paths
├── eslint.config.js
├── .env.example
├── public/              # favicon.svg and font licenses
└── src/
    ├── main.jsx         # Mounts the app with the router and providers
    ├── App.jsx          # Route table
    ├── config.js        # API base URL, app base path, token storage key
    ├── api/             # One module per backend area. client.js wraps fetch, the token and errors.
    ├── context/         # Session, toasts and the user's library
    ├── hooks/           # Async data, pagination, debounce, URL state, follows, document title
    ├── components/
    │   ├── ui/          # Button, Field, Modal, Menu, Pagination, StarRating…
    │   ├── layout/      # Layout, navigation, auth guard, wordmark
    │   ├── books/       # Covers, cards, grids, library and playlist controls
    │   ├── reviews/     # Review form and review item
    │   ├── users/       # Reader rows and follow button
    │   ├── stats/       # Genre wheel, achievements, quests, progress panels
    │   └── admin/       # Moderation menu
    ├── pages/           # One component and CSS module per screen
    ├── styles/          # tokens.css (colors, type, spacing, motion) and base.css
    └── utils/           # Formatting, book helpers, genre wheel, validation
```

Conventions:

- Pages never call `fetch` directly. They use the functions in `src/api/`.
- Each component has its own `*.module.css` file, and style values come from `tokens.css`.
- The access token is stored in `localStorage` under `exlibris.token`.

<details>
<summary>Backend endpoints used by the frontend</summary>

Paths are relative to `/api`. Every route except register and login sends `Authorization: Bearer <token>`.

| Method | Path | Used in |
|---|---|---|
| POST | `/auth/register`, `/auth/login` (form data), `/auth/logout` | Sign-in pages, account menu |
| GET / PATCH | `/users/me`, `/users/me/settings` | Settings, session check, theme |
| PUT | `/users/me/password` | Settings |
| GET | `/users/me/stats`, `/users/me/quests`, `/users/me/achievements` | Home, Progress |
| GET | `/users/search`, `/users/{id}`, `/users/{id}/genre-wheel` | Readers, profiles, account menu |
| POST / DELETE | `/users/{id}/follow` | Follow buttons |
| GET | `/users/{id}/followers`, `/users/{id}/following` | Readers, profiles |
| GET | `/users/{id}/library`, `/users/{id}/playlists`, `/users/{id}/stats`, `/users/{id}/reviews` | Profiles |
| GET | `/books/search`, `/books`, `/books/{id}` | Discover, book page |
| GET / POST | `/books/{id}/reviews` | Book page |
| PUT / DELETE | `/reviews/{id}` | Book page |
| GET / POST | `/library/books` | Library, add to library |
| GET | `/library/favorites` | Library |
| DELETE | `/library/books/{id}` | Remove from library |
| PATCH | `/library/books/{id}/status`, `/library/books/{id}/dates` | Status and reading dates |
| POST | `/library/books/{id}/like`, `/library/books/{id}/favorite` | Like and favorite toggles |
| GET / POST | `/playlists` | Playlists |
| GET / PATCH / DELETE | `/playlists/{id}` | Playlist page |
| POST / DELETE | `/playlists/{id}/books`, `/playlists/{id}/books/{bookId}` | Add to or remove from a playlist |
| GET | `/recommendations` | Home, Discover |
| POST | `/admin/users/{id}/suspend`, `/admin/users/{id}/ban` | Moderation menu (admins) |
| DELETE | `/admin/reviews/{id}` | Book page (admins) |

</details>

## Contributing and license

Before committing frontend changes:

```bash
npm run lint     # ESLint with the recommended, react-hooks and react-refresh rules
npm run build    # Regenerate dist/
```

Commit the regenerated `dist/` with the source changes so that `app.py` serves the new version. If you edit `app.py`, also run `uv run ruff check` and `uv run mypy src tests frontend/app.py` from the repository root. Run the frontend checks locally because CI checks the Python backend.

**License:** GNU General Public License v3.0. See [../LICENSE](../LICENSE). The Instrument Serif and Work Sans fonts are licensed under the SIL Open Font License, and their license texts are in [public/licenses/](public/licenses/).
