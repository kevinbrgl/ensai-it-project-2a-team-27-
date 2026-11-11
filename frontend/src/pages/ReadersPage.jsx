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
import page from './Page.module.css';
import styles from './ReadersPage.module.css';

export function ReadersPage() {
  useDocumentTitle('Readers');
  const { user } = useAuth();
  const social = useFollowing();
  const [query, setQuery] = useState('');
  const term = useDebouncedValue(query.trim(), 300);
  const [tab, setTab] = useSearchParamState('list', 'following');

  const results = useAsync(() => searchUsers(term, 20), [term], { skip: !term });
  const followers = useAsync(() => getFollowers(user.id_user), [user.id_user]);

  const found = useMemo(() => (results.data || []).filter((u) => u.id_user !== user.id_user), [results.data, user.id_user]);
  const list = tab === 'followers' ? followers : { data: social.following, loading: social.loading, error: social.error, reload: social.reload };

  return (
    <>
      <PageHeader title="Readers" description="Follow people whose taste you trust, and see what they’re reading." />

      <div className={styles.layout}>
        <section>
          <div className={styles.search}>
            <Icon name="search" size={18} className={styles.searchIcon} />
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search readers by username"
              aria-label="Search readers by username"
              maxLength={30}
            />
          </div>

          {!term && <p className={`${page.muted} ${styles.hint}`}>Type part of a username to find someone.</p>}
          {term && results.error && <ErrorState error={results.error} onRetry={results.reload} />}
          {term && results.loading && <ListSkeleton />}
          {term && !results.loading && results.data && found.length === 0 && (
            <EmptyState icon="users" title={`No reader called “${term}”`}>
              Usernames are matched partially, so try fewer letters.
            </EmptyState>
          )}
          {term && !results.loading && found.length > 0 && (
            <ul className={page.list}>
              {found.map((u) => (
                <UserRow key={u.id_user} user={u} action={<FollowButton user={u} social={social} />} />
              ))}
            </ul>
          )}
        </section>

        <section className={`${page.card} ${styles.network}`}>
          <SegmentedControl
            label="Your network"
            size="sm"
            value={tab}
            onChange={setTab}
            options={[
              { value: 'following', label: 'Following', count: social.loading ? undefined : social.following.length },
              { value: 'followers', label: 'Followers', count: followers.data?.length },
            ]}
          />
          <div className={styles.networkList}>
            {list.error && <ErrorState error={list.error} onRetry={list.reload} />}
            {!list.error && list.loading && !list.data?.length && <ListSkeleton />}
            {!list.error && !list.loading && list.data?.length === 0 && (
              <p className={`${page.muted} ${styles.hint}`}>
                {tab === 'followers' ? 'Nobody follows you yet.' : 'You don’t follow anyone yet. Search for a reader to start.'}
              </p>
            )}
            {list.data?.length > 0 && (
              <ul className={page.list}>
                {list.data.map((u) => (
                  <UserRow key={u.id_user} user={u} action={<FollowButton user={u} social={social} />} />
                ))}
              </ul>
            )}
          </div>
        </section>
      </div>
    </>
  );
}

function ListSkeleton() {
  return (
    <div className={styles.skeleton}>
      {[0, 1, 2].map((i) => (
        <div key={i} className={styles.skeletonRow}>
          <Skeleton width={40} height={40} radius="50%" />
          <Skeleton width="40%" height={14} />
        </div>
      ))}
    </div>
  );
}
