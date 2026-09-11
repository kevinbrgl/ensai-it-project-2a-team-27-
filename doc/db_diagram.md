# Database Diagram - Ex-Libris

```mermaid
erDiagram
    USERS ||--o{ USER_BOOK_ACTIVITIES : "manages"
    BOOKS ||--o{ USER_BOOK_ACTIVITIES : "tracked_in"
    USERS ||--o{ REVIEWS : "writes"
    BOOKS ||--o{ REVIEWS : "receives"
    USERS ||--o{ PLAYLISTS : "creates"
    PLAYLISTS }o--o{ PLAYLIST_BOOKS : "contains"
    BOOKS }o--o{ PLAYLIST_BOOKS : "includes"
    USERS }o--o{ USER_FOLLOWS : "follower"
    USERS }o--o{ USER_FOLLOWS : "following"

    USERS {
        int id_user PK
        varchar username UK
        varchar email UK
        varchar password_hash
        text bio
        varchar profile_picture
    }
    BOOKS {
        int id_book PK
        varchar title
        varchar author
        varchar category
        date publish_date
        text description
        varchar cover_image
    }
    USER_BOOK_ACTIVITIES {
        int id_user PK, FK
        int id_book PK, FK
        varchar state "CHECK: TO_READ, CURRENTLY_READING, READ, ABANDONED"
        boolean is_liked
        boolean is_favorite
    }
    REVIEWS {
        int id_review PK
        int id_user FK
        int id_book FK
        int rating "CHECK (1-5)"
        text comment
        timestamp created_at
    }
    PLAYLISTS {
        int id_playlist PK
        int id_user FK
        varchar name
        timestamp updated_at
    }
    PLAYLIST_BOOKS {
        int id_playlist PK, FK
        int id_book PK, FK
    }
    USER_FOLLOWS {
        int follower_id PK, FK
        int following_id PK, FK
    }
