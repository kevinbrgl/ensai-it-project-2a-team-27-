import { useState } from 'react';
import { Link } from 'react-router-dom';
import { getRecommendations } from '../api/recommendations';
import { getMyQuests } from '../api/users';
import readingRoom from '../assets/reading-room.webp';
import { BookCover } from '../components/books/BookCover';
import { BookGrid, BookGridSkeleton } from '../components/books/BookGrid';
import { RecommendationMeta } from '../components/books/RecommendationMeta';
import { Button } from '../components/ui/Button';
import { Icon } from '../components/ui/Icon';
import { Skeleton } from '../components/ui/Skeleton';
import { EmptyState, ErrorState } from '../components/ui/States';
import { useAuth } from '../context/AuthContext';
import { useLibrary } from '../context/LibraryContext';
import { useAsync } from '../hooks/useAsync';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { firstAuthor, greeting, largeCover, plural } from '../utils/format';
import page from './Page.module.css';
import styles from './HomePage.module.css';

export function HomePage() {
  useDocumentTitle('Reading room');
  const { user } = useAuth();
  const library = useLibrary();
  const today = new Date();
  const reading = library.books.filter((book) => book.state === 'READING');
  const next = library.books.find((book) => book.state === 'WANT_TO_READ');

  return (
    <>
      <header className={styles.header}>
        <div>
          <p className={styles.greeting}>{greeting(today)}, {user.username}.</p>
          <h1>The reading <em>room.</em></h1>
        </div>
        <span className={styles.date}>{today.toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long' })}</span>
      </header>

      <div className={styles.spread}>
        {library.error ? <ErrorState error={library.error} onRetry={library.refresh} title="Your library didn’t load" /> :
          library.loading ? <Skeleton height={310} /> :
            <Nightstand reading={reading} next={next} onStatusChange={library.setStatus} />}
        <aside className={styles.margin}>
          <section aria-labelledby="record-title">
            <div className={styles.asideHeader}>
              <h2 id="record-title">Reading record</h2>
              <Link to="/progress" aria-label="View reading progress"><Icon name="arrowRight" size={19} /></Link>
            </div>
            <div className={styles.snapshot}>
              {[
                ['COMPLETED', 'Finished'], ['READING', 'Reading'], ['WANT_TO_READ', 'To read'],
              ].map(([state, label]) => (
                <Link key={state} to={`/library?status=${state}`} className={styles.stat}>
                  <span className="tabular">{library.loading || library.error ? '–' : library.books.filter((book) => book.state === state).length}</span>
                  {label}
                </Link>
              ))}
            </div>
          </section>
          <NextQuest readingKey={library.books.map((b) => `${b.id_book}:${b.state}`).join(',')} />
        </aside>
      </div>
      <Recommendations />
    </>
  );
}

function Nightstand({ reading, next, onStatusChange }) {
  const [busy, setBusy] = useState(false);
  const current = reading[0];
  const book = current || next;
  const changeStatus = async () => {
    setBusy(true);
    try {
      await onStatusChange(book.id_book, current ? 'COMPLETED' : 'READING');
    } finally {
      setBusy(false);
    }
  };
  return (
    <section className={styles.feature}>
      <div className={styles.featureText}>
        <span className={styles.eyebrow}><Icon name="book" size={16} /> {current ? 'Currently reading' : next ? 'Next on your list' : 'Your nightstand'}</span>
        <h2 className={styles.featureTitle}>{book ? <Link to={`/books/${book.id_book}`}>{book.title}</Link> : <>Find your<br /><em>next read.</em></>}</h2>
        <p className={styles.byline}>{book ? firstAuthor(book.author) : 'Choose a book to start your reading journal.'}</p>
        <div className={styles.actions}>
          {book ? (
            <>
              <Button className={styles.featureAction} loading={busy} icon={current ? 'check' : 'book'} onClick={changeStatus}>
                {current ? 'Mark as finished' : 'Start reading'}
              </Button>
              <Link className={styles.textLink} to={`/books/${book.id_book}`}>Open book <Icon name="arrowRight" size={15} /></Link>
            </>
          ) : (
            <Button className={styles.featureAction} to="/discover" iconRight="arrowRight">Find a book</Button>
          )}
        </div>
        {reading.length > 1 && <Link className={styles.moreReading} to="/library?status=READING">{plural(reading.length - 1, 'more book')} in progress</Link>}
      </div>
      <div className={`${styles.scene} ${book ? styles.withCover : ''}`}>
        <img className={styles.room} src={readingRoom} alt="" />
        {book && (
          <Link to={`/books/${book.id_book}`} className={styles.jacket} aria-label={`Open ${book.title}`}>
            <BookCover book={book} src={largeCover(book.cover_image)} decorative />
          </Link>
        )}
      </div>
    </section>
  );
}

function NextQuest({ readingKey }) {
  const { data, error, loading, reload } = useAsync(() => getMyQuests('active'), [readingKey]);
  const quest = data?.reduce((best, q) => !best || q.progress_percentage > best.progress_percentage ? q : best, null);
  return (
    <section className={styles.milestone}>
      <div className={styles.asideHeader}>
        <h2>Next milestone</h2>
        <Link to="/progress?view=quests" aria-label="View all quests"><Icon name="arrowRight" size={19} /></Link>
      </div>
      {loading ? <Skeleton height={48} /> : error ? <ErrorState error={error} onRetry={reload} title="Quests didn’t load" /> :
        quest ? (
          <div>
            <p className={styles.questName}>{quest.title} <span>{quest.reward_xp} XP</span></p>
            <p className={styles.questDescription}>{quest.description}</p>
            <div className={styles.questProgress}>
              <progress value={Math.min(quest.current, quest.target)} max={quest.target} aria-label={quest.title} />
              <span>{Math.min(quest.current, quest.target)} / {quest.target}</span>
            </div>
          </div>
        ) : <p className={page.muted}>No active quests.</p>}
    </section>
  );
}

function Recommendations() {
  const { data, error, loading, reload } = useAsync(() => getRecommendations({ limit: 10 }), []);
  return (
    <section className={page.section}>
      <div className={page.sectionHeader}>
        <h2>Picked for <em>you.</em></h2>
        <Link to="/discover" className={page.sectionLink}>Browse by genre <Icon name="arrowRight" size={15} /></Link>
      </div>
      {loading ? <BookGridSkeleton count={6} variant="row" /> :
        error ? <ErrorState error={error} onRetry={reload} title="Recommendations didn’t load" /> :
        data.length === 0 ? (
          <EmptyState icon="compass" title="No recommendations yet" action={<Button to="/discover">Find books</Button>}>
            Add books to your library or rate what you’ve read to get suggestions.
          </EmptyState>
        ) : (
          <BookGrid variant="row" books={data.map((r) => ({ ...r.book, _rec: r }))}
            renderMeta={(book) => <RecommendationMeta rec={book._rec} />} />
        )}
    </section>
  );
}
