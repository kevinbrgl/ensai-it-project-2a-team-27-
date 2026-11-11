import { request } from './client';

// Books rarely change, so details are cached for the session. This avoids
// refetching the same book when listing a user's reviews, for instance.
const bookCache = new Map();

function remember(books) {
  for (const book of books) bookCache.set(book.id_book, Promise.resolve(book));
  return books;
}

/** GET /books/search?q=&limit= — searches Open Library and saves results locally. */
export async function searchBooks(q, limit = 12, signal) {
  return remember(await request('/books/search', { query: { q, limit }, signal }));
}

/** GET /books?category=&author= — local catalog, optionally filtered. */
export async function listBooks({ category, author } = {}, signal) {
  return remember(await request('/books', { query: { category, author }, signal }));
}

/** GET /books/{id} */
export function getBook(bookId) {
  const id = Number(bookId);
  if (!bookCache.has(id)) {
    const promise = request(`/books/${id}`).catch((error) => {
      bookCache.delete(id);
      throw error;
    });
    bookCache.set(id, promise);
  }
  return bookCache.get(id);
}
