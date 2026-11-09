import { Icon } from '../ui/Icon';
import styles from './QuestCard.module.css';

const CATEGORY_LABELS = {
  READING: 'Reading',
  EXPLORATION: 'Exploration',
  SOCIAL: 'Social',
  ENGAGEMENT: 'Engagement',
};

export function QuestCard({ quest }) {
  return (
    <article className={`${styles.card} ${quest.is_completed ? styles.done : ''}`}>
      <div className={styles.top}>
        <span className={styles.category}>{CATEGORY_LABELS[quest.category] || quest.category}</span>
        <span className={`${styles.xp} tabular`}>{quest.reward_xp} XP</span>
      </div>
      <h3 className={styles.title}>
        {quest.is_completed && <Icon name="check" size={18} className={styles.check} />}
        {quest.title}
      </h3>
      <p className={styles.description}>{quest.description}</p>
      <div className={styles.progress}>
        <span
          className={styles.track}
          role="progressbar"
          aria-valuenow={quest.progress_percentage}
          aria-valuemin={0}
          aria-valuemax={100}
        >
          <span className={styles.bar} style={{ width: `${quest.progress_percentage}%` }} />
        </span>
        <span className={`${styles.count} tabular`}>
          {Math.min(quest.current, quest.target)} / {quest.target}
        </span>
      </div>
    </article>
  );
}
