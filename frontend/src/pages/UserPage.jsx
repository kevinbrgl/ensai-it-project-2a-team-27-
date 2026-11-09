import { Link, useParams } from 'react-router-dom';
import { getBook } from '../api/books';
import { listUserReviews } from '../api/reviews';
import * as usersApi from '../api/users';
import { BookGrid, BookGridSkeleton } from '../components/books/BookGrid';
import { ReviewItem } from '../components/reviews/ReviewItem';
import { StatsPanels } from '../components/stats/StatsPanels';
import { FollowButton } from '../components/users/FollowButton';
import { UserRow } from '../components/users/UserRow';
import { Avatar } from '../components/ui/Avatar';
import { Button } from '../components/ui/Button';
import { SegmentedControl } from '../components/ui/SegmentedControl';
import { Skeleton } from '../components/ui/Skeleton';
import { EmptyState, ErrorState } from '../components/ui/States';
import { useAuth } from '../context/AuthContext';
import { useAsync } from '../hooks/useAsync';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { useFollowing } from '../hooks/useFollowing';
import { useSearchParamState } from '../hooks/useSearchParamState';
import { STATUS_LABELS } from '../utils/format';
import page from './Page.module.css';
import styles from './UserPage.module.css';

const LIBRARY_FILTERS = [
  { value: 'all', label: 'All' },
  { value: 'READING', label: STATUS_LABELS.READING },
  { value: 'WANT_TO_READ', label: STATUS_LABELS.WANT_TO_READ },
  { value: 'COMPLETED', label: STATUS_LABELS.COMPLETED },
];

export function UserPage() {
  const { userId } = useParams();
  const id = Number(userId);
  const { user: me } = useAuth();
  const social = useFollowing();
  const isMe = id === me.id_user;
  const [tab, setTab] = useSearchParamState('tab', 'library');

  const followers = useAsync(() => usersApi.getFollowers(id), [id]);
  const following = useAsync(() => usersApi.getFollowing(id), [id]);

  // No "get user by id" route exists: the name comes from users seen elsewhere.
  const profile = isMe ? me : usersApi.getKnownUser(id);
  const name = profile?.username || `Reader #${id}`;
  useDocumentTitle(name);

  if (followers.error?.status === 404 || (!Number.isInteger(id) || id < 1)) {
    return (
      <EmptyState icon="users" title="This reader doesn’t exist" action={<Button to="/readers">Find readers</Button>}>
        The account may have been deleted.
      </EmptyState>
    );
  }

  const tabs = [
    { value: 'library', label: 'Library' },
    { value: 'reviews', label: 'Reviews' },
    { value: 'shelves', label: 'Shelves' },
    { value: 'stats', label: 'Stats' },
    { value: 'followers', label: 'Followers', count: followers.data?.length },
    { value: 'following', label: 'Following', count: following.data?.length },
  ];

  return (
    <>
      <header className={styles.header}>
        <Avatar user={profile || { id_user: id, username: name }} size={72} />
        <div className={styles.identity}>
          <h1>{name}</h1>
          {profile?.bio && <p className={styles.bio}>{profile.bio}</p>}
        </div>
        <div className={styles.headerAction}>
          {isMe ? (
            <Button icon="settings" to="/settings">
              Edit profile
            </Button>
          ) : (
            <FollowButton user={profile || { id_user: id, username: name }} social={social} size="md" />
          )}
        </div>
      </header>

      <div className={styles.tabs}>
        <SegmentedControl label="Profile sections" options={tabs} value={tab} onChange={setTab} />
      </div>

      {tab === 'library' && <UserLibrary id={id} />}
      {tab === 'reviews' && <UserReviews id={id} isMe={isMe} />}
      {tab === 'shelves' && <UserShelves id={id} isMe={isMe} />}
      {tab === 'stats' && <UserStats id={id} isMe={isMe} name={name} social={social} profile={profile} />}
      {tab === 'followers' && <PeopleList state={followers} social={social} meId={me.id_user} empty={`Nobody follows ${isMe ? 'you' : name} yet.`} />}
      {tab === 'following' && <PeopleList state={following} social={social} meId={me.id_user} empty={`${isMe ? 'You don’t' : `${name} doesn’t`} follow anyone yet.`} />}
    </>
  );
}

function UserLibrary({ id }) {
  const [status, setStatus] = useSearchParamState('status', 'all');
  const { data, error, loading, reload } = useAsync(
    () => usersApi.getUserLibrary(id, status === 'all' ? undefined : status),
    [id, status],
  );
  return (
    <>
      <div className={page.toolbar}>
        <SegmentedControl label="Reading status" size="sm" options={LIBRARY_FILTERS} value={status} onChange={setStatus} />
      </div>
      {error && <ErrorState error={error} onRetry={reload} />}
      {!error && loading && <BookGridSkeleton count={6} />}
      {!loading && data?.length === 0 && <EmptyState icon="library" title="No books here" />}
      {!loading && data?.length > 0 && <BookGrid books={data} />}
    </>
  );
}

async function loadReviewsWithBooks(id) {
  const reviews = await listUserReviews(id);
  const books = await Promise.all(reviews.map((r) => getBook(r.id_book).catch(() => null)));
  return reviews.map((review, i) => ({ review, book: books[i] }));
}

function UserReviews({ id, isMe }) {
  const { data, error, loading, reload } = useAsync(() => loadReviewsWithBooks(id), [id]);
  if (error) return <ErrorState error={error} onRetry={reload} />;
  if (loading) return <ListSkeleton />;
  if (!data.length) return <EmptyState icon="star" title="No reviews yet" />;
  return (
    <div className={styles.reviews}>
      {data.map(({ review, book }) => (
        <ReviewItem
          key={review.id_review}
          review={review}
          isMine={isMe}
          heading={
            <Link to={`/books/${review.id_book}`} className={styles.reviewBook}>
              {book?.title || 'Book'}
              {book?.author && <span className={styles.reviewAuthor}> · {book.author.split(',')[0]}</span>}
            </Link>
          }
        />
      ))}
    </div>
  );
}

function UserShelves({ id, isMe }) {
  const { data, error, loading, reload } = useAsync(() => usersApi.getUserPlaylists(id), [id]);
  if (error) return <ErrorState error={error} onRetry={reload} />;
  if (loading) return <ListSkeleton />;
  if (!data.length) return <EmptyState icon="shelves" title="No shelves yet" />;
  return (
    <ul className={`${page.list} ${styles.shelves}`}>
      {data.map((shelf) => (
        <li key={shelf.id_playlist}>
          {isMe ? (
            <Link to={`/shelves/${shelf.id_playlist}`} className={styles.shelfLink}>
              {shelf.name}
            </Link>
          ) : (
            <span className={styles.shelfName}>{shelf.name}</span>
          )}
        </li>
      ))}
    </ul>
  );
}

function UserStats({ id, isMe, name, social, profile }) {
  const followsThem = social.isFollowing(id);
  const { data, error, loading, reload } = useAsync(
    () => (isMe ? usersApi.getMyStats() : usersApi.getUserStats(id)),
    [id, isMe, followsThem],
  );
  if (error?.status === 403) {
    return (
      <EmptyState
        icon="chart"
        title={`Follow ${name} to see their stats`}
        action={<FollowButton user={profile || { id_user: id, username: name }} social={social} size="md" />}
      >
        Reading statistics are only shared with followers.
      </EmptyState>
    );
  }
  if (error) return <ErrorState error={error} onRetry={reload} />;
  if (loading) return <Skeleton height={200} radius="var(--radius-lg)" />;
  return <StatsPanels stats={data} />;
}

function PeopleList({ state, social, meId, empty }) {
  if (state.error) return <ErrorState error={state.error} onRetry={state.reload} />;
  if (state.loading) return <ListSkeleton />;
  if (!state.data.length) return <p className={page.muted}>{empty}</p>;
  return (
    <ul className={`${page.list} ${styles.people}`}>
      {state.data.map((u) => (
        <UserRow key={u.id_user} user={u} action={u.id_user !== meId && <FollowButton user={u} social={social} />} />
      ))}
    </ul>
  );
}

function ListSkeleton() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
      {[0, 1, 2].map((i) => (
        <Skeleton key={i} height={56} />
      ))}
    </div>
  );
}
