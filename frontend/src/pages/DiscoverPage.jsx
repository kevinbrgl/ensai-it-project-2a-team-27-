import { useMemo, useState } from 'react';
import { searchBooks } from '../api/books';
import { getRecommendations } from '../api/recommendations';
import { getMyStats } from '../api/users';
import { BookGrid, BookGridSkeleton } from '../components/books/BookGrid';
import { RecommendationMeta } from '../components/books/RecommendationMeta';
import { Button } from '../components/ui/Button';
import { ChipGroup } from '../components/ui/ChipGroup';
import { Icon } from '../components/ui/Icon';
import { PageHeader } from '../components/ui/PageHeader';
import { SegmentedControl } from '../components/ui/SegmentedControl';
import { EmptyState, ErrorState } from '../components/ui/States';
import { useAsync } from '../hooks/useAsync';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { useSearchParamState } from '../hooks/useSearchParamState';
import page from './Page.module.css';
import styles from './DiscoverPage.module.css';

const PAGE_STEP = 12;
const MAX_RESULTS = 50; // backend limit for /books/search
const STARTER_GENRES = ['Fantasy', 'Science fiction', 'Mystery', 'Romance', 'History', 'Poetry', 'Philosophy', 'Biography'];
const SORTS = [
  { value: 'rating', label: 'Best rated' },
  { value: 'new', label: 'Newest' },
  { value: 'title', label: 'A–Z' },
];

export function DiscoverPage() {
  const [q, setQ] = useSearchParamState('q');
  useDocumentTitle(q ? `“${q}”` : 'Discover');
  return (
    <>
      <PageHeader
        title="Find your next book"
        description="Search millions of titles from Open Library, or let your reading history suggest something."
      />
      <SearchForm key={`form-${q}`} q={q} onSearch={setQ} />

      {q ? <SearchResults key={`results-${q}`} q={q} onClear={() => setQ('')} /> : <RecommendationBrowser />}
    </>
  );
}

function SearchForm({ q, onSearch }) {
  const [draft, setDraft] = useState(q);
  return (
    <form
      className={styles.search}
      role="search"
      onSubmit={(e) => {
        e.preventDefault();
        onSearch(draft.trim());
      }}
    >
      <Icon name="search" size={20} className={styles.searchIcon} />
      <input
        type="search"
        value={draft}
        onChange={(e) => {
          setDraft(e.target.value);
          if (!e.target.value) onSearch('');
        }}
        placeholder="Title or author, e.g. “Le Petit Prince” or “Toni Morrison”"
        aria-label="Search books by title or author"
        autoFocus={!q}
      />
      <Button type="submit" variant="primary" disabled={!draft.trim()}>
        Search
      </Button>
    </form>
  );
}

function SearchResults({ q, onClear }) {
  const [limit, setLimit] = useState(PAGE_STEP);
  const { data, error, loading, reload } = useAsync(() => searchBooks(q, limit), [q, limit]);
  const books = data || [];
  const canLoadMore = data && books.length >= limit && limit < MAX_RESULTS;

  return (
    <section className={page.section}>
      <div className={page.sectionHeader}>
        <h2>Results for “{q}”</h2>
        <Button variant="ghost" size="sm" icon="x" onClick={onClear}>
          Clear search
        </Button>
      </div>
      {error && <ErrorState error={error} onRetry={reload} title="Search failed" />}
      {!error && !data && loading && <BookGridSkeleton count={12} />}
      {data && books.length === 0 && (
        <EmptyState icon="search" title="No books match this search">
          Check the spelling, or try the author’s name instead of the title.
        </EmptyState>
      )}
      {books.length > 0 && (
        <>
          <BookGrid books={books} />
          {canLoadMore && (
            <div className={styles.more}>
              <Button loading={loading} onClick={() => setLimit((l) => Math.min(l + PAGE_STEP, MAX_RESULTS))}>
                Show more results
              </Button>
            </div>
          )}
        </>
      )}
    </section>
  );
}

function RecommendationBrowser() {
  const [genre, setGenre] = useSearchParamState('genre');
  const [sort, setSort] = useSearchParamState('sort', 'rating');
  const [custom, setCustom] = useState('');
  const stats = useAsync(getMyStats, []);
  const recs = useAsync(() => getRecommendations({ genre, sort, limit: 24 }), [genre, sort]);

  // The reader's own genres first, then a few common starting points.
  const genres = useMemo(() => {
    const mine = (stats.data?.genres || []).map((g) => g.category).filter(Boolean);
    const all = [...mine, ...STARTER_GENRES, ...(genre ? [genre] : [])];
    const seen = new Set();
    return all
      .filter((name) => {
        const key = name.toLowerCase();
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
      })
      .slice(0, 12)
      .map((name) => ({ name }));
  }, [stats.data, genre]);

  return (
    <section className={page.section}>
      <div className={page.sectionHeader}>
        <h2>{genre ? `Recommended in ${genre}` : 'Recommended for you'}</h2>
        <SegmentedControl label="Sort recommendations" options={SORTS} value={sort} onChange={setSort} size="sm" />
      </div>
      <div className={page.filters}>
        <ChipGroup label="Genre" options={genres} value={genre} onChange={setGenre} allLabel="From my reading" />
        <form
          className={styles.customGenre}
          onSubmit={(e) => {
            e.preventDefault();
            if (custom.trim()) {
              setGenre(custom.trim().slice(0, 100));
              setCustom('');
            }
          }}
        >
          <input
            value={custom}
            onChange={(e) => setCustom(e.target.value)}
            placeholder="Another genre…"
            aria-label="Another genre"
            maxLength={100}
          />
          <Button type="submit" size="sm" disabled={!custom.trim()}>
            Apply
          </Button>
        </form>
      </div>

      {recs.error && <ErrorState error={recs.error} onRetry={recs.reload} />}
      {!recs.error && recs.loading && <BookGridSkeleton count={12} />}
      {!recs.loading && recs.data?.length === 0 && (
        <EmptyState icon="compass" title={genre ? `Nothing found in “${genre}”` : 'No suggestions yet'}>
          {genre
            ? 'Try a broader genre, such as “Fiction” or “History”.'
            : 'Add books to your library and rate them; suggestions follow your favourite genres.'}
        </EmptyState>
      )}
      {!recs.loading && recs.data?.length > 0 && (
        <BookGrid
          books={recs.data.map((r) => ({ ...r.book, _rec: r }))}
          renderMeta={(book) => <RecommendationMeta rec={book._rec} />}
        />
      )}
    </section>
  );
}
