import { useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { getRecommendations } from '../api/recommendations';
import { getMyQuests } from '../api/users';
import { BookCover } from '../components/books/BookCover';
import { BookGrid, BookGridSkeleton } from '../components/books/BookGrid';
import { RecommendationMeta } from '../components/books/RecommendationMeta';
import { QuestCard } from '../components/stats/QuestCard';
import { Button } from '../components/ui/Button';
import { Icon } from '../components/ui/Icon';
import { Skeleton } from '../components/ui/Skeleton';
import { EmptyState, ErrorState } from '../components/ui/States';
import { useAuth } from '../context/AuthContext';
import { useLibrary } from '../context/LibraryContext';
import { useAsync } from '../hooks/useAsync';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { firstAuthor, greeting, largeCover, plural, yearOf } from '../utils/format';
import page from './Page.module.css';
import styles from './HomePage.module.css';

export function HomePage() {
  useDocumentTitle('Home');
  const { user } = useAuth();
  const library = useLibrary();

  const reading = useMemo(() => library.books.filter((b) => b.state === 'READING'), [library.books]);
  const counts = useMemo(() => {
    const c = { READING: 0, WANT_TO_READ: 0, COMPLETED: 0 };
    for (const b of library.books) c[b.state] += 1;
    return c;
  }, [library.books]);

  return (
    <>
      <header className={styles.header}>
        <h1>
          {greeting()}, {user.username}
        </h1>
        {!library.loading && (
          <p className={page.muted}>
            {counts.READING
              ? `You have ${plural(counts.READING, 'book')} in progress.`
              : 'Nothing in progress right now — pick your next read below.'}
          </p>
        )}
      </header>

      <div className={styles.top}>
        <CurrentlyReading library={library} reading={reading} />
        <aside className={styles.side}>
          <Snapshot counts={counts} loading={library.loading} />
          <NextQuests />
        </aside>
      </div>

      <Recommendations />
    </>
  );
}

function CurrentlyReading({ library, reading }) {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [busy, setBusy] = useState(false);

  if (library.loading) {
    return (
      <section className={styles.hero} aria-busy="true">
        <Skeleton width={160} height={240} radius="var(--radius-cover)" />
        <div className={styles.heroText}>
          <Skeleton width="30%" height={12} />
          <Skeleton width="70%" height={32} />
          <Skeleton width="40%" height={14} />
        </div>
      </section>
    );
  }
  if (library.error) return <ErrorState error={library.error} onRetry={library.refresh} />;

  if (!reading.length) {
    const next = library.books.find((b) => b.state === 'WANT_TO_READ');
    return (
      <section className={`${styles.hero} ${styles.heroEmpty}`}>
        <div className={styles.heroText}>
          <span className={styles.eyebrow}>Currently reading</span>
          <h2 className={styles.heroTitle}>Your nightstand is empty</h2>
          {next ? (
            <>
              <p className={page.muted}>“{next.title}” is first on your want-to-read list.</p>
              <div className={styles.heroActions}>
                <Button
                  variant="primary"
                  icon="book"
                  loading={busy}
                  onClick={async () => {
                    setBusy(true);
                    await library.setStatus(next.id_book, 'READING');
                    setBusy(false);
                  }}
                >
                  Start reading it
                </Button>
                <Button to="/discover">Find something else</Button>
              </div>
            </>
          ) : (
            <form
              className={styles.heroSearch}
              onSubmit={(e) => {
                e.preventDefault();
                if (query.trim()) navigate(`/discover?q=${encodeURIComponent(query.trim())}`);
              }}
            >
              <input
                type="search"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search by title or author"
                aria-label="Search books"
              />
              <Button type="submit" variant="primary" icon="search">
                Search
              </Button>
            </form>
          )}
        </div>
      </section>
    );
  }

  const [main, ...others] = reading;
  const year = yearOf(main.publish_date);
  return (
    <section className={styles.hero}>
      <Link to={`/books/${main.id_book}`} className={styles.heroCover}>
        <BookCover book={main} src={largeCover(main.cover_image)} />
      </Link>
      <div className={styles.heroText}>
        <span className={styles.eyebrow}>Currently reading</span>
        <Link to={`/books/${main.id_book}`}>
          <h2 className={styles.heroTitle}>{main.title}</h2>
        </Link>
        <p className={page.muted}>
          {firstAuthor(main.author)}
          {year && <span className="tabular"> · {year}</span>}
        </p>
        <div className={styles.heroActions}>
          <Button
            variant="primary"
            icon="check"
            loading={busy}
            onClick={async () => {
              setBusy(true);
              await library.setStatus(main.id_book, 'COMPLETED');
              setBusy(false);
            }}
          >
            Mark as finished
          </Button>
          <Button to={`/books/${main.id_book}`}>Open book</Button>
        </div>
        {others.length > 0 && (
          <div className={styles.alsoReading}>
            <span className={styles.alsoLabel}>Also reading</span>
            <ul>
              {others.slice(0, 4).map((book) => (
                <li key={book.id_book}>
                  <Link to={`/books/${book.id_book}`} className={styles.alsoItem}>
                    <BookCover book={book} size="sm" decorative />
                    <span>{book.title}</span>
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </section>
  );
}

function Snapshot({ counts, loading }) {
  const items = [
    { label: 'Finished', value: counts.COMPLETED, to: '/library?status=COMPLETED' },
    { label: 'Reading', value: counts.READING, to: '/library?status=READING' },
    { label: 'Want to read', value: counts.WANT_TO_READ, to: '/library?status=WANT_TO_READ' },
  ];
  return (
    <div className={`${page.card} ${styles.snapshot}`}>
      {items.map((item) => (
        <Link key={item.label} to={item.to} className={styles.stat}>
          <span className={`${styles.statValue} tabular`}>{loading ? '–' : item.value}</span>
          <span className={styles.statLabel}>{item.label}</span>
        </Link>
      ))}
    </div>
  );
}

function NextQuests() {
  const { data, error, loading, reload } = useAsync(() => getMyQuests('active'), []);
  if (error) return <ErrorState error={error} onRetry={reload} title="Quests didn’t load" />;
  const quests = (data || []).slice().sort((a, b) => b.progress_percentage - a.progress_percentage).slice(0, 2);
  return (
    <div className={styles.quests}>
      <div className={page.sectionHeader}>
        <h3>Next milestones</h3>
        <Link to="/progress" className={page.sectionLink}>
          All quests <Icon name="arrowRight" size={14} />
        </Link>
      </div>
      {loading ? (
        <Skeleton height={130} radius="var(--radius-lg)" />
      ) : quests.length ? (
        quests.map((quest) => <QuestCard key={quest.id_quest} quest={quest} />)
      ) : (
        <p className={page.muted}>Every quest is complete. Impressive.</p>
      )}
    </div>
  );
}

function Recommendations() {
  const { data, error, loading, reload } = useAsync(() => getRecommendations({ limit: 10 }), []);
  return (
    <section className={page.section}>
      <div className={page.sectionHeader}>
        <h2>Picked for you</h2>
        <Link to="/discover" className={page.sectionLink}>
          Browse by genre <Icon name="arrowRight" size={14} />
        </Link>
      </div>
      {loading && <BookGridSkeleton count={6} variant="row" />}
      {error && <ErrorState error={error} onRetry={reload} />}
      {data && data.length === 0 && (
        <EmptyState icon="compass" title="No recommendations yet" action={<Button to="/discover">Search for books</Button>}>
          Add a few books to your library or rate what you’ve read, and suggestions will appear here.
        </EmptyState>
      )}
      {data && data.length > 0 && (
        <BookGrid
          variant="row"
          books={data.map((r) => ({ ...r.book, _rec: r }))}
          renderMeta={(book) => <RecommendationMeta rec={book._rec} />}
        />
      )}
    </section>
  );
}
