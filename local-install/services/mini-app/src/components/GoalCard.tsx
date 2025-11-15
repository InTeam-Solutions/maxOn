import dayjs from 'dayjs';
import { Typography } from '@maxhub/max-ui';
import type { Goal } from '../types/domain';
import { ProgressBar } from './ProgressBar';
import styles from './GoalCard.module.css';

interface GoalCardProps {
  goal: Goal;
  isActive?: boolean;
  onSelect?: (goalId: string) => void;
}

export const GoalCard = ({ goal, isActive, onSelect }: GoalCardProps) => (
  <button
    type="button"
    className={`${styles.card} ${isActive ? styles.active : ''}`}
    onClick={() => onSelect?.(goal.id)}
  >
    <div className={styles.header}>
      <Typography.Title variant="small-strong">
        {goal.title}
      </Typography.Title>
      <span className={styles.deadline}>{dayjs(goal.targetDate).format('DD MMM')}</span>
    </div>
    <Typography.Body variant="small" className={styles.description}>
      {goal.description}
    </Typography.Body>
    <div className={styles.progressRow}>
      <ProgressBar value={goal.progress} />
      <span className={styles.progressValue}>{goal.progress}%</span>
    </div>
    <div className={styles.meta}>
      <span>{goal.category}</span>
      <span className={styles.status}>{goal.status === 'active' ? 'В работе' : goal.status}</span>
    </div>
  </button>
);
