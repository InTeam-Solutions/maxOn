import { useState } from 'react';
import type { Task } from '../types/domain';
import styles from './TaskCheckbox.module.css';

interface TaskCheckboxProps {
  task: Task;
  onToggle: (task: Task, newStatus: 'done' | 'scheduled') => Promise<void>;
  disabled?: boolean;
}

export const TaskCheckbox = ({ task, onToggle, disabled }: TaskCheckboxProps) => {
  const [loading, setLoading] = useState(false);
  const isCompleted = task.status === 'done';

  const handleToggle = async (e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent parent click handlers

    if (loading || disabled) return;

    setLoading(true);
    try {
      const newStatus = isCompleted ? 'scheduled' : 'done';
      await onToggle(task, newStatus);
    } catch (error) {
      console.error('[TaskCheckbox] Failed to toggle task:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <button
      className={`${styles.checkbox} ${isCompleted ? styles.checked : ''} ${loading ? styles.loading : ''}`}
      onClick={handleToggle}
      disabled={loading || disabled}
      aria-label={isCompleted ? 'Отметить как невыполненное' : 'Отметить как выполненное'}
    >
      {isCompleted && (
        <svg
          width="16"
          height="16"
          viewBox="0 0 16 16"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            d="M13.3337 4L6.00033 11.3333L2.66699 8"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      )}
    </button>
  );
};
