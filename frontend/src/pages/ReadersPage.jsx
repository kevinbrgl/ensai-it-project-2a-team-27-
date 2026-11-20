import { useMemo, useState } from 'react';
import { getFollowers, searchUsers } from '../api/users';
import { FollowButton } from '../components/users/FollowButton';
import { UserRow } from '../components/users/UserRow';
import { Icon } from '../components/ui/Icon';
import { PageHeader } from '../components/ui/PageHeader';
import { SegmentedControl } from '../components/ui/SegmentedControl';
import { Skeleton } from '../components/ui/Skeleton';
import { EmptyState, ErrorState } from '../components/ui/States';
import { useAuth } from '../context/AuthContext';
import { useAsync } from '../hooks/useAsync';
import { useDebouncedValue } from '../hooks/useDebouncedValue';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { useFollowing } from '../hooks/useFollowing';
import { useSearchParamState } from '../hooks/useSearchParamState';
import styles from './ReadersPage.module.css';

export function ReadersPage() {
  useDocumentTitle('Readers');
  const { user } = useAuth();
  const social = useFollowing(true);
  const [query, setQuery] = useState('');
  const term = useDebouncedValue(query.trim(), 300);
  const [tab, setTab] = useSearchParamState('list', 'following');

  const results = useAsync(() => searchUsers(term, 20), [term], { skip: !term });
  const followers = useAsync(() => getFollowers(user.id_user, true), [user.id_user]);

  const found = useMemo(() => (results.data || []).filter((u) => u.id_user !== user.id_user), [results.data, user.id_user]);
  const list = tab === 'followers' ? followers : { data: social.following, loading: social.loading, error: social.error, reload: social.reload };

  return (
    <>
      <PageHeader title="Readers" description="Follow people whose taste you trust, and see what they’re reading." />

      <div className={styles.search}>
        <Icon name="search" size={20} className={styles.searchIcon} />
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Find a reader by username…"
          aria-label="Search readers by username"
          maxLength={30}
        />
        {query && (
          <button type="button" className={styles.clear} onClick={() => setQuery('')} aria-label="Clear search">
            <Icon name="x" size={18} />
          </button>
        )}
      </div>

      {term ? (
        <section className={styles.panel} aria-label={`Readers matching ${term}`}>
          <p className={styles.panelLabel}>Readers matching <em>“{term}”</em></p>
          {results.error && <ErrorState error={results.error} onRetry={results.reload} />}
          {results.loading && <ListSkeleton />}
          {!results.loading && results.data && found.length === 0 && (
            <EmptyState icon="users" title={`No reader called “${term}”`}>
              Usernames are matched partially, so try fewer letters.
            </EmptyState>
          )}
          {!results.loading && found.length > 0 && (
            <ul className={styles.list}>
              {found.map((u) => (
                <UserRow key={u.id_user} user={u} showWheel action={<FollowButton user={u} social={social} />} />
              ))}
            </ul>
          )}
        </section>
      ) : (
        <section className={styles.panel} aria-label="Your reading circle">
          <SegmentedControl
            label="Your reading circle"
            value={tab}
            onChange={setTab}
            options={[
              { value: 'following', label: 'Following', count: social.loading ? undefined : social.following.length },
              { value: 'followers', label: 'Followers', count: followers.data?.length },
            ]}
          />
          {list.error && <ErrorState error={list.error} onRetry={list.reload} />}
          {!list.error && list.loading && !list.data?.length && <ListSkeleton />}
          {!list.error && !list.loading && list.data?.length === 0 && (
            <EmptyState icon="users" title={tab === 'followers' ? 'Nobody follows you yet' : 'Your circle is empty'}>
              {tab === 'followers'
                ? 'Readers who follow you will be listed here.'
                : 'Search for a reader above and follow them to see what they read.'}
            </EmptyState>
          )}
          {list.data?.length > 0 && (
            <ul className={styles.list}>
              {list.data.map((u) => (
                <UserRow key={u.id_user} user={u} showWheel action={<FollowButton user={u} social={social} />} />
              ))}
            </ul>
          )}
        </section>
      )}
    </>
  );
}

function ListSkeleton() {
  return (
    <div className={styles.list} aria-busy="true" aria-label="Loading readers">
      {[0, 1, 2, 3].map((i) => (
        <div key={i} className={styles.skeletonRow}>
          <Skeleton width={44} height={44} radius="50%" />
          <Skeleton width="40%" height={14} />
        </div>
      ))}
    </div>
  );
}
