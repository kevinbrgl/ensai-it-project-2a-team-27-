import { useMemo, useState } from 'react';
import { preconnect } from 'react-dom';
import { Link } from 'react-router-dom';
import { searchBooks } from '../api/books';
import { getRecommendations } from '../api/recommendations';
import { getMyStats } from '../api/users';
import { BookCover } from '../components/books/BookCover';
import { BookGrid, BookGridSkeleton } from '../components/books/BookGrid';
import { LibraryControl } from '../components/books/LibraryControl';
import { RecommendationMeta } from '../components/books/RecommendationMeta';
import { Button } from '../components/ui/Button';
import { Icon } from '../components/ui/Icon';
import { PageHeader } from '../components/ui/PageHeader';
import { SegmentedControl } from '../components/ui/SegmentedControl';
import { Skeleton } from '../components/ui/Skeleton';
import { EmptyState, ErrorState } from '../components/ui/States';
import { useAsync } from '../hooks/useAsync';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { useSearchParamState } from '../hooks/useSearchParamState';
import { firstAuthor, formatRating, largeCover, yearOf } from '../utils/format';
import page from './Page.module.css';
import styles from './DiscoverPage.module.css';

const PAGE_STEP = 12;
const MAX_RESULTS = 50; // backend limit for /books/search
// Open Library rejects searches made only of these words (e.g. "the"),
// so they are blocked before reaching the backend.
const STOPWORDS = new Set([
  'a', 'an', 'the', 'of', 'and', 'or', 'to', 'in', 'on', 'at', 'is', 'by',
  'le', 'la', 'l', 'un', 'de', 'du', 'd', 'et',
]);
const TOO_GENERIC = 'Search is too generic, add more words.';

/** True when every word of the query is a stopword, e.g. "the" or "the a". */
function isTooGeneric(query) {
  const words = query.toLowerCase().split(/[\s'’]+/).filter(Boolean);
  return words.length > 0 && words.every((word) => STOPWORDS.has(word));
}

const STARTER_GENRES = ['Fantasy', 'Science fiction', 'Mystery', 'Romance', 'History', 'Poetry', 'Philosophy', 'Biography'];
const SORTS = [
  { value: 'rating', label: 'Best rated' },
  { value: 'new', label: 'Newest' },
  { value: 'title', label: 'A–Z' },
];

export function DiscoverPage() {
  preconnect('https://covers.openlibrary.org');
  const [q, setQ] = useSearchParamState('q');
  useDocumentTitle(q ? `“${q}”` : 'Discover');
  return (
    <>
      <PageHeader
        title={<>Find your next <em>book.</em></>}
        description="Search millions of titles from Open Library, or let your reading history suggest something."
      />
      <SearchForm key={`form-${q}`} q={q} onSearch={setQ} />

      {q ? <SearchResults key={`results-${q}`} q={q} onClear={() => setQ('')} /> : <RecommendationBrowser />}
    </>
  );
}

function SearchForm({ q, onSearch }) {
  const [draft, setDraft] = useState(q);
  const tooGeneric = isTooGeneric(draft.trim());
  return (
    <form
      className={styles.search}
      role="search"
      onSubmit={(e) => {
        e.preventDefault();
        if (!tooGeneric) onSearch(draft.trim());
      }}
    >
      <Icon name="search" size={22} className={styles.searchIcon} />
      <input
        type="search"
        value={draft}
        onChange={(e) => {
          setDraft(e.target.value);
          if (!e.target.value) onSearch('');
        }}
        placeholder="A title or an author…"
        aria-label="Search books by title or author"
        aria-invalid={tooGeneric || undefined}
        aria-describedby="search-hint"
        autoFocus={!q}
      />
      <button type="submit" className={styles.searchSubmit} disabled={!draft.trim() || tooGeneric}>
        Search <Icon name="arrowRight" size={18} />
      </button>
      <p id="search-hint" className={tooGeneric ? `${styles.searchHint} ${styles.searchHintError}` : styles.searchHint} aria-live="polite">
        {tooGeneric ? TOO_GENERIC : 'Try “Le Petit Prince”, “Toni Morrison” or “Earthsea”.'}
      </p>
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
        <h2>Results for <em>“{q}”</em></h2>
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
  const stats = useAsync(getMyStats, []);
  const recs = useAsync(() => getRecommendations({ genre, sort, limit: 24 }), [genre, sort]);

  // The reader's own genres first, then a few common starting points.
  const genres = useMemo(() => {
    const mine = new Set((stats.data?.genres || []).map((g) => g.category?.toLowerCase()).filter(Boolean));
    const names = [...(stats.data?.genres || []).map((g) => g.category).filter(Boolean), ...STARTER_GENRES, ...(genre ? [genre] : [])];
    const seen = new Set();
    return names
      .filter((name) => {
        const key = name.toLowerCase();
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
      })
      .slice(0, 12)
      .map((name) => ({ name, mine: mine.has(name.toLowerCase()) }));
  }, [stats.data, genre]);

  const [lead, ...rest] = recs.data || [];

  return (
    <div className={styles.browser}>
      <GenreIndex genres={genres} value={genre} onChange={setGenre} />

      <section className={styles.picks} aria-labelledby="picks-title">
        <div className={styles.picksHeader}>
          <h2 id="picks-title">{genre ? <>In <em>{genre}</em></> : <>From your <em>reading.</em></>}</h2>
          <SegmentedControl label="Sort recommendations" options={SORTS} value={sort} onChange={setSort} size="sm" />
        </div>

        {recs.error && <ErrorState error={recs.error} onRetry={recs.reload} title="Recommendations didn’t load" />}
        {!recs.error && recs.loading && (
          <>
            <Skeleton height={230} />
            <div className={styles.restGrid}><BookGridSkeleton count={8} /></div>
          </>
        )}
        {!recs.loading && recs.data?.length === 0 && (
          <EmptyState icon="compass" title={genre ? `Nothing found in “${genre}”` : 'No suggestions yet'}>
            {genre
              ? 'Try a broader genre, such as “Fiction” or “History”.'
              : 'Add books to your library and rate them; suggestions follow your favorite genres.'}
          </EmptyState>
        )}
        {!recs.loading && lead && (
          <>
            <LeadPick rec={lead} />
            {rest.length > 0 && (
              <div className={styles.restGrid}>
                <BookGrid
                  books={rest.map((r) => ({ ...r.book, _rec: r }))}
                  renderMeta={(book) => <RecommendationMeta rec={book._rec} />}
                />
              </div>
            )}
          </>
        )}
      </section>
    </div>
  );
}

/** The genre list down the side, with a free-text genre at the end. */
function GenreIndex({ genres, value, onChange }) {
  const [custom, setCustom] = useState('');
  const choose = (name) => onChange(value === name ? '' : name);
  return (
    <nav className={styles.index} aria-label="Browse by genre">
      <p className={styles.indexLabel}>Index of genres</p>
      <ul>
        <li>
          <button type="button" aria-pressed={!value} onClick={() => onChange('')}>
            From my reading
          </button>
        </li>
        {genres.map((g) => (
          <li key={g.name}>
            <button type="button" aria-pressed={value === g.name} onClick={() => choose(g.name)}>
              {g.name}
              {g.mine && <span className={styles.mine} title="A genre you read">yours</span>}
            </button>
          </li>
        ))}
      </ul>
      <form
        className={styles.customGenre}
        onSubmit={(e) => {
          e.preventDefault();
          if (custom.trim()) {
            onChange(custom.trim().slice(0, 100));
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
        <button type="submit" disabled={!custom.trim()} aria-label="Show this genre">
          <Icon name="arrowRight" size={16} />
        </button>
      </form>
    </nav>
  );
}

/** The best recommendation, set as a spread with room for its blurb. */
function LeadPick({ rec }) {
  const { book } = rec;
  const year = yearOf(book.publish_date);
  return (
    <article className={styles.lead}>
      <Link to={`/books/${book.id_book}`} className={styles.leadCover} tabIndex={-1} aria-hidden="true">
        <BookCover book={book} src={largeCover(book.cover_image)} decorative />
      </Link>
      <div className={styles.leadText}>
        <p className={styles.leadKicker}>
          <span>Top pick</span>
          {rec.score != null && (
            <span className="tabular"><Icon name="star" size={12} filled /> {formatRating(rec.score)}</span>
          )}
        </p>
        <h3 className={styles.leadTitle}><Link to={`/books/${book.id_book}`}>{book.title}</Link></h3>
        <p className={styles.leadByline}>
          {firstAuthor(book.author)}
          {year && <span className="tabular"> · {year}</span>}
          {book.category && <span> · {book.category}</span>}
        </p>
        {book.description && <p className={styles.leadBlurb}>{book.description}</p>}
        <p className={styles.leadReason}>{rec.reason}</p>
        <div className={styles.leadActions}>
          <LibraryControl book={book} size="sm" />
        </div>
      </div>
    </article>
  );
}
