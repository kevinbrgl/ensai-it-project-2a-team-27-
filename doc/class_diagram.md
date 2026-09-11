# Diagramme de Classes Métier (POO) - Ex-Libris

```mermaid
%%{init: {"class": {"defaultRenderer": "elk"}} }%%
classDiagram
    direction LR

    %% Data Models
    class User {
        +int id_user
        +String username
        +String email
        +String password_hash
        +String bio
        +String profile_picture
    }
    class Book {
        +int id_book
        +String title
        +String author
        +String category
        +Date publish_date
        +String description
        +String cover_image
    }
    class ReadingState {
        <<enumeration>>
        TO_READ
        CURRENTLY_READING
        READ
        ABANDONED
    }
    class UserBookActivity {
        +ReadingState state
        +Boolean is_liked
        +Boolean is_favorite
    }
    class Review {
        +int id_review
        +int rating
        +String comment
    }
    class Playlist {
        +int id_playlist
        +String name
    }

    %% Service Classes
    class UserService {
        +followUser(followerId: int, followingId: int)
        +unfollowUser(followerId: int, followingId: int)
    }
    class BookActivityService {
        +updateReadingState(userId: int, bookId: int, state: ReadingState)
        +toggleLike(userId: int, bookId: int)
        +toggleFavorite(userId: int, bookId: int)
    }
    class ReviewService {
        +createReview(userId: int, bookId: int, rating: int, comment: String)
    }
    class PlaylistService {
        +createPlaylist(userId: int, name: String)
        +addBookToPlaylist(playlistId: int, bookId: int)
        +removeBookFromPlaylist(playlistId: int, bookId: int)
    }

    %% Models <-> Services Links (Placés en premier pour forcer l'alignement)
    UserService ..> User : uses
    BookActivityService ..> UserBookActivity : uses
    ReviewService ..> Review : uses
    PlaylistService ..> Playlist : uses

    %% Model Relations
    User "1" --> "0..*" UserBookActivity
    Book "1" --> "0..*" UserBookActivity
    User "1" --> "0..*" Review
    Book "1" --> "0..*" Review
    User "1" --> "0..*" Playlist
    Playlist "0..*" --> "0..*" Book
