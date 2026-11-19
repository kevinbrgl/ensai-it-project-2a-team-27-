import { useRef, useState } from 'react';
import { getMyAchievements } from '../../api/users';
import { useAsync } from '../../hooks/useAsync';
import { useSearchParamState } from '../../hooks/useSearchParamState';
import { Icon } from '../ui/Icon';
import { SegmentedControl } from '../ui/SegmentedControl';
import { Skeleton } from '../ui/Skeleton';
import { EmptyState, ErrorState } from '../ui/States';
import { ProgressSummary } from './ProgressSummary';
import styles from './AchievementShowcase.module.css';

const FILTERS = [
  { value: 'all', label: 'All' },
  { value: 'unlocked', label: 'Unlocked' },
  { value: 'locked', label: 'Locked' },
];

const TIERS = ['BRONZE', 'SILVER', 'GOLD', 'PLATINUM'];

const label = (value) => value[0] + value.slice(1).toLowerCase();

// Give the API's badge symbols consistent printed marks on every platform.
// Keys carry no emoji variation selector (U+FE0F); badgeIcon strips it.
const BADGE_ICONS = {
  '🌱': 'sprout', '📖': 'book', '👓': 'glasses', '📚': 'library', '🔥': 'flame', '🏅': 'medal', '🏆': 'trophy',
  '🌅': 'sunrise', '📜': 'scroll', '📑': 'layers', '👑': 'crown', '⛰': 'mountain',
  '🧱': 'brick', '🏋': 'dumbbell', '🤹': 'juggle', '📅': 'calendar', '🗓': 'calendar', '🚪': 'door',
  '🧭': 'compass', '🔀': 'shuffle', '🌍': 'globe', '✨': 'sparkles', '🪶': 'feather', '🗺': 'map',
  '⏳': 'hourglass', '🏛': 'columns',
  '✍': 'edit', '🖋': 'pen', '💬': 'message', '📣': 'megaphone', '📝': 'document', '⭐': 'star', '👍': 'thumbsUp',
  '🤝': 'users', '🔗': 'link', '🙋': 'userPlus', '📈': 'trendingUp', '📡': 'broadcast', '💎': 'gem',
  '🫂': 'userCheck', '☕': 'cup', '🪪': 'idCard',
  '📁': 'playlists', '🗂': 'playlists', '🗄': 'archive', '📦': 'package', '❤': 'heart',
  '🏠': 'home', '🏘': 'grid', '🏰': 'castle', '🌌': 'planet', '🔖': 'bookmark',
};
const badgeIcon = (icon) => BADGE_ICONS[icon.replace(/️/g, '')] || 'trophy';

/** Consecutive achievements of one category, in the API's order. */
function byCategory(achievements) {
  const groups = [];
  for (const item of achievements) {
    let group = groups.find((entry) => entry.category === item.category);
    if (!group) groups.push(group = { category: item.category, items: [] });
    group.items.push(item);
  }
  return groups;
}

function Milestones({ achievements, everything }) {
  const [chosen, setChosen] = useState('');
  const featureRef = useRef(null);
  const current = achievements.find((item) => item.id_achievement === chosen) || achievements[0];

  // On narrow screens the list sits below the feature, so bring it back into view.
  const choose = (id) => {
    setChosen(id);
    const feature = featureRef.current;
    if (feature && window.matchMedia('(max-width: 670px)').matches && feature.getBoundingClientRect().top < 0) {
      feature.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  return (
    <div className={styles.showcase}>
      <article ref={featureRef} className={styles.feature} aria-live="polite" aria-atomic="true">
        <div className={styles.ribbon} data-tier={current.tier} aria-hidden="true">
          <span className={styles.seal}><Icon name={badgeIcon(current.icon)} size={32} /></span>
        </div>
        <p className={styles.tier}>{label(current.tier)} · {label(current.category)}</p>
        <h3>{current.title}</h3>
        <p className={styles.description}>{current.description}</p>
        <div className={styles.status}>
          <span><Icon name={current.is_unlocked ? 'check' : 'lock'} size={14} /> {current.is_unlocked ? 'Unlocked' : 'Locked'}</span>
          <span className="tabular">{current.progress.toLocaleString()} / {current.target.toLocaleString()}</span>
        </div>
        <progress className={styles.progress} value={current.progress_percentage} max={100} aria-label={`${current.title} progress`} />
      </article>
      <div className={styles.list}>
        {byCategory(achievements).map((group) => {
          const all = everything?.filter((item) => item.category === group.category);
          const headingId = `achievements-${group.category.toLowerCase()}`;
          return (
            <section key={group.category} className={styles.group} aria-labelledby={headingId}>
              <h3 id={headingId} className={styles.groupTitle}>
                {label(group.category)}
                {all?.length > 0 && (
                  <span className="tabular">
                    {all.filter((item) => item.is_unlocked).length} / {all.length} unlocked
                  </span>
                )}
              </h3>
              <ul>
                {group.items.map((item) => (
                  <li key={item.id_achievement}>
                    <button type="button" aria-pressed={item === current} className={styles.choice}
                      onClick={() => choose(item.id_achievement)}>
                      <span className={styles.token} data-tier={item.tier}>
                        <Icon name={badgeIcon(item.icon)} size={19} />
                      </span>
                      <span className={styles.name}>
                        {item.title}
                        <span className={styles.meta}>{label(item.tier)}</span>
                      </span>
                      <span className={styles.state} data-unlocked={item.is_unlocked || undefined}>
                        {item.is_unlocked ? (
                          <><Icon name="check" size={13} /> Unlocked</>
                        ) : (
                          <>
                            <span className={styles.mini} aria-hidden="true"><span style={{ width: `${item.progress_percentage}%` }} /></span>
                            <span className="tabular">{Math.round(item.progress_percentage)}%</span>
                            <span className="visually-hidden"> complete, locked</span>
                          </>
                        )}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          );
        })}
      </div>
    </div>
  );
}

/** Unlocked count, overall share and a tally per tier, read from the full list. */
function Tally({ achievements }) {
  const unlocked = achievements.filter((item) => item.is_unlocked).length;
  const share = Math.round((100 * unlocked) / achievements.length);
  const breakdown = TIERS.map((tier) => {
    const all = achievements.filter((item) => item.tier === tier);
    return { key: tier, tone: tier, label: label(tier), total: all.length, done: all.filter((item) => item.is_unlocked).length };
  }).filter((item) => item.total > 0);

  return (
    <ProgressSummary
      label="Achievements unlocked"
      share={share}
      figures={[
        { key: 'unlocked', value: unlocked, total: achievements.length, caption: 'Achievements unlocked' },
        { key: 'share', value: share, unit: '%', caption: 'Collection complete' },
      ]}
      breakdown={breakdown}
    />
  );
}

export function AchievementShowcase({ activityKey }) {
  // The tally always counts every achievement, whatever the list filter is.
  const everything = useAsync(() => getMyAchievements('all'), [activityKey]);
  const [queryFilter, setFilter] = useSearchParamState('achievements', 'all');
  const filter = FILTERS.some((option) => option.value === queryFilter) ? queryFilter : 'all';
  const { data, error, loading, reload } = useAsync(
    () => getMyAchievements(filter), [filter, activityKey],
  );
  let content;
  if (loading) {
    content = <div aria-label="Loading achievements" aria-busy="true"><Skeleton height={305} /></div>;
  } else if (error) {
    content = <ErrorState title="Achievements didn’t load" error={error} onRetry={reload} />;
  } else if (!data.length) {
    const title = { all: 'No achievements available', unlocked: 'No achievements unlocked yet', locked: 'Every achievement is unlocked' }[filter];
    content = <EmptyState icon="trophy" title={title}>{filter === 'unlocked' && 'Choose Locked to explore the milestones ahead.'}</EmptyState>;
  } else {
    content = <Milestones achievements={data} everything={everything.data} />;
  }

  return (
    <section>
      <div className={styles.header}>
        <h2>Achievements</h2>
        <SegmentedControl label="Filter achievements" options={FILTERS} value={filter} onChange={setFilter} size="sm" />
      </div>
      {everything.data?.length > 0 && <Tally achievements={everything.data} />}
      {content}
    </section>
  );
}
