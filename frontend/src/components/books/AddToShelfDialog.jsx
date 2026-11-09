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
import styles from './AddToShelfDialog.module.css';

/** Lists the user's shelves (playlists) and toggles the book in each of them. */
// Shelves only list names; their details tell whether the book is on them.
async function loadShelves(idBook) {
  const list = await playlistsApi.listPlaylists();
  const details = await Promise.all(list.map((p) => playlistsApi.getPlaylist(p.id_playlist)));
  return details.map((d) => ({
    id_playlist: d.id_playlist,
    name: d.name,
    count: d.books.length,
    contains: d.books.some((b) => b.id_book === idBook),
  }));
}

/** Lists the user's shelves (playlists) and toggles the book in each of them. */
export function AddToShelfDialog({ book, open, onClose }) {
  return (
    <Modal open={open} title="Save to a shelf" onClose={onClose}>
      <ShelfPicker book={book} />
    </Modal>
  );
}

function ShelfPicker({ book }) {
  const toast = useToast();
  const { data: shelves, error, reload, setData: setShelves } = useAsync(() => loadShelves(book.id_book), [book.id_book]);
  const [pending, setPending] = useState(null);
  const [newName, setNewName] = useState('');
  const [nameError, setNameError] = useState('');
  const [creating, setCreating] = useState(false);
  const toggle = async (shelf) => {
    setPending(shelf.id_playlist);
    try {
      if (shelf.contains) {
        await playlistsApi.removeBookFromPlaylist(shelf.id_playlist, book.id_book);
        toast.success(`Removed from “${shelf.name}”.`);
      } else {
        await playlistsApi.addBookToPlaylist(shelf.id_playlist, book.id_book);
        toast.success(`Added to “${shelf.name}”.`);
      }
      setShelves((list) =>
        list.map((s) => (s.id_playlist === shelf.id_playlist
            ? { ...s, contains: !s.contains, count: s.count + (s.contains ? -1 : 1) }
            : s)),
      );
    } catch (err) {
      toast.error(err.message);
    } finally {
      setPending(null);
    }
  };

  const create = async (event) => {
    event.preventDefault();
    const name = newName.trim();
    if (!name) return setNameError('Give the shelf a name.');
    if (name.length > 100) return setNameError('At most 100 characters.');
    setCreating(true);
    try {
      const shelf = await playlistsApi.createPlaylist(name);
      await playlistsApi.addBookToPlaylist(shelf.id_playlist, book.id_book);
      setShelves((list) => [...(list || []), { ...shelf, count: 1, contains: true }]);
      setNewName('');
      setNameError('');
      toast.success(`Created “${shelf.name}” with this book.`);
    } catch (err) {
      setNameError(err.status === 409 ? 'You already have a shelf with this name.' : err.message);
    } finally {
      setCreating(false);
    }
  };

  return (
    <>
      {error && <ErrorState error={error} onRetry={reload} />}
      {!error && !shelves && (
        <div className={styles.list}>
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} height={44} radius="var(--radius-md)" />
          ))}
        </div>
      )}
      {shelves && (
        <ul className={styles.list}>
          {shelves.length === 0 && <li className={styles.empty}>No shelves yet. Create your first one below.</li>}
          {shelves.map((shelf) => (
            <li key={shelf.id_playlist}>
              <button
                type="button"
                className={`${styles.shelf} ${shelf.contains ? styles.selected : ''}`}
                onClick={() => toggle(shelf)}
                disabled={pending === shelf.id_playlist}
                aria-pressed={shelf.contains}
              >
                <span className={styles.box}>{shelf.contains && <Icon name="check" size={14} />}</span>
                <span className={styles.name}>{shelf.name}</span>
                <span className={`${styles.count} tabular`}>
                  {shelf.count}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
      <form className={styles.create} onSubmit={create} noValidate>
        <Field
          label="New shelf"
          placeholder="e.g. Summer reads"
          value={newName}
          maxLength={100}
          onChange={(e) => {
            setNewName(e.target.value);
            setNameError('');
          }}
          error={nameError}
        />
        <Button type="submit" icon="plus" loading={creating} className={styles.createButton}>
          Create
        </Button>
      </form>
    </>
  );
}
