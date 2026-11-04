   CREATE TABLE IF NOT EXISTS users (
       id_user         SERIAL PRIMARY KEY,
       username        VARCHAR(30)  NOT NULL UNIQUE,
       email           VARCHAR(100) NOT NULL UNIQUE,
       password_hash   VARCHAR(255) NOT NULL,
       bio             TEXT,
       profile_picture VARCHAR(255)
   );

   CREATE TABLE IF NOT EXISTS books (
       id_book         SERIAL PRIMARY KEY,
       id_book_api     VARCHAR(100) UNIQUE,
       title           VARCHAR(255) NOT NULL,
       author          VARCHAR(255),
       category        VARCHAR(100),
       publish_date    DATE,
       description     TEXT,
       cover_image     VARCHAR(255)
   );


   CREATE TABLE IF NOT EXISTS user_book_activities (
    id_user     INT REFERENCES users(id_user) ON DELETE CASCADE,
    id_book     INT REFERENCES books(id_book) ON DELETE CASCADE,
    state       VARCHAR(50) NOT NULL,
    is_liked    BOOLEAN DEFAULT FALSE,
    is_favorite BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (id_user, id_book)

);


CREATE TABLE IF NOT EXISTS revoked_tokens (
    token_hash VARCHAR(64) PRIMARY KEY,
    expires_at TIMESTAMPTZ NOT NULL
);
 


CREATE TABLE IF NOT EXISTS user_follows (
    follower_id  INT REFERENCES users(id_user) ON DELETE CASCADE,
    following_id INT REFERENCES users(id_user) ON DELETE CASCADE,
    created_at   TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (follower_id, following_id),
    CHECK (follower_id <> following_id)
);

CREATE TABLE IF NOT EXISTS playlists (
    id_playlist SERIAL PRIMARY KEY,
    id_user     INT NOT NULL REFERENCES users(id_user) ON DELETE CASCADE,
    name        VARCHAR(100) NOT NULL,
    UNIQUE (id_user, name)
);

CREATE TABLE IF NOT EXISTS playlist_books (
    id_playlist INT REFERENCES playlists(id_playlist) ON DELETE CASCADE,
    id_book     INT REFERENCES books(id_book) ON DELETE CASCADE,
    PRIMARY KEY (id_playlist, id_book)
);

CREATE TABLE IF NOT EXISTS reviews (
    id_review   SERIAL PRIMARY KEY,
    id_user     INT NOT NULL REFERENCES users(id_user) ON DELETE CASCADE,
    id_book     INT NOT NULL REFERENCES books(id_book) ON DELETE CASCADE,
    rating      INT NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment     TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (id_user, id_book)
);