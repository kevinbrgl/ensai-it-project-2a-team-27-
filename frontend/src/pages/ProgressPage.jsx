import { useOutletContext, useSearchParams } from 'react-router-dom';
import { getMyQuests, getMyStats } from '../api/users';
import { AchievementShowcase } from '../components/stats/AchievementShowcase';
import { GenreWheel } from '../components/stats/GenreWheel';
import { ProgressSummary } from '../components/stats/ProgressSummary';
import { QuestCard } from '../components/stats/QuestCard';
import { StatsPanels } from '../components/stats/StatsPanels';
import { PageHeader } from '../components/ui/PageHeader';
import { SegmentedControl } from '../components/ui/SegmentedControl';
import { Skeleton } from '../components/ui/Skeleton';
import { EmptyState, ErrorState } from '../components/ui/States';
import { useAuth } from '../context/AuthContext';
import { useLibrary } from '../context/LibraryContext';
import { useAsync } from '../hooks/useAsync';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { useSearchParamState } from '../hooks/useSearchParamState';
import styles from './ProgressPage.module.css';

const VIEWS = [
  { value: 'overview', label: 'Overview' },
  { value: 'achievements', label: 'Achievements' },
  { value: 'quests', label: 'Quests' },
];
const QUEST_FILTERS = [
  { value: 'all', label: 'All' },
  { value: 'active', label: 'In progress' },
  { value: 'completed', label: 'Completed' },
];
const QUEST_CATEGORIES = [
  { value: 'READING', label: 'Reading' },
  { value: 'EXPLORATION', label: 'Exploration' },
  { value: 'ENGAGEMENT', label: 'Engagement' },
  { value: 'SOCIAL', label: 'Social' },
];
const categoryLabel = (value) => QUEST_CATEGORIES.find((item) => item.value === value)?.label || value;

export function ProgressPage() {
  useDocumentTitle('Progress');
  const { user } = useAuth();
  const accountWheel = useOutletContext();
  const library = useLibrary();
  const [params] = useSearchParams();
  const defaultView = params.has('quests') ? 'quests' : 'overview';
  const [view, setView] = useSearchParamState('view', defaultView);
  const selected = VIEWS.some((item) => item.value === view) ? view : 'overview';
  const activityKey = library.books.map((book) => `${book.id_book}:${book.state}:${book.is_favorite}`).join(',');

  return (
    <>
      <PageHeader title="Reading progress" />
      <nav className={styles.nav} aria-label="Reading progress sections">
        {VIEWS.map((item) => (
          <button type="button" key={item.value} aria-pressed={selected === item.value} onClick={() => setView(item.value)}>
            {item.label}
          </button>
        ))}
      </nav>
      {selected === 'overview' && (
        <div className={styles.overview}>
          <GenreWheel user={user} state={accountWheel} />
          <ReadingStats activityKey={activityKey} count={library.loading || library.error ? undefined : library.books.length} />
        </div>
      )}
      {selected === 'achievements' && <AchievementShowcase activityKey={activityKey} />}
      {selected === 'quests' && <Quests activityKey={activityKey} />}
    </>
  );
}

function ReadingStats({ activityKey, count }) {
  const stats = useAsync(getMyStats, [activityKey]);
  if (stats.loading) return <div aria-busy="true" aria-label="Loading reading statistics"><Skeleton height={180} /></div>;
  if (stats.error) return <ErrorState error={stats.error} onRetry={stats.reload} title="Reading statistics didn’t load" />;
  return <StatsPanels stats={stats.data} libraryCount={count} />;
}

function Quests({ activityKey }) {
  const [queryFilter, setFilter] = useSearchParamState('quests', 'all');
  const filter = QUEST_FILTERS.some((option) => option.value === queryFilter) ? queryFilter : 'all';
  const { data, loading, error, reload } = useAsync(getMyQuests, [activityKey]);
  const all = data || [];
  const quests = filter === 'all' ? all : all.filter((quest) => quest.is_completed === (filter === 'completed'));
  // Known categories first, in a fixed order, then any the API adds later.
  const categories = [...new Set([...QUEST_CATEGORIES.map((item) => item.value), ...all.map((quest) => quest.category)])];

  let content;
  if (loading) {
    content = <div aria-busy="true" aria-label="Loading quests"><Skeleton height={180} /></div>;
  } else if (error) {
    content = <ErrorState error={error} onRetry={reload} title="Quests didn’t load" />;
  } else if (!quests.length) {
    content = <EmptyState icon="trophy" title={{ all: 'No quests available', completed: 'No quests completed yet', active: 'All quests are complete' }[filter]} />;
  } else {
    content = categories.map((category) => {
      const shown = quests.filter((quest) => quest.category === category);
      if (!shown.length) return null;
      const inCategory = all.filter((quest) => quest.category === category);
      const headingId = `quests-${category.toLowerCase()}`;
      return (
        <section key={category} className={styles.questGroup} aria-labelledby={headingId}>
          <h3 id={headingId} className={styles.groupTitle}>
            {categoryLabel(category)}
            <span className="tabular">
              {inCategory.filter((quest) => quest.is_completed).length} / {inCategory.length} completed
            </span>
          </h3>
          <div className={styles.grid}>{shown.map((quest) => <QuestCard key={quest.id_quest} quest={quest} />)}</div>
        </section>
      );
    });
  }

  return (
    <section>
      <div className={styles.questsHeader}>
        <h2>Quests</h2>
        <SegmentedControl label="Filter quests" size="sm" options={QUEST_FILTERS} value={filter} onChange={setFilter} />
      </div>
      {!loading && !error && all.length > 0 && <QuestSummary quests={all} categories={categories} />}
      {content}
    </section>
  );
}

/** Experience earned, quests completed and a tally per category, from every quest. */
function QuestSummary({ quests, categories }) {
  const complete = quests.filter((quest) => quest.is_completed);
  const earned = complete.reduce((sum, quest) => sum + quest.reward_xp, 0);
  const total = quests.reduce((sum, quest) => sum + quest.reward_xp, 0);
  const breakdown = categories.map((category) => {
    const inCategory = quests.filter((quest) => quest.category === category);
    return {
      key: category,
      label: categoryLabel(category),
      total: inCategory.length,
      done: inCategory.filter((quest) => quest.is_completed).length,
    };
  }).filter((item) => item.total > 0);

  return (
    <ProgressSummary
      label="Quest experience earned"
      share={total ? Math.round((100 * earned) / total) : 0}
      figures={[
        { key: 'xp', value: earned, total, unit: 'XP', caption: 'Experience earned' },
        { key: 'completed', value: complete.length, total: quests.length, caption: 'Quests completed' },
      ]}
      breakdown={breakdown}
    />
  );
}
