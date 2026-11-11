import { useMemo } from 'react';
import { getMyQuests, getMyStats } from '../api/users';
import { QuestCard } from '../components/stats/QuestCard';
import { StatsPanels } from '../components/stats/StatsPanels';
import { PageHeader } from '../components/ui/PageHeader';
import { SegmentedControl } from '../components/ui/SegmentedControl';
import { Skeleton } from '../components/ui/Skeleton';
import { EmptyState, ErrorState } from '../components/ui/States';
import { useLibrary } from '../context/LibraryContext';
import { useAsync } from '../hooks/useAsync';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { useSearchParamState } from '../hooks/useSearchParamState';
import page from './Page.module.css';
import styles from './ProgressPage.module.css';

const QUEST_FILTERS = [
  { value: 'all', label: 'All' },
  { value: 'active', label: 'In progress' },
  { value: 'completed', label: 'Completed' },
];

export function ProgressPage() {
  useDocumentTitle('Progress');
  const library = useLibrary();
  const [filter, setFilter] = useSearchParamState('quests', 'all');
  // Re-fetch stats when the library changes (a book finished, removed…).
  const libraryKey = library.books.map((b) => `${b.id_book}:${b.state}`).join(',');
  const stats = useAsync(getMyStats, [libraryKey]);
  const allQuests = useAsync(() => getMyQuests('all'), [libraryKey]);
  const quests = useAsync(() => getMyQuests(filter), [filter, libraryKey]);

  const xp = useMemo(() => {
    const list = allQuests.data || [];
    return {
      earned: list.filter((q) => q.is_completed).reduce((sum, q) => sum + q.reward_xp, 0),
      total: list.reduce((sum, q) => sum + q.reward_xp, 0),
      done: list.filter((q) => q.is_completed).length,
      count: list.length,
    };
  }, [allQuests.data]);

  return (
    <>
      <PageHeader title="Your reading, in numbers" />

      <section className={page.section}>
        {stats.error && <ErrorState error={stats.error} onRetry={stats.reload} />}
        {!stats.error && !stats.data && <Skeleton height={220} radius="var(--radius-lg)" />}
        {stats.data && <StatsPanels stats={stats.data} libraryCount={library.loading ? undefined : library.books.length} />}
      </section>

      <section className={page.section}>
        <div className={page.sectionHeader}>
          <div className={styles.questsTitle}>
            <h2>Quests</h2>
            {allQuests.data && (
              <span className={`${styles.xp} tabular`}>
                {xp.earned} / {xp.total} XP · {xp.done} of {xp.count} completed
              </span>
            )}
          </div>
          <SegmentedControl label="Filter quests" size="sm" options={QUEST_FILTERS} value={filter} onChange={setFilter} />
        </div>
        {quests.error && <ErrorState error={quests.error} onRetry={quests.reload} />}
        {!quests.error && !quests.data && (
          <div className={styles.grid}>
            {[0, 1, 2].map((i) => (
              <Skeleton key={i} height={150} radius="var(--radius-lg)" />
            ))}
          </div>
        )}
        {quests.data?.length === 0 && (
          <EmptyState icon="trophy" title={filter === 'completed' ? 'No quest completed yet' : 'All quests are complete'}>
            {filter === 'completed' ? 'Finish a book or follow a reader to complete your first quest.' : 'Nothing left in progress.'}
          </EmptyState>
        )}
        {quests.data?.length > 0 && (
          <div className={styles.grid}>
            {quests.data.map((quest) => (
              <QuestCard key={quest.id_quest} quest={quest} />
            ))}
          </div>
        )}
      </section>
    </>
  );
}
