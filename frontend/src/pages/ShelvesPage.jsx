import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import * as playlistsApi from '../api/playlists';
import { BookCover } from '../components/books/BookCover';
import { ShelfNameDialog } from '../components/books/ShelfNameDialog';
import { Button } from '../components/ui/Button';
import { PageHeader } from '../components/ui/PageHeader';
import { Skeleton } from '../components/ui/Skeleton';
import { EmptyState, ErrorState } from '../components/ui/States';
import { useToast } from '../context/ToastContext';
import { useAsync } from '../hooks/useAsync';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { plural } from '../utils/format';
import styles from './ShelvesPage.module.css';

// Shelves list only names; details are loaded in parallel to show real covers.
async function loadShelves() {
  const list = await playlistsApi.listPlaylists();
  return Promise.all(list.map((p) => playlistsApi.getPlaylist(p.id_playlist)));
}

export function ShelvesPage() {
  useDocumentTitle('Shelves');
  const toast = useToast();
  const navigate = useNavigate();
  const { data, error, loading, reload } = useAsync(loadShelves, []);
  const [creating, setCreating] = useState(false);

  const create = async (name) => {
    try {
      const shelf = await playlistsApi.createPlaylist(name);
      toast.success(`Shelf “${shelf.name}” created.`);
      navigate(`/shelves/${shelf.id_playlist}`);
      return null;
    } catch (err) {
      return err.status === 409 ? 'You already have a shelf with this name.' : err.message;
    }
  };

  return (
    <>
      <PageHeader
        title="Shelves"
        description="Group books your way: a reading list for the holidays, a course syllabus, favourites to lend."
        actions={
          <Button variant="primary" icon="plus" onClick={() => setCreating(true)}>
            New shelf
          </Button>
        }
      />

      {error && <ErrorState error={error} onRetry={reload} />}
      {loading && !data && (
        <div className={styles.grid}>
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} height={232} radius="var(--radius-lg)" />
          ))}
        </div>
      )}
      {data && data.length === 0 && (
        <EmptyState
          icon="shelves"
          title="No shelves yet"
          action={
            <Button variant="primary" icon="plus" onClick={() => setCreating(true)}>
              Create your first shelf
            </Button>
          }
        >
          You can also save a book to a shelf from its page.
        </EmptyState>
      )}
      {data && data.length > 0 && (
        <div className={styles.grid}>
          {data.map((shelf) => (
            <Link key={shelf.id_playlist} to={`/shelves/${shelf.id_playlist}`} className={styles.shelf}>
              <div className={styles.covers}>
                {shelf.books.slice(0, 4).map((book) => (
                  <BookCover key={book.id_book} book={book} decorative />
                ))}
                {shelf.books.length === 0 && <span className={styles.emptyShelf}>Empty shelf</span>}
              </div>
              <div className={styles.shelfText}>
                <h2 className={styles.shelfName}>{shelf.name}</h2>
                <span className={`${styles.shelfCount} tabular`}>{plural(shelf.books.length, 'book')}</span>
              </div>
            </Link>
          ))}
        </div>
      )}

      <ShelfNameDialog open={creating} title="New shelf" submitLabel="Create shelf" onSubmit={create} onClose={() => setCreating(false)} />
    </>
  );
}
