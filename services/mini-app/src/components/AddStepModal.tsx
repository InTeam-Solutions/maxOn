import { useState } from 'react';
import { Button, Input, Typography } from '@maxhub/max-ui';
import { apiClient } from '../services/api';
import styles from './AddGoalModal.module.css'; // Reuse same styles

interface AddStepModalProps {
  goalId: string;
  onClose: () => void;
  onSuccess: () => void;
}

export const AddStepModal = ({ goalId, onClose, onSuccess }: AddStepModalProps) => {
  const [title, setTitle] = useState('');
  const [plannedDate, setPlannedDate] = useState('');
  const [plannedTime, setPlannedTime] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async () => {
    // Валидация названия
    if (!title.trim()) {
      setError('Введите название подцели');
      return;
    }

    if (title.trim().length < 3) {
      setError('Название должно содержать минимум 3 символа');
      return;
    }

    if (title.trim().length > 200) {
      setError('Название слишком длинное (максимум 200 символов)');
      return;
    }

    // Валидация даты
    if (plannedDate) {
      const selectedDate = new Date(plannedDate);
      const today = new Date();
      today.setHours(0, 0, 0, 0);

      if (selectedDate < today) {
        setError('Дата подцели не может быть в прошлом');
        return;
      }

      const maxDate = new Date();
      maxDate.setFullYear(maxDate.getFullYear() + 5);
      if (selectedDate > maxDate) {
        setError('Дата слишком далеко в будущем (максимум 5 лет)');
        return;
      }
    }

    try {
      setLoading(true);
      setError('');

      await apiClient.createStep({
        goal_id: parseInt(goalId),
        title: title.trim(),
        planned_date: plannedDate || undefined,
        planned_time: plannedTime || undefined,
        status: 'pending'
      });

      onSuccess();
    } catch (err) {
      console.error('Failed to create step:', err);
      setError('Не удалось создать подцель');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <Typography.Title variant="medium-strong">Новая подцель</Typography.Title>
          <button className={styles.closeButton} onClick={onClose}>✕</button>
        </div>

        <div className={styles.content}>
          <div className={styles.field}>
            <label className={styles.label}>Название * (3-200 символов)</label>
            <Input
              placeholder="Например: Прочитать главу 5"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              maxLength={200}
            />
          </div>

          <div className={styles.row}>
            <div className={styles.field}>
              <label className={styles.label}>Дата</label>
              <Input
                type="date"
                value={plannedDate}
                onChange={(e) => setPlannedDate(e.target.value)}
              />
            </div>

            <div className={styles.field}>
              <label className={styles.label}>Время</label>
              <Input
                type="time"
                value={plannedTime}
                onChange={(e) => setPlannedTime(e.target.value)}
              />
            </div>
          </div>

          {error && <div className={styles.error}>{error}</div>}
        </div>

        <div className={styles.footer}>
          <Button
            mode="secondary"
            appearance="neutral-themed"
            onClick={onClose}
            disabled={loading}
          >
            Отмена
          </Button>
          <Button
            mode="primary"
            appearance="themed"
            onClick={handleSubmit}
            disabled={loading}
          >
            {loading ? 'Создание...' : 'Создать подцель'}
          </Button>
        </div>
      </div>
    </div>
  );
};
