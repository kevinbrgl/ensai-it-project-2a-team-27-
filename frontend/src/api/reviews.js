import { request } from './client';

/** GET /books/{id}/reviews → { id_book, average_rating, review_count, reviews } */
export function getBookReviews(idBook) {
  return request(`/books/${idBook}/reviews`);
}

/** POST /books/{id}/reviews → ReviewRead */
export function createReview(idBook, { rating, comment }) {
  return request(`/books/${idBook}/reviews`, { method: 'POST', json: { rating, comment: comment || null } });
}

/** PUT /reviews/{id} → ReviewRead */
export function updateReview(idReview, { rating, comment }) {
  return request(`/reviews/${idReview}`, { method: 'PUT', json: { rating, comment: comment || null } });
}

/** DELETE /reviews/{id} → 204 */
export function deleteReview(idReview) {
  return request(`/reviews/${idReview}`, { method: 'DELETE' });
}

/** GET /users/{id}/reviews → ReviewRead[] (newest first) */
export function listUserReviews(idUser) {
  return request(`/users/${idUser}/reviews`);
}
