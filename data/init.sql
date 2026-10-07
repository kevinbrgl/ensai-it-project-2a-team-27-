   CREATE TABLE IF NOT EXISTS users (
       id_user         SERIAL PRIMARY KEY,
       username        VARCHAR(30)  NOT NULL UNIQUE,
       email           VARCHAR(100) NOT NULL UNIQUE,
       password_hash   VARCHAR(255) NOT NULL,
       bio             TEXT,
       profile_picture VARCHAR(255)
   );