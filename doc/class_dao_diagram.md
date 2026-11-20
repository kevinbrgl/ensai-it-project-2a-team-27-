# DAO Class Diagrams - Ex-Libris

The data access layer (`src/dao/`) has one concrete class per data domain. There is no abstract `GenericDAO` interface: each DAO receives the request's `psycopg2` `RealDictCursor` in its constructor, runs plain SQL and converts rows into Pydantic models. Database errors are translated into business exceptions (`DAOError`, `BookAlreadyInLibraryError`, `ReviewAlreadyExistsError`, ...) so that services never see `psycopg2` errors.

---

## Diagram 1: DAO classes

```mermaid
classDiagram
    direction LR

    class RealDictCursor {
        <<psycopg2>>
        +execute(query, params)
        +fetchone() dict
        +fetchall() list~dict~
    }

    class UserDAO {
        -RealDictCursor cur
        +create(user_create: UserCreate) User
        +read(user_id: int) Optional~User~
        +read_by_username(username: str) Optional~User~
        +read_by_email(email: str) Optional~User~
        +search_by_username(username: str, limit: int) list~User~
        +add_follow(follower_id: int, following_id: int) None
        +remove_follow(follower_id: int, following_id: int) None
        +is_following(follower_id: int, following_id: int) bool
        +get_followers(user_id: int) list~User~
        +get_following(user_id: int) list~User~
        +update(user_id: int, user_in: UserUpdateFull) Optional~User~
        +update_settings(user_id: int, settings_in: UserSettingsUpdate) Optional~User~
        +set_suspended_until(user_id: int, until: datetime) Optional~User~
        +set_banned(user_id: int, banned: bool) Optional~User~
    }
    class FollowDAO {
        -RealDictCursor cur
        +add_follow(follower_id: int, following_id: int) None
        +remove_follow(follower_id: int, following_id: int) None
        +is_following(follower_id: int, following_id: int) bool
        +get_followers(user_id: int) list~User~
        +get_following(user_id: int) list~User~
    }
    class TokenDAO {
        -RealDictCursor cur
        +revoke(token_hash: str, expires_at: datetime) None
        +is_revoked(token_hash: str) bool
    }
    class BookDAO {
        -RealDictCursor cur
        +create(book_create: BookCreate) Book
        +upsert(book_create: BookCreate) Book
        +read(book_id: int) Optional~Book~
        +read_by_api_id(id_book_api: str) Optional~Book~
        +find_by_author(author: str) list~Book~
        +find_by_category(category: str) list~Book~
        +find_all() list~Book~
        +find_books(category: str, author: str) list~Book~
    }
    class LibraryDAO {
        -RealDictCursor cur
        +add_book(id_user: int, book_in: LibraryBookAdd) LibraryBookRead
        +read(id_user: int, id_book: int) Optional~LibraryBookRead~
        +remove_book(id_user: int, id_book: int) None
        +toggle_like(id_user: int, id_book: int) LibraryBookRead
        +toggle_favorite(id_user: int, id_book: int) LibraryBookRead
        +update_status(id_user: int, id_book: int, state: str) LibraryBookRead
        +update_dates(id_user: int, id_book: int, started_at: date, finished_at: date) LibraryBookRead
        +find_favorites_by_user_id(id_user: int) list~LibraryBookDetails~
        +find_books_by_user_id(id_user: int, status: str) list~LibraryBookDetails~
    }
    class ReviewDAO {
        -RealDictCursor cur
        +create(id_user: int, id_book: int, review_in: ReviewCreate) ReviewRead
        +find_by_id(id_review: int) ReviewRead
        +find_by_book_id(id_book: int) list~ReviewRead~
        +find_by_user_id(id_user: int) list~ReviewRead~
        +get_rating_stats(id_book: int) tuple
        +update(id_review: int, review_in: ReviewUpdate) ReviewRead
        +delete(id_review: int) None
    }
    class PlaylistDAO {
        -RealDictCursor cur
        +create(id_user: int, playlist_in: PlaylistCreate) PlaylistRead
        +find_by_user_id(id_user: int) list~PlaylistRead~
        +rename(id_user: int, id_playlist: int, playlist_in: PlaylistUpdate) PlaylistRead
        +delete(id_user: int, id_playlist: int) None
        +read(id_user: int, id_playlist: int) Optional~PlaylistRead~
        +add_book(id_playlist: int, id_book: int) PlaylistBookRead
        +find_books(id_playlist: int) list~Book~
        +remove_book(id_playlist: int, id_book: int) None
    }
    class RecommendationDAO {
        -RealDictCursor cur
        +count_rated_genres(id_user: int, min_rating: int) list~GenreCount~
        +find_library_api_keys(id_user: int) set~str~
        +get_average_ratings(book_ids: list~int~) dict
        +find_top_rated_books(id_user: int, limit: int, category: str) list~tuple~
    }
    class StatsDAO {
        -RealDictCursor cur
        +count_finished_books(id_user: int) int
        +sum_pages_read(id_user: int) int
        +count_genres(id_user: int) list~GenreCount~
        +count_ratings(id_user: int) dict
    }
    class QuestDAO {
        -RealDictCursor cur
        +get_user_stats(user_id: int) QuestUserStats
    }
    class AchievementDAO {
        -RealDictCursor cur
        +get_user_stats(user_id: int) AchievementUserStats
    }
    class GenreWheelDAO {
        -RealDictCursor cur
        +get_user_completed_books(user_id: int) list~dict~
    }

    UserDAO --> RealDictCursor
    UserDAO --> FollowDAO
    FollowDAO --> RealDictCursor
    TokenDAO --> RealDictCursor
    BookDAO --> RealDictCursor
    LibraryDAO --> RealDictCursor
    ReviewDAO --> RealDictCursor
    PlaylistDAO --> RealDictCursor
    RecommendationDAO --> RealDictCursor
    StatsDAO --> RealDictCursor
    QuestDAO --> RealDictCursor
    AchievementDAO --> RealDictCursor
    GenreWheelDAO --> RealDictCursor
```

### Tables used by each DAO

| DAO | Tables |
|---|---|
| `UserDAO` | `users` |
| `FollowDAO` | `user_follows`, `users` |
| `TokenDAO` | `revoked_tokens` |
| `BookDAO` | `books` |
| `LibraryDAO` | `user_book_activities`, `books` |
| `ReviewDAO` | `reviews` |
| `PlaylistDAO` | `playlists`, `playlist_books`, `books` |
| `RecommendationDAO` | `reviews`, `books`, `user_book_activities` |
| `StatsDAO` | `user_book_activities`, `books`, `reviews` |
| `GenreWheelDAO` | `user_book_activities`, `books`, `reviews` |
| `QuestDAO`, `AchievementDAO` | all tables except `revoked_tokens` (one aggregated query of counters) |

---

## Diagram 2: Services and the DAOs they use

```mermaid
classDiagram
    direction LR

    class UserService
    class TokenService
    class AdminService
    class BookService
    class LibraryService
    class ReviewService
    class PlaylistService
    class RecommendationService
    class StatsService
    class QuestService
    class AchievementService
    class GenreWheelService

    class UserDAO
    class TokenDAO
    class BookDAO
    class LibraryDAO
    class ReviewDAO
    class PlaylistDAO
    class RecommendationDAO
    class StatsDAO
    class QuestDAO
    class AchievementDAO
    class GenreWheelDAO

    UserService --> UserDAO
    TokenService --> TokenDAO
    AdminService --> UserDAO
    AdminService --> ReviewDAO
    BookService --> BookDAO
    LibraryService --> LibraryDAO
    ReviewService --> ReviewDAO
    ReviewService --> BookDAO
    ReviewService --> UserDAO
    ReviewService --> LibraryDAO
    PlaylistService --> PlaylistDAO
    RecommendationService --> RecommendationDAO
    RecommendationService --> StatsDAO
    RecommendationService --> BookService
    StatsService --> StatsDAO
    QuestService --> QuestDAO
    AchievementService --> AchievementDAO
    GenreWheelService --> GenreWheelDAO
```

Notes:

- The wiring is done in `src/api/deps.py` (`get_user_service`, `get_review_service`, `get_recommendation_service`, ...). All the DAOs of one request share the same cursor, so the request is a single transaction: `get_cursor` commits at the end of the request and rolls back on any exception.
- Unit tests replace the DAOs with mocks (`tests/mocks.py`), and integration tests in `tests/integration/dao/` run each DAO against a real PostgreSQL database.
