import { useState } from 'react';
import * as playlistsApi from '../../api/playlists';
import { useToast } from '../../context/ToastContext';
import { useAsync } from '../../hooks/useAsync';
import { Button } from '../ui/Button';
import { Field } from '../ui/Field';
import { Icon } from '../ui/Icon';
import { Modal } from '../ui/Modal';
import { Skeleton } from '../ui/Skeleton';
import { ErrorState } from '../ui/States';
import styles from './AddToPlaylistDialog.module.css';

export function AddToPlaylistDialog({ book, open, onClose }) {
  return (
    <Modal open={open} title="Save to a playlist" onClose={onClose}>
      <PlaylistPicker book={book} />
    </Modal>
  );
}

function PlaylistPicker({ book }) {
  const toast = useToast();
  const { data: playlists, error, loading, reload, setData } = useAsync(playlistsApi.listPlaylistDetails, [book.id_book]);
  const [pending, setPending] = useState(false);
  const [actionError, setActionError] = useState('');
  const [newName, setNewName] = useState('');
  const [nameError, setNameError] = useState('');
  const [creating, setCreating] = useState(false);
  const toggle = async (playlist, contains, created = false) => {
    setPending(true);
    setActionError('');
    try {
      if (contains) {
        await playlistsApi.removeBookFromPlaylist(playlist.id_playlist, book.id_book);
        toast.success(`Removed from “${playlist.name}”.`);
      } else {
        await playlistsApi.addBookToPlaylist(playlist.id_playlist, book.id_book);
        toast.success(`Added to “${playlist.name}”.`);
      }
      setData((list) => list.map((item) => {
        if (item.id_playlist !== playlist.id_playlist) return item;
        const books = contains ? item.books.filter((b) => b.id_book !== book.id_book) : [...item.books, book];
        return { ...item, books };
      }));
    } catch (err) {
      setActionError(created ? `Playlist “${playlist.name}” created. Select it to retry adding this book. ${err.message}` : err.message);
      reload();
    } finally {
      setPending(false);
    }
  };

  const create = async (event) => {
    event.preventDefault();
    const name = newName.trim();
    if (!name) return setNameError('Give the playlist a name.');
    if (name.length > 100) return setNameError('At most 100 characters.');
    setCreating(true);
    setActionError('');
    try {
      const playlist = await playlistsApi.createPlaylist(name);
      setData((list) => [...list, { ...playlist, books: [] }]);
      setNewName('');
      setNameError('');
      await toggle(playlist, false, true);
    } catch (err) {
      setNameError(err.status === 409 ? 'You already have a playlist with this name.' : err.message);
    } finally {
      setCreating(false);
    }
  };

  return (
    <>
      {actionError && <p role="alert" className={styles.error}>{actionError}</p>}
      {error && <ErrorState error={error} onRetry={reload} />}
      {loading && (
        <div className={styles.list} aria-busy="true" aria-label="Loading playlists">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} height={44} radius="var(--radius-md)" />
          ))}
        </div>
      )}
      {!loading && !error && playlists && (
        <ul className={styles.list}>
          {playlists.length === 0 && <li className={styles.empty}>No playlists yet. Create your first one below.</li>}
          {playlists.map((playlist) => {
            const contains = playlist.books.some((item) => item.id_book === book.id_book);
            return (
              <li key={playlist.id_playlist}>
                <button
                  type="button"
                  className={`${styles.playlist} ${contains ? styles.selected : ''}`}
                  onClick={() => toggle(playlist, contains)}
                  disabled={pending || creating}
                  aria-pressed={contains}
                >
                  <span className={styles.box}>{contains && <Icon name="check" size={14} />}</span>
                  <span className={styles.name}>{playlist.name}</span>
                  <span className={`${styles.count} tabular`}>
                    {playlist.books.length}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
      <form className={styles.create} onSubmit={create} noValidate>
        <Field
          label="New playlist"
          placeholder="e.g. Summer reads"
          value={newName}
          disabled={creating}
          maxLength={100}
          onChange={(e) => {
            setNewName(e.target.value);
            setNameError('');
          }}
          error={nameError}
        />
        <Button type="submit" icon="plus" loading={creating} disabled={loading || !!error || pending || !newName.trim()} className={styles.createButton}>
          Create &amp; add
        </Button>
      </form>
    </>
  );
}
