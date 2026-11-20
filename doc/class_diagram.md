# Class Diagrams - Ex-Libris

Three diagrams, each matching a package of `src/`:

1. **Business models**: the Pydantic models of `src/models/` that map to database rows.
2. **Statistics and gamification models**: computed objects that are never stored (stats, quests, achievements, genre wheel, recommendations).
3. **Services**: the business layer of `src/services/`.

The DAO layer is in [class_dao_diagram.md](class_dao_diagram.md).

Input-only models (`UserRegister`, `UserUpdate`, `UserSettingsUpdate`, `UserUpdatePassword`, `LibraryBookAdd`, `LibraryBookUpdateStatus`, `LibraryBookUpdateDates`, `ReviewCreate`, `ReviewUpdate`, `PlaylistCreate`, `PlaylistUpdate`, `PlaylistBookAdd`, `SuspendRequest`, `BookCreate`) are left out to keep the diagrams readable. Each one carries a subset of the attributes of the model it creates or updates.

---

## Diagram 1: Business models

```mermaid
classDiagram
    direction LR

    class ReadingState {
        <<enumeration>>
        WANT_TO_READ
        READING
        COMPLETED
        ABANDONED
    }
    class Theme {
        <<enumeration>>
        day
        night
    }
    class ProfileVisibility {
        <<enumeration>>
        public
        private
    }

    class User {
        +int id_user
        +str username
        +EmailStr email
        +str password_hash
        +str bio
        +str profile_picture
        +Theme theme
        +ProfileVisibility profile_visibility
        +bool is_admin
        +bool is_banned
        +datetime suspended_until
    }
    class UserPublic {
        +int id_user
        +str username
        +str bio
        +str profile_picture
        +ProfileVisibility profile_visibility
    }
    class UserFollow {
        +int follower_id
        +int following_id
    }
    class Token {
        +str access_token
        +str token_type
    }
    class ModerationStatus {
        +int id_user
        +str username
        +bool is_banned
        +datetime suspended_until
    }

    class Book {
        +int id_book
        +str id_book_api
        +str title
        +str author
        +str category
        +date publish_date
        +str description
        +str cover_image
        +int num_pages
    }
    class BookDetails {
        +list~Edition~ editions
    }
    class Edition {
        +str title
        +list~str~ publishers
        +str publish_date
        +int num_pages
        +str isbn
        +str language
    }

    class LibraryBookRead {
        +int id_user
        +int id_book
        +ReadingState state
        +bool is_liked
        +bool is_favorite
        +date started_at
        +date finished_at
    }
    class LibraryBookDetails {
        +str title
        +str author
        +str category
        +date publish_date
        +str description
        +str cover_image
    }

    class ReviewRead {
        +int id_review
        +int id_user
        +int id_book
        +int rating
        +str comment
        +datetime created_at
    }
    class BookReviews {
        +int id_book
        +float average_rating
        +int review_count
        +list~ReviewRead~ reviews
    }

    class PlaylistRead {
        +int id_playlist
        +int id_user
        +str name
    }
    class PlaylistDetails {
        +list~Book~ books
    }

    %% Inheritance
    Book <|-- BookDetails
    LibraryBookRead <|-- LibraryBookDetails
    PlaylistRead <|-- PlaylistDetails

    %% Composition / aggregation
    BookDetails "1" *-- "0..*" Edition : editions
    BookReviews "1" o-- "0..*" ReviewRead : reviews
    PlaylistDetails "0..*" o-- "0..*" Book : books

    %% Associations (foreign keys)
    User "1" --> "0..*" LibraryBookRead : library
    Book "1" --> "0..*" LibraryBookRead
    User "1" --> "0..*" ReviewRead : writes
    Book "1" --> "0..*" ReviewRead
    User "1" --> "0..*" PlaylistRead : owns
    User "1" --> "0..*" UserFollow : follower
    User "1" --> "0..*" UserFollow : following

    %% Enumerations
    LibraryBookRead ..> ReadingState
    User ..> Theme
    User ..> ProfileVisibility
    User ..> UserPublic : shown to other users as
    User ..> ModerationStatus : summarised by
```

Notes:

- `User` is the full database row. It is never returned as is: the API returns `UserRead` for one's own profile, `UserMe` for one's settings and `UserPublic` for other users' profiles (no email, no settings).
- `ReadingState`, `Theme` and `ProfileVisibility` are shown as enumerations. In the code, `state` is a string validated by a regex and `Theme` / `ProfileVisibility` are `Literal` types.
- `BookDetails.editions` is fetched live from Open Library and never stored.

---

## Diagram 2: Statistics and gamification models

```mermaid
classDiagram
    direction LR

    class UserStats {
        +int books_finished
        +int pages_read
        +list~GenreCount~ genres
        +list~RatingCount~ ratings
    }
    class GenreCount {
        +str category
        +int count
    }
    class RatingCount {
        +int rating
        +int count
    }

    class Recommendation {
        +Book book
        +float score
        +str reason
    }

    class QuestCategory {
        <<enumeration>>
        READING
        EXPLORATION
        SOCIAL
        ENGAGEMENT
    }
    class QuestDefinition {
        <<dataclass>>
        +str id_quest
        +str title
        +str description
        +QuestCategory category
        +int target
        +int reward_xp
        +str stat_key
        +evaluate(current: int) Quest
    }
    class Quest {
        +str id_quest
        +str title
        +str description
        +QuestCategory category
        +int current
        +int target
        +float progress_percentage
        +bool is_completed
        +int reward_xp
    }
    class QuestUserStats {
        +int completed_books
        +int reading_books
        +int distinct_categories
        +int following_count
        +int favorite_books
        +int pages_read
        +int reviews_count
        +int playlists_count
        +int ... 9 other counters
    }

    class AchievementCategory {
        <<enumeration>>
        READING
        EXPLORATION
        COMMUNITY
        SOCIAL
        COLLECTION
    }
    class AchievementTier {
        <<enumeration>>
        BRONZE
        SILVER
        GOLD
        PLATINUM
    }
    class AchievementDefinition {
        <<dataclass>>
        +str id_achievement
        +str title
        +str description
        +AchievementCategory category
        +AchievementTier tier
        +str icon
        +int target
        +str stat_key
        +evaluate(current_stat: int) Achievement
    }
    class Achievement {
        +str id_achievement
        +str title
        +str description
        +AchievementCategory category
        +AchievementTier tier
        +str icon
        +bool is_unlocked
        +int progress
        +int target
        +float progress_percentage
    }
    class AchievementUserStats {
        +int completed_books
        +int pages_read
        +int distinct_genres
        +int reviews_count
        +int favorites_count
        +int following_count
        +int followers_count
        +int playlists_count
        +int ... 14 other counters
    }

    class GenreWheel {
        +int id_user
        +bool is_empty
        +str empty_color
        +int total_books
        +list~GenreWheelSegment~ segments
    }
    class GenreWheelSegment {
        +str genre
        +str color
        +float percentage
        +int book_count
        +float average_rating
        +float raw_score
    }

    UserStats "1" *-- "0..*" GenreCount
    UserStats "1" *-- "0..*" RatingCount
    GenreWheel "1" *-- "0..7" GenreWheelSegment

    QuestDefinition ..> Quest : evaluate()
    QuestDefinition ..> QuestUserStats : reads stat_key
    QuestDefinition --> QuestCategory
    Quest --> QuestCategory

    AchievementDefinition ..> Achievement : evaluate()
    AchievementDefinition ..> AchievementUserStats : reads stat_key
    AchievementDefinition --> AchievementCategory
    AchievementDefinition --> AchievementTier
    Achievement --> AchievementCategory
    Achievement --> AchievementTier
```

Notes:

- 32 quests and 55 achievements are declared as constants (`QUESTS`, `ACHIEVEMENTS`) in their services. Each definition names the counter it tracks (`stat_key`); the service fetches all counters in one query and calls `evaluate()` on every definition.
- The genre wheel keeps at most 7 segments. Genres under 3 % of the total weight are dropped and the remaining shares are rescaled to 100 %.

---

## Diagram 3: Services

```mermaid
classDiagram
    direction LR

    class UserService {
        -UserDAO dao
        +authenticate(username: str, password: str) User
        +login(username: str, password: str) Token
        +register(user_in: UserRegister) User
        +read(user_id: int) User
        +read_by_username(username: str) User
        +search_users(username: str, limit: int) list~User~
        +follow_user(follower_id: int, following_id: int) None
        +unfollow_user(follower_id: int, following_id: int) None
        +get_followers(user_id: int) list~User~
        +get_following(user_id: int) list~User~
        +update(user_id: int, user_in: UserUpdate) User
        +update_password(current_user: User, body: UserUpdatePassword) User
        +update_settings(user_id: int, settings_in: UserSettingsUpdate) User
        +ensure_active(user: User) None$
        +ensure_profile_visible(user: User, viewer_id: int) None$
    }
    class TokenService {
        -TokenDAO dao
        +revoke(token: str) None
        +is_revoked(token: str) bool
    }
    class AdminService {
        -UserDAO user_dao
        -ReviewDAO review_dao
        -_check_target(admin_id: int, user_id: int) None
        +suspend_user(admin_id: int, user_id: int, days: int) ModerationStatus
        +ban_user(admin_id: int, user_id: int) ModerationStatus
        +delete_review(review_id: int) None
    }

    class OpenLibraryClient {
        -float timeout
        -_get_json(url: str, params: dict) dict
        +search(query, limit, subject, sort) dict
        +fetch_editions(work_key: str, limit: int) dict
    }
    class BookService {
        -BookDAO dao
        -OpenLibraryClient open_library
        -_doc_to_book_create(doc: dict) BookCreate$
        -_entry_to_edition(entry: dict) Edition$
        +search_books(query: str, limit: int) list~Book~
        +search_by_subject(subject: str, limit: int, sort: str) list~tuple~
        +save_book(book_create: BookCreate) Book
        +get_book(book_id: int) Book
        +get_editions(book: Book) list~Edition~
        +get_book_details(book_id: int) BookDetails
        +get_books(category: str, author: str) list~Book~
        +get_catalogue(category: str, author: str) list~Book~
    }
    class LibraryService {
        -LibraryDAO dao
        +add_book_to_library(id_user: int, book_in: LibraryBookAdd) LibraryBookRead
        +remove_book_from_library(id_user: int, id_book: int) None
        +toggle_like(id_user: int, id_book: int) LibraryBookRead
        +toggle_favorite(id_user: int, id_book: int) LibraryBookRead
        +update_book_status(id_user: int, id_book: int, state: str) LibraryBookRead
        +update_book_dates(id_user: int, id_book: int, dates_in: LibraryBookUpdateDates) LibraryBookRead
        +list_books(id_user: int, status: str) list~LibraryBookDetails~
        +list_favorites(id_user: int) list~LibraryBookDetails~
    }
    class ReviewService {
        -ReviewDAO review_dao
        -BookDAO book_dao
        -UserDAO user_dao
        -LibraryDAO library_dao
        +get_book_reviews(id_book: int) BookReviews
        +create_review(id_user: int, id_book: int, review_in: ReviewCreate) ReviewRead
        -_check_author(id_user: int, id_review: int) None
        +update_review(id_user: int, id_review: int, review_in: ReviewUpdate) ReviewRead
        +delete_review(id_user: int, id_review: int) None
        +list_user_reviews(id_user: int) list~ReviewRead~
    }
    class PlaylistService {
        -PlaylistDAO dao
        +create_playlist(id_user: int, playlist_in: PlaylistCreate) PlaylistRead
        +list_playlists(id_user: int) list~PlaylistRead~
        +rename_playlist(id_user: int, id_playlist: int, playlist_in: PlaylistUpdate) PlaylistRead
        +delete_playlist(id_user: int, id_playlist: int) None
        -_get_own_playlist(id_user: int, id_playlist: int) PlaylistRead
        +add_book_to_playlist(id_user: int, id_playlist: int, book_in: PlaylistBookAdd) PlaylistBookRead
        +get_playlist(id_user: int, id_playlist: int) PlaylistDetails
        +remove_book_from_playlist(id_user: int, id_playlist: int, id_book: int) None
    }

    class RecommendationService {
        -RecommendationDAO recommendation_dao
        -StatsDAO stats_dao
        -BookService book_service
        +get_recommendations(id_user: int, genre: str, sort: RecommendationSort, limit: int) list~Recommendation~
        -_favorite_genres(id_user: int) list~str~
        -_from_open_library(id_user, genres, reason_template, sort, limit) list~Recommendation~
        -_fallback(id_user, genre, sort, limit) list~Recommendation~
        -_sort(recommendations, sort) list~Recommendation~$
    }
    class StatsService {
        -StatsDAO dao
        +get_stats(id_user: int) UserStats
    }
    class QuestService {
        -QuestDAO dao
        +get_quests(user_id: int, status_filter: str) list~Quest~
    }
    class AchievementService {
        -AchievementDAO dao
        +get_achievements(user_id: int, status_filter: str) list~Achievement~
    }
    class GenreWheelService {
        -GenreWheelDAO dao
        +resolve_color(genre: str) str$
        -_compute_book_weight(rating: int, is_favorite: bool) float$
        -_aggregate_books(books: list) tuple
        -_build_segments(scores, counts, ratings) list~GenreWheelSegment~
        +get_genre_wheel(user_id: int) GenreWheel
    }

    RecommendationService --> BookService : searches Open Library and saves books

    UserService ..> User
    UserService ..> Token
    AdminService ..> ModerationStatus
    BookService --> OpenLibraryClient
    BookService ..> Book
    BookService ..> Edition
    LibraryService ..> LibraryBookRead
    ReviewService ..> ReviewRead
    PlaylistService ..> PlaylistRead
    RecommendationService ..> Recommendation
    StatsService ..> UserStats
    QuestService ..> Quest
    AchievementService ..> Achievement
    GenreWheelService ..> GenreWheel
```

Notes:

- Each service is built per request by a FastAPI dependency in `src/api/deps.py`, with DAOs that share the request's database cursor (one transaction per request).
- `BookService` uses `OpenLibraryClient` to call Open Library (`/search.json` for searches and recommendations, `/works/{key}/editions.json` for editions).
- Static methods are marked with `$`. Private helpers start with `-`.
