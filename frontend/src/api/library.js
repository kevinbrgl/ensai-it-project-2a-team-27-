import { request } from './client';

/** Reading states accepted by the backend. */
export const READING_STATES = ['WANT_TO_READ', 'READING', 'COMPLETED'];

/** GET /library/books?status= → LibraryBookDetails[] */
export function listMyLibrary(status) {
  return request('/library/books', { query: { status } });
}

/** GET /library/favorites → LibraryBookDetails[] */
export function listMyFavorites() {
  return request('/library/favorites');
}

/** POST /library/books → LibraryBookRead */
export function addToLibrary(idBook, state) {
  return request('/library/books', { method: 'POST', json: { id_book: Number(idBook), state } });
}

/** DELETE /library/books/{id} → 204 */
export function removeFromLibrary(idBook) {
  return request(`/library/books/${idBook}`, { method: 'DELETE' });
}

/** PATCH /library/books/{id}/status → LibraryBookRead */
export function updateStatus(idBook, state) {
  return request(`/library/books/${idBook}/status`, { method: 'PATCH', json: { state } });
}

/** POST /library/books/{id}/like → LibraryBookRead (toggles) */
export function toggleLike(idBook) {
  return request(`/library/books/${idBook}/like`, { method: 'POST' });
}

/** POST /library/books/{id}/favorite → LibraryBookRead (toggles) */
export function toggleFavorite(idBook) {
  return request(`/library/books/${idBook}/favorite`, { method: 'POST' });
}
