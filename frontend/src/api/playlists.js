import { request } from './client';

/** GET /playlists → PlaylistRead[] */
export function listPlaylists() {
  return request('/playlists');
}

/** GET /playlists/{id} → PlaylistDetails (with books) */
export function getPlaylist(id) {
  return request(`/playlists/${id}`);
}

/** The list response contains names. Fetch the contents for cover and membership views. */
export async function listPlaylistDetails() {
  const playlists = await listPlaylists();
  return Promise.all(playlists.map((playlist) => getPlaylist(playlist.id_playlist)));
}

/** POST /playlists → PlaylistRead */
export function createPlaylist(name) {
  return request('/playlists', { method: 'POST', json: { name } });
}

/** PATCH /playlists/{id} → PlaylistRead */
export function renamePlaylist(id, name) {
  return request(`/playlists/${id}`, { method: 'PATCH', json: { name } });
}

/** DELETE /playlists/{id} → 204 */
export function deletePlaylist(id) {
  return request(`/playlists/${id}`, { method: 'DELETE' });
}

/** POST /playlists/{id}/books → PlaylistBookRead */
export function addBookToPlaylist(id, idBook) {
  return request(`/playlists/${id}/books`, { method: 'POST', json: { id_book: Number(idBook) } });
}

/** DELETE /playlists/{id}/books/{idBook} → 204 */
export function removeBookFromPlaylist(id, idBook) {
  return request(`/playlists/${id}/books/${idBook}`, { method: 'DELETE' });
}
