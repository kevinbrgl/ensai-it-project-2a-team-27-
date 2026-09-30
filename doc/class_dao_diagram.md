```mermaid
classDiagram
    direction TB

    class GenericDAO~T, ID~ {
        <<interface>>
        +findById(id) T
        +findAll() List~T~
        +save(entity) T
        +update(entity) void
        +deleteById(id) void
    }

    class UserDAO {
        <<interface>>
        +findByUsername(username) User
        +findByEmail(email) User
        +addFollow(followerId, followingId) void
        +removeFollow(followerId, followingId) void
    }

    class BookDAO {
        <<interface>>
        +findByCategory(category) List~Book~
        +findByAuthor(author) List~Book~
    }

    class ReviewDAO {
        <<interface>>
        +findByBookId(bookId) List~Review~
        +findByUserId(userId) List~Review~
    }

    class PlaylistDAO {
        <<interface>>
        +findByUserId(userId) List~Playlist~
        +addBook(playlistId, bookId) void
        +removeBook(playlistId, bookId) void
    }

    class UserBookActivityDAO {
        <<interface>>
        +findByUserAndBook(userId, bookId) UserBookActivity
        +findFavoritesByUserId(userId) List~Book~
    }

    GenericDAO <|-- UserDAO
    GenericDAO <|-- BookDAO
    GenericDAO <|-- ReviewDAO
    GenericDAO <|-- PlaylistDAO
    GenericDAO <|-- UserBookActivityDAO
