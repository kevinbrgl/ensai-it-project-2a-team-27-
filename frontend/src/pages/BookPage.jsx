import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { moderateReview } from '../api/admin';
import { getBookDetails, listBooks } from '../api/books';
import * as reviewsApi from '../api/reviews';
import { getFollowers, getFollowing } from '../api/users';
import { AddToPlaylistDialog } from '../components/books/AddToPlaylistDialog';
import { BookCover } from '../components/books/BookCover';
import { BookRow } from '../components/books/BookRow';
import { LibraryControl } from '../components/books/LibraryControl';
import { ReviewForm } from '../components/reviews/ReviewForm';
import { ReviewItem } from '../components/reviews/ReviewItem';
import { Button } from '../components/ui/Button';
import { ConfirmDialog } from '../components/ui/ConfirmDialog';
import { Icon } from '../components/ui/Icon';
import { Menu } from '../components/ui/Menu';
import { Skeleton } from '../components/ui/Skeleton';
import { Stars } from '../components/ui/StarRating';
import { EmptyState, ErrorState } from '../components/ui/States';
import { useAuth } from '../context/AuthContext';
import { useLibrary } from '../context/LibraryContext';
import { useToast } from '../context/ToastContext';
import { useAsync } from '../hooks/useAsync';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { firstAuthor, formatRating, largeCover, plural, yearOf } from '../utils/format';
import page from './Page.module.css';
import styles from './BookPage.module.css';

export function BookPage() {
  const { bookId } = useParams();
  // GET /books/{id} returns the book plus its editions (BookDetails).
  const { data: book, error, loading, reload } = useAsync(() => getBookDetails(bookId), [bookId]);
  useDocumentTitle(book?.title || 'Book');

  if (error) {
    return error.status === 404 || error.status === 422 ? (
      <EmptyState icon="book" title="Book not found" action={<Button to="/discover">Search for books</Button>}>
        It may have been removed, or the link is incomplete.
      </EmptyState>
    ) : (
      <ErrorState error={error} onRetry={reload} />
    );
  }
  if (loading || !book) return <BookSkeleton />;

  return (
    <>
      <BookHeader book={book} />
      <Editions editions={book.editions || []} />
      <Reviews book={book} />
      {book.author?.trim() && <MoreByAuthor book={book} />}
    </>
  );
}

function BookHeader({ book }) {
  const library = useLibrary();
  const entry = library.get(book.id_book);
  const [playlistOpen, setPlaylistOpen] = useState(false);
  const year = yearOf(book.publish_date);

  return (
    <section className={styles.header}>
      <div className={styles.cover}>
        <BookCover book={book} src={largeCover(book.cover_image)} size="lg" />
      </div>
      <div className={styles.info}>
        {book.category && (
          <Link to={`/discover?genre=${encodeURIComponent(book.category)}`} className={styles.category}>
            {book.category}
          </Link>
        )}
        <h1 className={styles.title}>{book.title}</h1>
        <p className={styles.byline}>
          {book.author ? (
            book.author.split(',').map((name, index) => (
              <span key={`${name}-${index}`}>
                {index > 0 && ', '}
                <Link to={`/discover?q=${encodeURIComponent(name.trim())}`} className={styles.author}>
                  {name.trim()}
                </Link>
              </span>
            ))
          ) : (
            'Unknown author'
          )}
          {year && <span className="tabular"> · first published {year}</span>}
          {book.num_pages > 0 && <span className="tabular"> · {plural(book.num_pages, 'page')}</span>}
        </p>

        <div className={styles.actions}>
          <LibraryControl book={book} />
          {entry && (
            <>
              <Button
                icon="heart"
                variant="ghost"
                className={entry.is_liked ? styles.liked : ''}
                aria-pressed={entry.is_liked}
                onClick={() => library.toggleLike(book.id_book)}
              >
                {entry.is_liked ? 'Liked' : 'Like'}
              </Button>
              <Button
                icon="bookmark"
                variant="ghost"
                className={entry.is_favorite ? styles.favorite : ''}
                aria-pressed={entry.is_favorite}
                onClick={() => library.toggleFavorite(book.id_book)}
              >
                {entry.is_favorite ? 'Favorite' : 'Add to favorites'}
              </Button>
            </>
          )}
          <Button icon="playlists" variant="ghost" onClick={() => setPlaylistOpen(true)}>
            Save to playlist
          </Button>
        </div>

        {book.description ? (
          <p className={styles.description}>{book.description}</p>
        ) : (
          book.id_book_api && (
            <a
              className={styles.external}
              href={`https://openlibrary.org${book.id_book_api}`}
              target="_blank"
              rel="noreferrer"
            >
              Read the synopsis on Open Library <Icon name="arrowRight" size={14} />
            </a>
          )
        )}
      </div>
      <AddToPlaylistDialog book={book} open={playlistOpen} onClose={() => setPlaylistOpen(false)} />
    </section>
  );
}

/** Editions of the book, read live from Open Library by the backend. */
function Editions({ editions }) {
  const [expanded, setExpanded] = useState(false);
  const visible = expanded ? editions : editions.slice(0, 3);
  return (
    <section className={`${page.section} ${styles.editions}`}>
      <div className={styles.editionsAside}>
        <h2>Editions</h2>
        {editions.length > 0 && <p className={`${styles.editionCount} tabular`}>{plural(editions.length, 'edition')}</p>}
      </div>
      <div className={styles.editionsMain}>
        {editions.length > 0 ? (
          <>
            <ul id="edition-list" className={`${page.list} ${styles.editionList}`}>
              {visible.map((edition, index) => (
                <EditionItem key={`${edition.isbn || edition.title || 'edition'}-${index}`} edition={edition} />
              ))}
            </ul>
            {editions.length > 3 && (
              <Button size="sm" variant="ghost" aria-expanded={expanded} aria-controls="edition-list" onClick={() => setExpanded(!expanded)}>
                {expanded ? 'Show fewer editions' : `Show all ${editions.length} editions`}
              </Button>
            )}
          </>
        ) : (
          <p className={`${page.muted} ${styles.noEditions}`}>No edition is available from Open Library for this book right now.</p>
        )}
      </div>
    </section>
  );
}

function EditionItem({ edition }) {
  const details = [
    edition.publishers?.length ? edition.publishers.join(', ') : null,
    edition.publish_date,
    edition.num_pages ? plural(edition.num_pages, 'page') : null,
    edition.language ? edition.language.toUpperCase() : null,
    edition.isbn ? `ISBN ${edition.isbn}` : null,
  ].filter(Boolean);

  return (
    <li className={styles.edition}>
      <span className={styles.editionTitle}>{edition.title || 'Untitled edition'}</span>
      {details.length > 0 && <span className={`${styles.editionMeta} tabular`}>{details.join(' · ')}</span>}
    </li>
  );
}

function MoreByAuthor({ book }) {
  const author = firstAuthor(book.author);
  const { data, error, loading, reload } = useAsync(() => listBooks({ author }), [author]);
  const books = (data || []).filter((other) => other.id_book !== book.id_book
    && other.author?.split(',').some((name) => name.trim().toLocaleLowerCase() === author.toLocaleLowerCase()));

  return (
    <section className={`${page.section} ${styles.related}`}>
      <div className={styles.relatedHeader}>
        <h2>More by {author}</h2>
        <Link to={`/discover?q=${encodeURIComponent(author)}`} className={page.sectionLink}>
          Search Open Library <Icon name="arrowRight" size={14} />
        </Link>
      </div>
      {loading ? (
        <div aria-busy="true" aria-label="Loading books by this author"><Skeleton height={72} /></div>
      ) : error ? (
        <ErrorState title="Couldn’t load this author’s books" error={error} onRetry={reload} />
      ) : books.length ? (
        <ul className={page.list}>{books.slice(0, 4).map((other) => <BookRow key={other.id_book} book={other} />)}</ul>
      ) : (
        <p className={page.muted}>This is the only title by {author} saved by readers here so far.</p>
      )}
    </section>
  );
}

function Reviews({ book }) {
  const { user } = useAuth();
  const toast = useToast();
  const library = useLibrary();
  const { data, error, loading, reload, setData } = useAsync(() => reviewsApi.getBookReviews(book.id_book), [book.id_book]);
  const [editing, setEditing] = useState(false);
  const [toDelete, setToDelete] = useState(null);
  const [toModerate, setToModerate] = useState(null);
  const [, setNamesReady] = useState(false);

  // Reviews only carry user ids; loading the people around me lets the
  // review list show their usernames instead of "Reader #12".
  useEffect(() => {
    Promise.allSettled([getFollowing(user.id_user), getFollowers(user.id_user)]).then(() => setNamesReady(true));
  }, [user.id_user]);

  const reviews = data?.reviews || [];
  const mine = reviews.find((r) => r.id_user === user.id_user);
  const others = reviews.filter((r) => r.id_user !== user.id_user);
  // The backend only accepts a new review on a book of the user's library.
  const inLibrary = Boolean(library.get(book.id_book));

  const refreshSummary = async () => setData(await reviewsApi.getBookReviews(book.id_book));

  const create = async (values) => {
    try {
      await reviewsApi.createReview(book.id_book, values);
      await refreshSummary();
      toast.success('Your review is published.');
      return true;
    } catch (err) {
      toast.error(err.message);
      return false;
    }
  };

  const update = async (values) => {
    try {
      await reviewsApi.updateReview(mine.id_review, values);
      await refreshSummary();
      setEditing(false);
      toast.success('Review updated.');
      return true;
    } catch (err) {
      toast.error(err.message);
      return false;
    }
  };

  const remove = async () => {
    try {
      await reviewsApi.deleteReview(toDelete.id_review);
      await refreshSummary();
      toast.success('Review deleted.');
    } catch (err) {
      toast.error(err.message);
    }
  };

  const moderate = async () => {
    try {
      await moderateReview(toModerate.id_review);
      await refreshSummary();
      toast.success('Review removed.');
    } catch (err) {
      toast.error(err.message);
    }
  };

  return (
    <section className={`${page.section} ${styles.reviews}`}>
      <div className={styles.reviewsAside}>
        <h2>Reader reviews</h2>
        {loading && !data ? (
          <Skeleton width={120} height={48} />
        ) : (
          data && (
            <div className={styles.average}>
              <span className={`${styles.averageValue} tabular`}>{formatRating(data.average_rating)}</span>
              <div>
                <Stars value={data.average_rating || 0} size={16} />
                <p className={`${styles.reviewCount} tabular`}>{plural(data.review_count, 'review')}</p>
              </div>
            </div>
          )
        )}
      </div>

      <div className={styles.reviewsMain}>
        {error && <ErrorState error={error} onRetry={reload} />}
        {loading && !data && (
          <div className={styles.reviewSkeleton}>
            <Skeleton width="40%" height={16} />
            <Skeleton height={14} />
            <Skeleton width="80%" height={14} />
          </div>
        )}
        {data && (
          <>
            <div className={`${page.card} ${styles.myReview}`}>
              {!mine && inLibrary && (
                <>
                  <h3 className={page.cardTitle}>Rate this book</h3>
                  <ReviewForm onSubmit={create} />
                </>
              )}
              {!mine && !inLibrary && (
                <>
                  <h3 className={page.cardTitle}>Rate this book</h3>
                  <p className={`${page.muted} ${styles.reviewLocked}`}>
                    You can only review a book from your library. Add this book to your library to rate it.
                  </p>
                </>
              )}
              {mine && editing && (
                <>
                  <h3 className={page.cardTitle}>Edit your review</h3>
                  <ReviewForm initial={mine} onSubmit={update} onCancel={() => setEditing(false)} submitLabel="Save changes" />
                </>
              )}
              {mine && !editing && (
                <ReviewItem
                  review={mine}
                  isMine
                  actions={
                    <Menu
                      align="end"
                      trigger={({ toggle }) => <Button variant="ghost" size="sm" icon="edit" onClick={toggle} aria-label="Review options" />}
                      items={[
                        { label: 'Edit review', icon: 'edit', onSelect: () => setEditing(true) },
                        { label: 'Delete review', icon: 'trash', tone: 'danger', onSelect: () => setToDelete(mine) },
                      ]}
                    />
                  }
                />
              )}
            </div>

            {others.length > 0 ? (
              <div>
                {others.map((review) => (
                  <ReviewItem
                    key={review.id_review}
                    review={review}
                    actions={
                      user.is_admin && (
                        <Menu
                          align="end"
                          trigger={({ toggle }) => <Button variant="ghost" size="sm" icon="alert" onClick={toggle} aria-label="Moderate review" />}
                          items={[{ label: 'Remove review', icon: 'trash', tone: 'danger', onSelect: () => setToModerate(review) }]}
                        />
                      )
                    }
                  />
                ))}
              </div>
            ) : (
              <p className={`${page.muted} ${styles.noOthers}`}>No other reader has reviewed this book yet.</p>
            )}
          </>
        )}
      </div>

      <ConfirmDialog
        open={Boolean(toDelete)}
        title="Delete your review?"
        message="Your rating and comment will be removed for good."
        confirmLabel="Delete review"
        onConfirm={remove}
        onClose={() => setToDelete(null)}
      />
      <ConfirmDialog
        open={Boolean(toModerate)}
        title="Remove this review?"
        message="The review will be deleted for every reader. This can’t be undone."
        confirmLabel="Remove review"
        onConfirm={moderate}
        onClose={() => setToModerate(null)}
      />
    </section>
  );
}

function BookSkeleton() {
  return (
    <section className={styles.header} aria-busy="true">
      <div className={styles.cover}>
        <Skeleton style={{ aspectRatio: '2 / 3', height: 'auto' }} radius="var(--radius-cover)" />
      </div>
      <div className={styles.info}>
        <Skeleton width={100} height={14} />
        <Skeleton width="70%" height={40} />
        <Skeleton width="40%" height={16} />
        <Skeleton width={260} height={40} radius="var(--radius-md)" style={{ marginTop: 24 }} />
      </div>
    </section>
  );
}
