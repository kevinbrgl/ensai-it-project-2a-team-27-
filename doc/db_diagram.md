# Diagramme de Classes - Ex-Libris

```mermaid
classDiagram
    class User {
        +int id_user
        +String username
        +String name
        +String lastname
        +String email
        +String password_hash
        +String google_id
        +String bio
        +String profile_picture
        +Boolean is_private
        +Boolean dark_mode
        +Timestamp created_at
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
        A_LIRE
        EN_COURS
        LU
        ABANDONNE
    }

    class User_Book_Activity {
        +ReadingState state
        +Boolean is_liked
        +Boolean is_favorite
        +Timestamp updated_at
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
        +Boolean is_public
    }

    %% Relations
    User "1" -- "*" User_Book_Activity : gère >
    Book "1" -- "*" User_Book_Activity : est suivi dans >
    
    User "1" -- "*" Review : écrit >
    Book "1" -- "*" Review : reçoit >
    
    User "1" -- "*" Playlist : crée >
    Playlist "*" -- "*" Book : contient >
    
    User "*" -- "*" User : s'abonne à >
```