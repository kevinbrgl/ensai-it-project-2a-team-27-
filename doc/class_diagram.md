---

### Diagramme 2 : Modèles et Services

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
        +int id_book_api
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
        +Timestamp created_at
    }
    class Playlist {
        +int id_playlist
        +String name
        +Timestamp updated_at
    }

    %% Service Classes (Reliés aux routes API)
    class UserService {
        +getProfile(userId: int) User
        +followUser(followerId: int, followingId: int)
        +unfollowUser(followerId: int, followingId: int)
    }
    class BookService {
        +searchBooks(query: String) List~Book~
        +getBookDetails(bookId: int) Book
    }
    class BookActivityService {
        +updateReadingState(userId: int, bookId: int, state: ReadingState)
        +toggleLike(userId: int, bookId: int)
        +toggleFavorite(userId: int, bookId: int)
    }
    class ReviewService {
        +createReview(userId: int, bookId: int, rating: int, comment: String)
        +deleteReview(reviewId: int)
    }
    class PlaylistService {
        +createPlaylist(userId: int, name: String)
        +addBookToPlaylist(playlistId: int, bookId: int)
        +removeBookFromPlaylist(playlistId: int, bookId: int)
    }

    %% Models <-> Services Links 
    UserService ..> User : uses
    BookService ..> Book : uses
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
