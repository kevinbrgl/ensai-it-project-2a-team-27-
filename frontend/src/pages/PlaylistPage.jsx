import { useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import * as playlistsApi from '../api/playlists';
import { BookRow } from '../components/books/BookRow';
import { PlaylistNameDialog } from '../components/books/PlaylistNameDialog';
import { Button } from '../components/ui/Button';
import { ConfirmDialog } from '../components/ui/ConfirmDialog';
import { Field } from '../components/ui/Field';
import { PageHeader } from '../components/ui/PageHeader';
import { Skeleton } from '../components/ui/Skeleton';
import { EmptyState, ErrorState } from '../components/ui/States';
import { useToast } from '../context/ToastContext';
import { useAsync } from '../hooks/useAsync';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { BOOK_SORTS, sortBooks } from '../utils/books';
import { plural } from '../utils/format';
import page from './Page.module.css';

export function PlaylistPage() {
  const { playlistId } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const { data: playlist, error, loading, reload, setData } = useAsync(() => playlistsApi.getPlaylist(playlistId), [playlistId]);
  useDocumentTitle(playlist?.name || 'Playlist');
  const [sort, setSort] = useState('title');
  const [renaming, setRenaming] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [toRemove, setToRemove] = useState(null);

  const books = useMemo(() => sortBooks(playlist?.books || [], sort), [playlist, sort]);

  if (error) {
    return [404, 422].includes(error.status) ? (
      <EmptyState icon="playlists" title="This playlist doesn’t exist" action={<Button to="/playlists">Back to playlists</Button>}>
        It may have been deleted.
      </EmptyState>
    ) : (
      <ErrorState error={error} onRetry={reload} />
    );
  }
  if (loading && !playlist) {
    return (
      <div aria-busy="true" aria-label="Loading playlist" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
        <Skeleton width="40%" height={36} />
        <Skeleton height={72} />
        <Skeleton height={72} />
      </div>
    );
  }

  const rename = async (name) => {
    try {
      const updated = await playlistsApi.renamePlaylist(playlist.id_playlist, name);
      setData((s) => ({ ...s, name: updated.name }));
      toast.success('Playlist renamed.');
      return null;
    } catch (err) {
      return err.status === 409 ? 'You already have a playlist with this name.' : err.message;
    }
  };

  const remove = async () => {
    try {
      await playlistsApi.deletePlaylist(playlist.id_playlist);
      toast.success(`Playlist “${playlist.name}” deleted.`);
      navigate('/playlists', { replace: true });
    } catch (err) {
      toast.error(err.message);
    }
  };

  const removeBook = async () => {
    const book = toRemove;
    try {
      await playlistsApi.removeBookFromPlaylist(playlist.id_playlist, book.id_book);
      setData((s) => ({ ...s, books: s.books.filter((b) => b.id_book !== book.id_book) }));
      toast.success(`“${book.title}” removed from the playlist.`);
    } catch (err) {
      toast.error(err.message);
    }
  };

  return (
    <>
      <PageHeader
        title={playlist.name}
        description={plural(playlist.books.length, 'book')}
        actions={
          <>
            <Button icon="edit" onClick={() => setRenaming(true)}>
              Rename
            </Button>
            <Button icon="trash" variant="ghost" onClick={() => setConfirmDelete(true)}>
              Delete playlist
            </Button>
          </>
        }
      />

      {books.length === 0 ? (
        <EmptyState icon="playlists" title="This playlist is empty" action={<Button variant="primary" to="/discover">Find books</Button>}>
          Open any book and choose “Save to playlist” to add it here.
        </EmptyState>
      ) : (
        <>
          <div className={page.toolbar} style={{ justifyContent: 'flex-end' }}>
            <Field as="select" aria-label="Sort books" value={sort} onChange={(e) => setSort(e.target.value)} className={page.sortSelect}>
              {BOOK_SORTS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </Field>
          </div>
          <ul className={page.list}>
            {books.map((book) => (
              <BookRow
                key={book.id_book}
                book={book}
                actions={
                  <Button size="sm" variant="ghost" icon="x" onClick={() => setToRemove(book)}>
                    Remove
                  </Button>
                }
              />
            ))}
          </ul>
        </>
      )}

      <PlaylistNameDialog
        open={renaming}
        title="Rename playlist"
        initialName={playlist.name}
        submitLabel="Save name"
        onSubmit={rename}
        onClose={() => setRenaming(false)}
      />
      <ConfirmDialog
        open={confirmDelete}
        title={`Delete “${playlist.name}”?`}
        message="This permanently deletes the playlist."
        confirmLabel="Delete playlist"
        onConfirm={remove}
        onClose={() => setConfirmDelete(false)}
      />
      <ConfirmDialog
        open={Boolean(toRemove)}
        title="Remove from this playlist?"
        message={toRemove ? `“${toRemove.title}” will be taken off “${playlist.name}”.` : ''}
        confirmLabel="Remove"
        onConfirm={removeBook}
        onClose={() => setToRemove(null)}
      />
    </>
  );
}
