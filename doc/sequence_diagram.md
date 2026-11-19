# Ex-Libris — Sequence Diagram (F2: Search + F3: Add to Library)

High-level view, one participant per layer of the application. The detailed versions are [sequence_diagram_detailed.md](sequence_diagram_detailed.md), [sequence_diagram_f2.md](sequence_diagram_f2.md) and [sequence_diagram_f3.md](sequence_diagram_f3.md).

```mermaid
sequenceDiagram
    actor User
    participant UI as React frontend
    participant API as FastAPI routes
    participant Service as Services
    participant DAO as DAO
    participant DB as PostgreSQL
    participant OL as Open Library API

    %% ===== F2: Book search =====
    User->>UI: enters a title or an author
    UI->>API: GET /api/books/search?q=...
    API->>Service: BookService.search_books(query)
    Service->>OL: GET /search.json?q=...
    OL-->>Service: results (JSON)
    Service->>DAO: BookDAO.upsert(book) for each result
    DAO->>DB: INSERT ... ON CONFLICT (id_book_api) DO UPDATE
    DB-->>DAO: rows with id_book
    DAO-->>Service: list[Book]
    Service-->>API: list[Book]
    API-->>UI: 200 OK - list of books
    UI-->>User: displays the results

    %% ===== F3: Add a book to the library =====
    User->>UI: picks a reading status on a book
    UI->>API: POST /api/library/books {id_book, state}
    API->>Service: LibraryService.add_book_to_library(id_user, book_in)
    Service->>DAO: LibraryDAO.add_book(id_user, book_in)
    DAO->>DB: INSERT INTO user_book_activities

    alt book already in the library
        DB-->>DAO: UniqueViolation
        DAO-->>Service: BookAlreadyInLibraryError
        Service-->>API: BookAlreadyInLibraryError
        API-->>UI: 409 Conflict
        UI-->>User: "Book is already in the library."
    else book added
        DB-->>DAO: new row
        DAO-->>Service: LibraryBookRead
        Service-->>API: LibraryBookRead
        API-->>UI: 201 Created
        UI-->>User: shows the new status
    end
```
