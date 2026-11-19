# Ex-Libris — Detailed Sequence Diagram (F2: Search + F3: Add to Library)

Same scenario as [sequence_diagram.md](sequence_diagram.md), with the authentication step and all the error cases. Each feature also has its own file: [F2](sequence_diagram_f2.md), [F3](sequence_diagram_f3.md).

```mermaid
---
config:
  theme: neo
  look: classic
---
sequenceDiagram
    actor User
    participant UI as React frontend
    participant API as FastAPI routes
    participant Auth as deps.get_user()
    participant Service as Services
    participant DAO as DAO
    participant DB as PostgreSQL
    participant OL as Open Library API

    %% ===== F2: Book search =====
    User->>UI: enters a title or an author
    UI->>API: GET /api/books/search?q=...&limit=12 (Bearer JWT)
    API->>Auth: check the token
    Auth-->>API: User (or 401 / 403)
    API->>Service: BookService.search_books(query, limit)
    Service->>Service: strip the query (blank query: return [])
    Service->>OL: GET /search.json?q=...&fields=...

    alt query rejected (HTTP 422, e.g. "the")
        OL-->>Service: 422
        Service-->>API: InvalidSearchQueryError
        API-->>UI: 400 Bad Request
        UI-->>User: "Search is too generic, add more words."
    else Open Library unavailable / timeout / invalid JSON
        OL-->>Service: error / timeout
        Service-->>API: ExternalServiceError
        API-->>UI: 502 Bad Gateway
        UI-->>User: "Open Library service is unavailable."
    else Open Library responds
        OL-->>Service: docs (JSON)
        loop for each doc with a title
            Service->>Service: _doc_to_book_create(doc)<br/>(title, authors, first subject, year, cover, pages)
            Service->>DAO: BookDAO.upsert(book_create)
            DAO->>DB: INSERT INTO books ... ON CONFLICT (id_book_api) DO UPDATE
            DB-->>DAO: row
            DAO-->>Service: Book (with id_book)
        end
        Service-->>API: list[Book]
        API-->>UI: 200 OK - list of books
        UI-->>User: displays the results
    end

    %% ===== F3: Add a book to the library =====
    User->>UI: picks a book and a reading status
    UI->>API: POST /api/library/books {id_book, state} (Bearer JWT)
    API->>Auth: check the token
    Auth-->>API: User (or 401 / 403)
    API->>API: validate LibraryBookAdd (422 if state is unknown)
    API->>Service: LibraryService.add_book_to_library(id_user, book_in)
    Service->>DAO: LibraryDAO.add_book(id_user, book_in)
    DAO->>DB: INSERT INTO user_book_activities (id_user, id_book, state)

    alt book already in the library
        DB-->>DAO: UniqueViolation
        DAO-->>Service: BookAlreadyInLibraryError
        Service-->>API: BookAlreadyInLibraryError
        API-->>UI: 409 Conflict
        UI-->>User: "Book is already in the library."
    else book not in the catalogue
        DB-->>DAO: ForeignKeyViolation
        DAO-->>Service: BookNotFoundError
        Service-->>API: BookNotFoundError
        API-->>UI: 404 Not Found
        UI-->>User: "Book not found in the local catalog."
    else book added
        DB-->>DAO: new row
        DAO-->>Service: LibraryBookRead
        Service-->>API: LibraryBookRead
        API-->>UI: 201 Created
        UI-->>User: shows the confirmation
    end
```
