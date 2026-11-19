# Database Diagram - Ex-Libris

Source of truth: [`data/init.sql`](../data/init.sql). PostgreSQL schema, 8 tables.

```mermaid
erDiagram
    USERS ||--o{ USER_BOOK_ACTIVITIES : "has in library"
    BOOKS ||--o{ USER_BOOK_ACTIVITIES : "tracked in"
    USERS ||--o{ REVIEWS : "writes"
    BOOKS ||--o{ REVIEWS : "receives"
    USERS ||--o{ PLAYLISTS : "creates"
    PLAYLISTS ||--o{ PLAYLIST_BOOKS : "contains"
    BOOKS ||--o{ PLAYLIST_BOOKS : "listed in"
    USERS ||--o{ USER_FOLLOWS : "follower"
    USERS ||--o{ USER_FOLLOWS : "following"

    USERS {
        serial id_user PK
        varchar(30) username UK "NOT NULL"
        varchar(100) email UK "NOT NULL"
        varchar(255) password_hash "NOT NULL, bcrypt"
        text bio
        varchar(255) profile_picture
        varchar(5) theme "day | night, default day"
        varchar(7) profile_visibility "public | private, default public"
        boolean is_admin "default FALSE"
        boolean is_banned "default FALSE"
        timestamptz suspended_until "NULL = not suspended"
    }
    BOOKS {
        serial id_book PK
        varchar(100) id_book_api UK "Open Library work key, e.g. /works/OL45804W"
        varchar(255) title "NOT NULL"
        varchar(255) author
        varchar(100) category
        date publish_date
        text description
        varchar(255) cover_image
        int num_pages
    }
    USER_BOOK_ACTIVITIES {
        int id_user PK, FK "ON DELETE CASCADE"
        int id_book PK, FK "ON DELETE CASCADE"
        varchar(50) state "WANT_TO_READ | READING | COMPLETED | ABANDONED"
        boolean is_liked "default FALSE"
        boolean is_favorite "default FALSE"
        date started_at
        date finished_at
    }
    REVIEWS {
        serial id_review PK
        int id_user FK "UNIQUE (id_user, id_book)"
        int id_book FK "UNIQUE (id_user, id_book)"
        int rating "CHECK 1-5"
        text comment
        timestamptz created_at "default NOW()"
    }
    PLAYLISTS {
        serial id_playlist PK
        int id_user FK "UNIQUE (id_user, name)"
        varchar(100) name "NOT NULL"
    }
    PLAYLIST_BOOKS {
        int id_playlist PK, FK "ON DELETE CASCADE"
        int id_book PK, FK "ON DELETE CASCADE"
    }
    USER_FOLLOWS {
        int follower_id PK, FK "CHECK follower_id <> following_id"
        int following_id PK, FK
        timestamptz created_at "default CURRENT_TIMESTAMP"
    }
    REVOKED_TOKENS {
        varchar(64) token_hash PK "SHA-256 of a logged-out JWT"
        timestamptz expires_at "NOT NULL"
    }
```

## Notes

- Every foreign key uses `ON DELETE CASCADE`: deleting a user or a book removes its library entries, reviews, playlists, playlist links and follows.
- `user_book_activities.state` has no SQL `CHECK`. The four allowed values are enforced by the Pydantic models (`LibraryBookAdd`, `LibraryBookUpdateStatus`).
- A user can review a book **once** (`UNIQUE (id_user, id_book)`) and cannot have two playlists with the same name (`UNIQUE (id_user, name)`).
- `revoked_tokens` is not linked to `users`: it only stores the hash of JWTs revoked by `POST /auth/logout` until they expire.
- `books` acts as a local cache of Open Library: a row is upserted on `id_book_api` each time a book appears in a search or a recommendation.
