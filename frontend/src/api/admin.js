import { request } from './client';

/** POST /admin/users/{id}/suspend { days } → { id_user, username, is_banned, suspended_until } */
export function suspendUser(idUser, days) {
  return request(`/admin/users/${idUser}/suspend`, { method: 'POST', json: { days } });
}

/** POST /admin/users/{id}/ban → { id_user, username, is_banned, suspended_until } */
export function banUser(idUser) {
  return request(`/admin/users/${idUser}/ban`, { method: 'POST' });
}

/** DELETE /admin/reviews/{id} → 204 (any review, admin only) */
export function moderateReview(idReview) {
  return request(`/admin/reviews/${idReview}`, { method: 'DELETE' });
}