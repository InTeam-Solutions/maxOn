import clsx from 'clsx';
import dayjs from 'dayjs';
import { Typography, IconButton } from '@maxhub/max-ui';
import type { Task } from '../types/domain';
import styles from './TaskCard.module.css';

interface TaskCardProps {
  task: Task;
  onClick?: (task: Task) => void;
  onDelete?: (task: Task) => void;
  accent?: 'green' | 'blue' | 'violet';
}

const statusLabel: Record<Task['status'], string> = {
  scheduled: '',
  'in-progress': 'Сегодня',
  done: 'Выполнено'
};

export const TaskCard = ({ task, onClick, onDelete, accent = 'blue' }: TaskCardProps) => {
  const hasNoTime = (task as any).hasNoTime;
  const isDeadline = task.isDeadline;
  const dateLabel = hasNoTime ? 'без времени' : dayjs(task.dueDate).format('DD MMM HH:mm');

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent card click
    onDelete?.(task);
  };

  return (
    <div className={styles.cardWrapper}>
      <button
        type="button"
        className={clsx(styles.card, isDeadline && styles.deadlineCard)}
        onClick={() => onClick?.(task)}
      >
        <div className={styles.header}>
          <Typography.Title variant="small-strong">
            {task.title}
          </Typography.Title>
          <span className={clsx(styles.badge, isDeadline ? styles.deadline : styles[accent])}>
            {isDeadline ? '🎯' : (statusLabel[task.status] || dateLabel)}
          </span>
        </div>
        <Typography.Body variant="small" className={styles.goal}>
          Цель: {task.goalTitle}
        </Typography.Body>
        <div className={styles.meta}>
          <span className={styles.date}>{isDeadline ? dayjs(task.dueDate).format('DD MMM') : dateLabel}</span>
          <span className={styles.label}>{task.focusArea}</span>
        </div>
      </button>
      {onDelete && !isDeadline && (
        <IconButton
          size="small"
          mode="tertiary"
          appearance="neutral"
          aria-label="Удалить задачу"
          onClick={handleDelete}
          className={styles.deleteButton}
        >
          🗑️
        </IconButton>
      )}
    </div>
  );
};
