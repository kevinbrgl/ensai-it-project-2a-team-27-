# Sequence Diagram - F5: Book recommendations

`GET /api/recommendations` → `recommendations_routes.get_recommendations` → `RecommendationService.get_recommendations`.

Three sources, tried in this order:

1. **Requested genre** (`?genre=...`): popular Open Library books of that genre, reason `"Popular in {genre}"`.
2. **Favorite genres** (no genre given): the 3 most frequent genres among the user's `READING` / `COMPLETED` books and the books they rated 4 or 5, reason `"Because you like {genre}"`.
3. **Fallback**: if there is no genre, Open Library fails, or no book is left, the best rated books reviewed on Ex-Libris, reason `"Top rated"`.

Books already in the user's library are never recommended.

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant UI as React frontend<br/>(HomePage / DiscoverPage)
    participant API as recommendations_routes<br/>get_recommendations()
    participant RS as RecommendationService
    participant SD as StatsDAO
    participant RD as RecommendationDAO
    participant BS as BookService
    participant BD as BookDAO
    participant DB as PostgreSQL
    participant OL as Open Library API

    User->>UI: opens the home page or the Discover page
    UI->>API: GET /api/recommendations?genre=...&sort=rating&limit=24<br/>Authorization: Bearer JWT
    Note over API: deps.get_user() checks the token (401 / 403)
    API->>RS: get_recommendations(id_user, genre, sort, limit)

    alt genre requested
        RS->>RS: genres = [genre]<br/>reason = "Popular in {genre}"
    else no genre: _favorite_genres(id_user)
        RS->>SD: count_genres(id_user)
        SD->>DB: COUNT books per category<br/>(state IN READING, COMPLETED)
        DB-->>SD: rows
        SD-->>RS: list[GenreCount]
        RS->>RD: count_rated_genres(id_user, min_rating=4)
        RD->>DB: COUNT reviewed books per category (rating >= 4)
        DB-->>RD: rows
        RD-->>RS: list[GenreCount]
        RS->>RS: add both counts, keep the top 3 genres<br/>reason = "Because you like {genre}"
    end

    opt at least one genre: _from_open_library()
        RS->>RD: find_library_api_keys(id_user)
        RD->>DB: SELECT id_book_api of the user's library
        DB-->>RD: keys
        RD-->>RS: set of keys to exclude
        loop for each genre
            RS->>BS: search_by_subject(genre, limit=min(2 x limit, 50), sort="rating")
            BS->>OL: GET /search.json?subject=...&sort=rating
            alt Open Library unavailable
                OL-->>BS: error
                BS-->>RS: raise ExternalServiceError
                RS->>RS: log a warning, skip this genre
            else results
                OL-->>BS: docs + ratings_average
                BS-->>RS: list of (BookCreate, Open Library rating)
                loop for each candidate not in the library and not seen yet
                    RS->>BS: save_book(book_create)
                    BS->>BD: upsert(book_create)
                    BD->>DB: INSERT ... ON CONFLICT (id_book_api) DO UPDATE
                    DB-->>BD: row
                    BD-->>BS: Book
                    BS-->>RS: Book
                end
            end
        end
        opt candidates found
            RS->>RD: get_average_ratings(candidate ids)
            RD->>DB: SELECT id_book, AVG(rating) FROM reviews<br/>WHERE id_book = ANY(ids) GROUP BY id_book
            DB-->>RD: local averages
            RD-->>RS: dict id_book -> average
            RS->>RS: score = local average if any, else Open Library rating<br/>_sort(sort), keep the first `limit`
        end
    end

    alt recommendations found
        RS-->>API: list[Recommendation]
    else nothing found: _fallback()
        RS->>RD: find_top_rated_books(id_user, limit, genre)
        RD->>DB: AVG(rating), COUNT(reviews) per reviewed book<br/>not in the user's library (category ILIKE genre)<br/>ORDER BY average DESC, count DESC
        DB-->>RD: rows
        RD-->>RS: list of (Book, average)
        RS->>RS: reason = "Top rated" (or "Top rated in {genre}")<br/>_sort(sort)
        RS-->>API: list[Recommendation]
    end

    API-->>UI: 200 OK - list[Recommendation] (book, score, reason)
    UI-->>User: displays the books with their score and reason
    Note over API,DB: A database error raises DAOError: 500 Internal Server Error
```

`sort` can be `rating` (highest score first, default), `new` (most recent publication first) or `title` (alphabetical).
