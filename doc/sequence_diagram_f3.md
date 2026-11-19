# Sequence Diagram - F3: Add a book to the library

`POST /api/library/books` → `library_routes.add_book` → `LibraryService.add_book_to_library` → `LibraryDAO.add_book`.

Open Library is not called here: the book is already in the local `books` table, because the user found it through a search, a recommendation or the catalogue (see F2). The request only sends its `id_book`.

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant UI as React frontend<br/>(LibraryControl)
    participant API as library_routes<br/>add_book()
    participant Auth as deps.get_user()
    participant LS as LibraryService
    participant DAO as LibraryDAO
    participant DB as PostgreSQL

    User->>UI: chooses a reading status on a book<br/>(WANT_TO_READ, READING, COMPLETED, ABANDONED)
    UI->>API: POST /api/library/books<br/>{"id_book": 12, "state": "WANT_TO_READ"}
    API->>Auth: check the token
    break no token, invalid or revoked token, banned or suspended account
        Auth-->>UI: 401 / 403
    end
    Auth-->>API: User
    API->>API: validate body (LibraryBookAdd)
    break unknown state or missing id_book
        API-->>UI: 422 Unprocessable Entity
    end
    API->>LS: add_book_to_library(id_user, book_in)
    LS->>DAO: add_book(id_user, book_in)
    DAO->>DB: INSERT INTO user_book_activities (id_user, id_book, state)<br/>VALUES (...) RETURNING *

    alt book already in the library (UniqueViolation on the primary key)
        DB-->>DAO: UniqueViolation
        DAO-->>LS: raise BookAlreadyInLibraryError
        LS-->>API: BookAlreadyInLibraryError
        API-->>UI: 409 Conflict
        UI-->>User: "Book is already in the library."
    else book not in the catalogue (ForeignKeyViolation)
        DB-->>DAO: ForeignKeyViolation
        DAO-->>LS: raise BookNotFoundError
        LS-->>API: BookNotFoundError
        API-->>UI: 404 Not Found
        UI-->>User: "Book not found in the local catalog."
    else entry created
        DB-->>DAO: row (is_liked = false, is_favorite = false)
        DAO-->>LS: LibraryBookRead
        LS-->>API: LibraryBookRead
        API-->>UI: 201 Created - LibraryBookRead
        UI-->>User: shows the new status on the book
    end

    Note over API,DB: Any other database error raises DAOError: 500 Internal Server Error
```

Once the book is in the library, the same entry is updated by `PATCH /api/library/books/{id_book}/status`, `PATCH .../dates`, `POST .../like`, `POST .../favorite` and removed by `DELETE /api/library/books/{id_book}`.
