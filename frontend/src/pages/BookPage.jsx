import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { getBook } from '../api/books';
import * as reviewsApi from '../api/reviews';
import { getFollowers, getFollowing } from '../api/users';
import { AddToShelfDialog } from '../components/books/AddToShelfDialog';
import { BookCover } from '../components/books/BookCover';
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
import { formatRating, largeCover, plural, yearOf } from '../utils/format';
import page from './Page.module.css';
import styles from './BookPage.module.css';

export function BookPage() {
  const { bookId } = useParams();
  const { data: book, error, loading, reload } = useAsync(() => getBook(bookId), [bookId]);
  useDocumentTitle(book?.title || 'Book');

  if (error) {
    return error.status === 404 || error.status === 422 ? (
      <EmptyState icon="book" title="This book isn’t in the catalog" action={<Button to="/discover">Search for books</Button>}>
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
      <Reviews book={book} />
    </>
  );
}

function BookHeader({ book }) {
  const library = useLibrary();
  const entry = library.get(book.id_book);
  const [shelfOpen, setShelfOpen] = useState(false);
  const year = yearOf(book.publish_date);

  return (
    <section className={styles.header}>
      <div className={styles.cover}>
        <BookCover book={book} src={largeCover(book.cover_image)} size="lg" />
      </div>
      <div className={styles.info}>
        {book.category && (
          <Link to={`/catalog?genre=${encodeURIComponent(book.category)}`} className={styles.category}>
            {book.category}
          </Link>
        )}
        <h1 className={styles.title}>{book.title}</h1>
        <p className={styles.byline}>
          {book.author ? (
            <Link to={`/catalog?author=${encodeURIComponent(book.author.split(',')[0].trim())}`} className={styles.author}>
              {book.author}
            </Link>
          ) : (
            'Unknown author'
          )}
          {year && <span className="tabular"> · first published {year}</span>}
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
          <Button icon="shelves" variant="ghost" onClick={() => setShelfOpen(true)}>
            Save to shelf
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
      <AddToShelfDialog book={book} open={shelfOpen} onClose={() => setShelfOpen(false)} />
    </section>
  );
}

function Reviews({ book }) {
  const { user } = useAuth();
  const toast = useToast();
  const { data, error, loading, reload, setData } = useAsync(() => reviewsApi.getBookReviews(book.id_book), [book.id_book]);
  const [editing, setEditing] = useState(false);
  const [toDelete, setToDelete] = useState(null);
  const [, setNamesReady] = useState(false);

  // Reviews only carry user ids; loading the people around me lets the
  // review list show their usernames instead of "Reader #12".
  useEffect(() => {
    Promise.allSettled([getFollowing(user.id_user), getFollowers(user.id_user)]).then(() => setNamesReady(true));
  }, [user.id_user]);

  const reviews = data?.reviews || [];
  const mine = reviews.find((r) => r.id_user === user.id_user);
  const others = reviews.filter((r) => r.id_user !== user.id_user);

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
              {!mine && (
                <>
                  <h3 className={page.cardTitle}>Rate this book</h3>
                  <ReviewForm onSubmit={create} />
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
                  <ReviewItem key={review.id_review} review={review} />
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
