# Sequence Diagram - F2: Search a book

`GET /api/books/search` → `books_routes.search_books` → `BookService.search_books` → `OpenLibraryClient.search` + `BookDAO.upsert`.

Each book found is saved (or refreshed) in the local `books` table. That gives it an `id_book` that the library, playlist and review routes can use.

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant UI as React frontend<br/>(DiscoverPage)
    participant API as books_routes<br/>search_books()
    participant Auth as deps.get_user()
    participant BS as BookService
    participant DAO as BookDAO
    participant DB as PostgreSQL
    participant OL as Open Library via OpenLibraryClient

    User->>UI: types a title or an author
    UI->>UI: isTooGeneric(query)
    break query made only of stopwords ("the", "a", "le", ...)
        UI-->>User: "Search is too generic, add more words."
    end
    UI->>API: GET /api/books/search?q=...&limit=12<br/>Authorization: Bearer JWT
    API->>Auth: check the token
    break no token, invalid or revoked token, banned or suspended account
        Auth-->>UI: 401 / 403
    end
    Auth-->>API: User
    API->>BS: search_books(query, limit)
    BS->>BS: query.strip()

    alt blank query
        BS-->>API: []
        API-->>UI: 200 OK - []
    else non-blank query
        BS->>OL: GET /search.json?q=...&limit=...&fields=...
        alt query rejected by Open Library (HTTP 422, e.g. "the")
            OL-->>BS: 422 Unprocessable Entity
            BS-->>API: raise InvalidSearchQueryError
            API-->>UI: 400 Bad Request
            UI-->>User: "Search is too generic, add more words."
        else network error, timeout, HTTP error or invalid JSON
            OL-->>BS: error
            BS-->>API: raise ExternalServiceError
            API-->>UI: 502 Bad Gateway
            UI-->>User: "Open Library service is unavailable."
        else results received
            OL-->>BS: {"docs": [...]}
            loop for each doc
                BS->>BS: _doc_to_book_create(doc)<br/>(skip docs without a title)
                BS->>DAO: upsert(book_create)
                DAO->>DB: INSERT INTO books ...<br/>ON CONFLICT (id_book_api) DO UPDATE ... RETURNING *
                DB-->>DAO: row
                DAO-->>BS: Book (with id_book)
            end
            BS-->>API: list[Book]
            API-->>UI: 200 OK - list[Book]
            UI-->>User: displays the result cards
        end
    end

    Note over API,DB: A database error raises DAOError: 500 Internal Server Error
```
