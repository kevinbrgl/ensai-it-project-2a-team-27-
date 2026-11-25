-- Optional demo for a local database. Run after init.sql.
-- Resolve database-generated IDs by unique keys so existing rows keep their IDs.
DO $demo$
DECLARE
    demo_hash CONSTANT text := '$2b$12$./Xe88N1f/CSuYfMm5yf4O5NuhXuXvV84SiMOtxGF3jEqxqvrrR7y';
    alex_id integer;
    jo_id integer;
    playlist_id integer;
BEGIN
    INSERT INTO users (username, email, password_hash, bio) VALUES
        ('demo_alex', 'demo_alex@example.com', demo_hash, 'Reading my way through science fiction and classics.'),
        ('demo_jo', 'demo_jo@example.com', demo_hash, 'Always looking for a book to share at reading club.')
    ON CONFLICT (username) DO NOTHING;

    -- A username already claimed by a different account must not receive demo data.
    SELECT id_user INTO STRICT alex_id FROM users
    WHERE username = 'demo_alex' AND email = 'demo_alex@example.com';
    SELECT id_user INTO STRICT jo_id FROM users
    WHERE username = 'demo_jo' AND email = 'demo_jo@example.com';

    -- Jo is the demo administrator. Alex stays a regular reader.
    -- An UPDATE, not the INSERT, so a database seeded earlier gets it too.
    UPDATE users SET is_admin = TRUE WHERE id_user = jo_id AND NOT is_admin;

    -- Open Library work keys also identify these books when a reader searches for them.
    INSERT INTO books (id_book_api, title, author, category, publish_date, num_pages, cover_image)
    VALUES
        ('/works/OL893414W', 'Dune', 'Frank Herbert', 'Science fiction', DATE '1965-01-01',
         606, 'https://covers.openlibrary.org/b/id/11481354-M.jpg'),
        ('/works/OL450063W', 'Frankenstein', 'Mary Shelley', 'Gothic fiction', DATE '1818-01-01',
         240, 'https://covers.openlibrary.org/b/id/12356249-M.jpg'),
        ('/works/OL27482W', 'The Hobbit', 'J.R.R. Tolkien', 'Fantasy', DATE '1937-01-01',
         310, 'https://covers.openlibrary.org/b/id/14627509-M.jpg'),
        ('/works/OL66554W', 'Pride and Prejudice', 'Jane Austen', 'Romance', DATE '1813-01-01',
         351, 'https://covers.openlibrary.org/b/id/14348537-M.jpg')
    ON CONFLICT (id_book_api) DO NOTHING;

    INSERT INTO user_book_activities
        (id_user, id_book, state, is_favorite, is_liked, started_at, finished_at)
    SELECT sample.reader, b.id_book, sample.state, sample.favorite, sample.liked,
           sample.started, sample.finished
    FROM (VALUES
        (alex_id, '/works/OL893414W', 'COMPLETED', TRUE, TRUE, DATE '2026-09-01', DATE '2026-09-19'),
        (alex_id, '/works/OL450063W', 'COMPLETED', FALSE, TRUE, DATE '2026-10-01', DATE '2026-10-12'),
        (alex_id, '/works/OL66554W', 'READING', FALSE, FALSE, DATE '2026-11-01', NULL),
        (jo_id, '/works/OL27482W', 'COMPLETED', TRUE, TRUE, DATE '2026-10-02', DATE '2026-10-16'),
        (jo_id, '/works/OL893414W', 'WANT_TO_READ', FALSE, FALSE, NULL, NULL)
    ) AS sample(reader, work_key, state, favorite, liked, started, finished)
    JOIN books b ON b.id_book_api = sample.work_key
    ON CONFLICT (id_user, id_book) DO NOTHING;

    INSERT INTO reviews (id_user, id_book, rating, comment)
    SELECT sample.reader, b.id_book, sample.rating, sample.comment
    FROM (VALUES
        (alex_id, '/works/OL893414W', 5, 'The politics of water made Arrakis feel real to me.'),
        (alex_id, '/works/OL450063W', 4, 'The creature telling his own story changed how I saw Victor.'),
        (jo_id, '/works/OL27482W', 5, 'I would read the riddle scene aloud at our next book club.')
    ) AS sample(reader, work_key, rating, comment)
    JOIN books b ON b.id_book_api = sample.work_key
    ON CONFLICT (id_user, id_book) DO NOTHING;

    INSERT INTO user_follows (follower_id, following_id) VALUES (alex_id, jo_id)
    ON CONFLICT (follower_id, following_id) DO NOTHING;

    INSERT INTO playlists (id_user, name) VALUES (alex_id, 'Book club picks')
    ON CONFLICT (id_user, name) DO NOTHING;
    SELECT id_playlist INTO STRICT playlist_id FROM playlists
    WHERE id_user = alex_id AND name = 'Book club picks';

    INSERT INTO playlist_books (id_playlist, id_book)
    SELECT playlist_id, id_book FROM books
    WHERE id_book_api IN ('/works/OL893414W', '/works/OL450063W')
    ON CONFLICT (id_playlist, id_book) DO NOTHING;
END;
$demo$;
