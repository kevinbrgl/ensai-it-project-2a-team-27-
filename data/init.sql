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