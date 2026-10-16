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
 