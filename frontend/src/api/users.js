import { request } from './client';

// Usernames are remembered whenever a user object passes through the app
// (search, followers, profile…), so lists of reviews can show them without
// one request per user.
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
 * GET /users/{id} → UserPublic: id_user, username, bio, profile_picture and
 * profile_visibility (never the email address).
 */
export async function getUser(idUser) {
  const user = await request(`/users/${idUser}`);
  remember([user]);
  return user;
}

/** GET /users/me → the signed-in reader's profile. */
export function getMyProfile() {
  return request('/users/me');
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

/** GET /users/search?username=&limit= → UserPublic[] */
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

/** GET /users/{id}/followers → UserPublic[] */
export async function getFollowers(idUser) {
  return remember(await request(`/users/${idUser}/followers`));
}

/** GET /users/{id}/following → UserPublic[] */
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

/** GET /users/me/stats → { books_finished, pages_read, genres, ratings } */
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

export function getMyAchievements(status = 'all') {
  return request('/users/me/achievements', { query: { status } });
}

export function getUserGenreWheel(idUser) {
  return request(`/users/${idUser}/genre-wheel`);
}
