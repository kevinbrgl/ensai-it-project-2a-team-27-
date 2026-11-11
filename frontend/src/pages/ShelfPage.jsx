import { useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import * as playlistsApi from '../api/playlists';
import { BookRow } from '../components/books/BookRow';
import { ShelfNameDialog } from '../components/books/ShelfNameDialog';
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

export function ShelfPage() {
  const { shelfId } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const { data: shelf, error, loading, reload, setData } = useAsync(() => playlistsApi.getPlaylist(shelfId), [shelfId]);
  useDocumentTitle(shelf?.name || 'Shelf');
  const [sort, setSort] = useState('title');
  const [renaming, setRenaming] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [toRemove, setToRemove] = useState(null);

  const books = useMemo(() => sortBooks(shelf?.books || [], sort), [shelf, sort]);

  if (error) {
    return error.status === 404 ? (
      <EmptyState icon="shelves" title="This shelf doesn’t exist" action={<Button to="/shelves">Back to shelves</Button>}>
        It may have been deleted.
      </EmptyState>
    ) : (
      <ErrorState error={error} onRetry={reload} />
    );
  }
  if (loading && !shelf) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
        <Skeleton width="40%" height={36} />
        <Skeleton height={72} />
        <Skeleton height={72} />
      </div>
    );
  }

  const rename = async (name) => {
    try {
      const updated = await playlistsApi.renamePlaylist(shelf.id_playlist, name);
      setData((s) => ({ ...s, name: updated.name }));
      toast.success('Shelf renamed.');
      return null;
    } catch (err) {
      return err.status === 409 ? 'You already have a shelf with this name.' : err.message;
    }
  };

  const remove = async () => {
    try {
      await playlistsApi.deletePlaylist(shelf.id_playlist);
      toast.success(`Shelf “${shelf.name}” deleted.`);
      navigate('/shelves', { replace: true });
    } catch (err) {
      toast.error(err.message);
    }
  };

  const removeBook = async () => {
    const book = toRemove;
    try {
      await playlistsApi.removeBookFromPlaylist(shelf.id_playlist, book.id_book);
      setData((s) => ({ ...s, books: s.books.filter((b) => b.id_book !== book.id_book) }));
      toast.success(`“${book.title}” removed from the shelf.`);
    } catch (err) {
      toast.error(err.message);
    }
  };

  return (
    <>
      <PageHeader
        title={shelf.name}
        description={plural(shelf.books.length, 'book')}
        actions={
          <>
            <Button icon="edit" onClick={() => setRenaming(true)}>
              Rename
            </Button>
            <Button icon="trash" variant="ghost" onClick={() => setConfirmDelete(true)}>
              Delete shelf
            </Button>
          </>
        }
      />

      {books.length === 0 ? (
        <EmptyState icon="shelves" title="This shelf is empty" action={<Button variant="primary" to="/library">Go to my library</Button>}>
          Open any book and choose “Save to shelf” to add it here.
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

      <ShelfNameDialog
        open={renaming}
        title="Rename shelf"
        initialName={shelf.name}
        submitLabel="Save name"
        onSubmit={rename}
        onClose={() => setRenaming(false)}
      />
      <ConfirmDialog
        open={confirmDelete}
        title={`Delete “${shelf.name}”?`}
        message="The shelf will be deleted. The books stay in the catalog and in your library."
        confirmLabel="Delete shelf"
        onConfirm={remove}
        onClose={() => setConfirmDelete(false)}
      />
      <ConfirmDialog
        open={Boolean(toRemove)}
        title="Remove from this shelf?"
        message={toRemove ? `“${toRemove.title}” will be taken off “${shelf.name}”.` : ''}
        confirmLabel="Remove"
        onConfirm={removeBook}
        onClose={() => setToRemove(null)}
      />
    </>
  );
}
