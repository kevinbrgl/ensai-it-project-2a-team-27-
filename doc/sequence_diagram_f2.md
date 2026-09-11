sequenceDiagram
    actor User
    participant UI as Interface
    participant API
    participant BusinessLogic
    participant DAO
    participant OL as Open Library API
 
    User->>UI: enters title/author
    UI->>API: GET /books/search?q=...
    API->>BusinessLogic: processSearchRequest(query)
 
    BusinessLogic->>BusinessLogic: validateAndSanitize(query)
    BusinessLogic->>OL: GET /search.json?q=...
 
    alt Open Library unavailable / timeout
        OL-->>BusinessLogic: error / timeout
        BusinessLogic-->>API: ExternalServiceException
        API-->>UI: 502 Bad Gateway
        UI-->>User: "search temporarily unavailable"
    else Open Library responds
        OL-->>BusinessLogic: raw results (JSON)
        BusinessLogic->>BusinessLogic: normalize(title, authors, cover, year, editions)
 
        BusinessLogic->>DAO: storeCachedSearch(query, results)
        activate DAO
        DAO-->>BusinessLogic: ack
        deactivate DAO
 
        BusinessLogic-->>API: formattedResults (DTO)
        API-->>UI: 200 OK - book list
        UI-->>User: displays results
    end