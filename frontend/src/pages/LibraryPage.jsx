import { useMemo, useState } from 'react';
import { listMyFavorites, READING_STATES } from '../api/library';
import { BookRow } from '../components/books/BookRow';
import { Button } from '../components/ui/Button';
import { ChipGroup } from '../components/ui/ChipGroup';
import { ConfirmDialog } from '../components/ui/ConfirmDialog';
import { Field } from '../components/ui/Field';
import { PageHeader } from '../components/ui/PageHeader';
import { Pagination } from '../components/ui/Pagination';
import { SegmentedControl } from '../components/ui/SegmentedControl';
import { Skeleton } from '../components/ui/Skeleton';
import { EmptyState, ErrorState } from '../components/ui/States';
import { useLibrary } from '../context/LibraryContext';
import { useAsync } from '../hooks/useAsync';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { usePagination } from '../hooks/usePagination';
import { useSearchParamState, useUpdateSearchParams } from '../hooks/useSearchParamState';
import { BOOK_SORTS, sortBooks, topCategories } from '../utils/books';
import { STATUS_LABELS } from '../utils/format';
import page from './Page.module.css';
import styles from './LibraryPage.module.css';

const PAGE_SIZE = 20;
const EMPTY_COPY = {
  all: ['Your library is empty', 'Search for a book you’re reading or want to read, and add it here.'],
  READING: ['Nothing in progress', 'Books you mark as “Reading” show up here.'],
  WANT_TO_READ: ['No books waiting', 'Save books for later by adding them as “Want to read”.'],
  COMPLETED: ['No finished books yet', 'Mark a book as finished to count it in your progress.'],
  favorites: ['No favorites yet', 'Open a book in your library and choose “Add to favorites”.'],
};

export function LibraryPage() {
  useDocumentTitle('My library');
  const library = useLibrary();
  const [tab] = useSearchParamState('status', 'all');
  const updateParams = useUpdateSearchParams();
  const [genre, setGenre] = useSearchParamState('genre');
  const [sort, setSort] = useSearchParamState('sort', 'title');
  const [toRemove, setToRemove] = useState(null);

  // The favorites tab reads GET /library/favorites, refreshed whenever the
  // set of favorites changes in this session.
  const favoriteKey = library.books
    .filter((b) => b.is_favorite)
    .map((b) => b.id_book)
    .sort()
    .join(',');
  const favorites = useAsync(listMyFavorites, [favoriteKey], { skip: tab !== 'favorites' });

  const tabBooks = useMemo(() => {
    if (tab === 'favorites') return (favorites.data || []).map((b) => library.get(b.id_book) || b);
    if (tab === 'all') return library.books;
    return library.books.filter((b) => b.state === tab);
  }, [tab, library, favorites.data]);

  const genres = useMemo(() => topCategories(tabBooks, 10), [tabBooks]);
  const visible = useMemo(() => {
    const filtered = genre ? tabBooks.filter((b) => b.category === genre) : tabBooks;
    return sortBooks(filtered, sort);
  }, [tabBooks, genre, sort]);
  const pagination = usePagination(visible, PAGE_SIZE, `${tab}|${genre}|${sort}`);

  const counts = useMemo(() => {
    const c = { all: library.books.length, favorites: 0, READING: 0, WANT_TO_READ: 0, COMPLETED: 0 };
    for (const b of library.books) {
      c[b.state] += 1;
      if (b.is_favorite) c.favorites += 1;
    }
    return c;
  }, [library.books]);

  const tabs = [
    { value: 'all', label: 'All', count: counts.all },
    { value: 'READING', label: 'Reading', count: counts.READING },
    { value: 'WANT_TO_READ', label: 'Want to read', count: counts.WANT_TO_READ },
    { value: 'COMPLETED', label: 'Finished', count: counts.COMPLETED },
    { value: 'favorites', label: 'Favorites', count: counts.favorites },
  ];

  const loading = library.loading || (tab === 'favorites' && favorites.loading && !favorites.data);
  const error = library.error || (tab === 'favorites' && favorites.error);
  const [emptyTitle, emptyText] = EMPTY_COPY[tab] || EMPTY_COPY.all;

  return (
    <>
      <PageHeader
        title="My library"
        actions={
          <Button variant="primary" icon="plus" to="/discover">
            Add a book
          </Button>
        }
      />

      <div className={page.filters}>
        <SegmentedControl
          label="Reading status"
          options={tabs}
          value={tab}
          onChange={(value) => updateParams({ status: value === 'all' ? '' : value, genre: '' })}
        />
        <div className={page.toolbar}>
          <div className={page.toolbarGroup}>
            {genres.length > 1 && <ChipGroup label="Genre" options={genres} value={genre} onChange={setGenre} allLabel="All genres" />}
          </div>
          <Field as="select" aria-label="Sort books" value={sort} onChange={(e) => setSort(e.target.value)} className={page.sortSelect}>
            {BOOK_SORTS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </Field>
        </div>
      </div>

      {error && <ErrorState error={error} onRetry={tab === 'favorites' ? favorites.reload : library.refresh} />}
      {!error && loading && (
        <div className={styles.skeleton}>
          {Array.from({ length: 5 }, (_, i) => (
            <div key={i} className={styles.skeletonRow}>
              <Skeleton width={48} height={72} radius="var(--radius-cover)" />
              <div className={styles.skeletonText}>
                <Skeleton width="45%" height={16} />
                <Skeleton width="30%" height={12} />
              </div>
            </div>
          ))}
        </div>
      )}
      {!error && !loading && visible.length === 0 && (
        <EmptyState icon="library" title={emptyTitle} action={<Button to="/discover">Find books</Button>}>
          {emptyText}
        </EmptyState>
      )}
      {!error && !loading && visible.length > 0 && (
        <>
          <ul className={page.list}>
            {pagination.pageItems.map((book) => (
              <LibraryRow key={book.id_book} book={book} library={library} onRemove={() => setToRemove(book)} />
            ))}
          </ul>
          <Pagination {...pagination} pageSize={PAGE_SIZE} onChange={pagination.setPage} />
        </>
      )}

      <ConfirmDialog
        open={Boolean(toRemove)}
        title="Remove from your library?"
        message={toRemove ? `“${toRemove.title}” will leave your library, with its like and favorite.` : ''}
        confirmLabel="Remove"
        onConfirm={() => library.remove(toRemove.id_book)}
        onClose={() => setToRemove(null)}
      />
    </>
  );
}

function LibraryRow({ book, library, onRemove }) {
  const [busy, setBusy] = useState(false);
  return (
    <BookRow
      book={book}
      actions={
        <>
          <Button
            size="sm"
            variant="ghost"
            icon="heart"
            className={book.is_liked ? styles.liked : ''}
            aria-label={book.is_liked ? 'Unlike' : 'Like'}
            aria-pressed={book.is_liked}
            title={book.is_liked ? 'Unlike' : 'Like'}
            onClick={() => library.toggleLike(book.id_book)}
          />
          <Button
            size="sm"
            variant="ghost"
            icon="bookmark"
            className={book.is_favorite ? styles.favorite : ''}
            aria-label={book.is_favorite ? 'Remove from favorites' : 'Add to favorites'}
            aria-pressed={book.is_favorite}
            title={book.is_favorite ? 'Remove from favorites' : 'Add to favorites'}
            onClick={() => library.toggleFavorite(book.id_book)}
          />
          <select
            className={styles.status}
            value={book.state}
            disabled={busy}
            aria-label={`Reading status of ${book.title}`}
            onChange={async (e) => {
              setBusy(true);
              await library.setStatus(book.id_book, e.target.value);
              setBusy(false);
            }}
          >
            {READING_STATES.map((state) => (
              <option key={state} value={state}>
                {STATUS_LABELS[state]}
              </option>
            ))}
          </select>
          <Button size="sm" variant="ghost" icon="trash" aria-label={`Remove ${book.title}`} title="Remove from library" onClick={onRemove} />
        </>
      }
    />
  );
}
