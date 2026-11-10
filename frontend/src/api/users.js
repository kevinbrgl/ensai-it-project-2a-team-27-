import { request } from './client';

// The backend has no "get user by id" route, so usernames are remembered
// whenever a user object passes through the app (search, followers…).
const knownUsers = new Map();

function remember(users) {
  for (const user of users) knownUsers.set(user.id_user, user);
  return users;
}

/** Returns a user seen earlier in the session, if any. */
export function getKnownUser(idUser) {
  return knownUsers.get(Number(idUser)) || null;
}

/**
 * GET /users/me/settings → UserMe
 * Same as /users/me plus theme, profile_visibility and is_admin.
 */
export async function getMe() {
  const me = await request('/users/me/settings');
  remember([me]);
  return me;
}

/** PATCH /users/me (only the given fields) → UserRead */
export async function updateMe(fields) {
  const me = await request('/users/me', { method: 'PATCH', json: fields });
  remember([me]);
  return me;
}

/** PATCH /users/me/settings { theme?: 'day'|'night', profile_visibility?: 'public'|'private' } → UserMe */
export async function updateSettings(settings) {
  const me = await request('/users/me/settings', { method: 'PATCH', json: settings });
  remember([me]);
  return me;
}

/** PUT /users/me/password → UserRead */
export function changePassword(currentPassword, newPassword) {
  return request('/users/me/password', {
    method: 'PUT',
    json: { current_password: currentPassword, new_password: newPassword },
  });
}

/** GET /users/search?username=&limit= → UserRead[] */
export async function searchUsers(username, limit = 20) {
  return remember(await request('/users/search', { query: { username, limit } }));
}

/** POST /users/{id}/follow → 204 */
export function followUser(idUser) {
  return request(`/users/${idUser}/follow`, { method: 'POST' });
}

/** DELETE /users/{id}/follow → 204 */
export function unfollowUser(idUser) {
  return request(`/users/${idUser}/follow`, { method: 'DELETE' });
}

/** GET /users/{id}/followers → UserRead[] */
export async function getFollowers(idUser) {
  return remember(await request(`/users/${idUser}/followers`));
}

/** GET /users/{id}/following → UserRead[] */
export async function getFollowing(idUser) {
  return remember(await request(`/users/${idUser}/following`));
}

/** GET /users/{id}/library?status= → LibraryBookDetails[] */
export function getUserLibrary(idUser, status) {
  return request(`/users/${idUser}/library`, { query: { status } });
}

/** GET /users/{id}/playlists → PlaylistRead[] */
export function getUserPlaylists(idUser) {
  return request(`/users/${idUser}/playlists`);
}

/** GET /users/me/stats → { books_finished, genres, ratings } */
export function getMyStats() {
  return request('/users/me/stats');
}

/** GET /users/{id}/stats — 403 unless the current user follows them. */
export function getUserStats(idUser) {
  return request(`/users/${idUser}/stats`);
}

/** GET /users/me/quests?status=all|active|completed → Quest[] */
export function getMyQuests(status = 'all') {
  return request('/users/me/quests', { query: { status } });
}