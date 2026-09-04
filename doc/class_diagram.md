# Diagramme de Classes Métier (POO) - Ex-Libris

```mermaid
%%{init: {'theme': 'neutral'}}%%
classDiagram
    direction TB

    class User {
        -id_user : Integer
        -username : String
        -name : String
        -lastname : String
        -email : String
        -password_hash : String
        -google_id : String
        -bio : String
        -profile_picture : String
        -is_private : Boolean
        -dark_mode : Boolean
        -created_at : DateTime
        +updateProfile(name : String, bio : String, profile_picture : String) void
        +toggleDarkMode() void
        +follow(user : User) void
        +unfollow(user : User) void
        +createPlaylist(name : String, is_public : Boolean) Playlist
    }

    class Book {
        -id_book : Integer
        -title : String
        -author : String
        -category : String
        -publish_date : Date
        -description : String
        -cover_image : String
        +getAverageRating() Float
        +getReviews() List~Review~
    }

    class ReadingState {
        <<enumeration>>
        TO_READ
        CURRENTLY_READING
        READ
        ABANDONED
    }

    class UserBookActivity {
        -state : ReadingState
        -is_liked : Boolean
        -is_favorite : Boolean
        -updated_at : DateTime
        +updateState(newState : ReadingState) void
        +toggleLike() void
        +toggleFavorite() void
    }

    class Review {
        -id_review : Integer
        -rating : Integer
        -comment : String
        -created_at : DateTime
        +editComment(newComment : String, newRating : Integer) void
    }

    class Playlist {
        -id_playlist : Integer
        -name : String
        -is_public : Boolean
        +addBook(book : Book) void
        +removeBook(book : Book) void
        +toggleVisibility() void
    }

    %% Relations
    User "1" --> "0..*" UserBookActivity : manages
    Book "1" --> "0..*" UserBookActivity : is tracked in
    
    User "1" --> "0..*" Review : writes
    Book "1" --> "0..*" Review : receives
    
    User "1" --> "0..*" Playlist : creates
    Playlist "0..*" --> "0..*" Book : contains
    
    User "0..*" --> "0..*" User : follows
```
