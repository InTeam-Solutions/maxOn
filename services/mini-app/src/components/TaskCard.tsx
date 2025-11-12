import clsx from 'clsx';
import dayjs from 'dayjs';
import { Typography } from '@maxhub/max-ui';
import type { Task } from '../types/domain';
import styles from './TaskCard.module.css';

interface TaskCardProps {
  task: Task;
  onClick?: (task: Task) => void;
  accent?: 'green' | 'blue' | 'violet';
}

const statusLabel: Record<Task['status'], string> = {
  scheduled: '',
  'in-progress': 'Сегодня',
  done: 'Выполнено'
};

export const TaskCard = ({ task, onClick, accent = 'blue' }: TaskCardProps) => {
  const dateLabel = dayjs(task.dueDate).format('DD MMM HH:mm');
  return (
    <button type="button" className={styles.card} onClick={() => onClick?.(task)}>
      <div className={styles.header}>
        <Typography.Title variant="small-strong">
          {task.title}
        </Typography.Title>
        <span className={clsx(styles.badge, styles[accent])}>
          {statusLabel[task.status] || dateLabel}
        </span>
      </div>
      <Typography.Body variant="small" className={styles.goal}>
        Цель: {task.goalTitle}
      </Typography.Body>
      <div className={styles.meta}>
        <span className={styles.date}>{dateLabel}</span>
        <span className={styles.label}>{task.focusArea}</span>
      </div>
    </button>
  );
};
