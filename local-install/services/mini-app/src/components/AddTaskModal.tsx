import { useState, useEffect } from 'react';
import dayjs from 'dayjs';
import { Button, Input, Typography } from '@maxhub/max-ui';
import { apiClient } from '../services/api';
import type { Goal } from '../types/domain';
import styles from './AddGoalModal.module.css'; // Reuse same styles

interface AddTaskModalProps {
  onClose: () => void;
  onSuccess: () => void;
  selectedDate?: string;
}

export const AddTaskModal = ({ onClose, onSuccess, selectedDate }: AddTaskModalProps) => {
  const [title, setTitle] = useState('');
  const [goalId, setGoalId] = useState('');
  const [plannedDate, setPlannedDate] = useState(selectedDate || '');
  const [plannedTime, setPlannedTime] = useState('');
  const [goals, setGoals] = useState<Goal[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    loadGoals();
  }, []);

  const loadGoals = async () => {
    try {
      const data = await apiClient.getGoals();
      const transformedGoals: Goal[] = data.map((g: any) => ({
        id: String(g.id),
        title: g.title,
        description: g.description || '',
        targetDate: g.target_date || new Date().toISOString(),
        progress: g.progress_percent || 0,
        category: g.category || 'Общее',
        priority: g.priority || 'medium',
        status: g.status || 'active',
        steps: []
      }));
      setGoals(transformedGoals.filter(g => g.status === 'active'));
      if (transformedGoals.length > 0 && !goalId) {
        setGoalId(transformedGoals[0].id);
      }
    } catch (err) {
      console.error('Failed to load goals:', err);
    }
  };

  const handleSubmit = async () => {
    // Валидация названия
    if (!title.trim()) {
      setError('Введите название задачи');
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

    // Валидация выбора цели
    if (!goalId) {
      setError('Выберите цель');
      return;
    }

    // Валидация даты
    if (plannedDate) {
      const selectedDate = new Date(plannedDate);
      const today = new Date();
      today.setHours(0, 0, 0, 0);

      if (selectedDate < today) {
        setError('Дата задачи не может быть в прошлом');
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

      // Use today's date if not specified
      const finalDate = plannedDate || dayjs().format('YYYY-MM-DD');
      // Use current time if not specified
      const finalTime = plannedTime || dayjs().format('HH:mm');

      console.log('[AddTaskModal] Creating step with:', {
        goal_id: parseInt(goalId),
        title: title.trim(),
        planned_date: finalDate,
        planned_time: finalTime,
        plannedDateRaw: plannedDate,
        plannedTimeRaw: plannedTime
      });

      await apiClient.createStep({
        goal_id: parseInt(goalId),
        title: title.trim(),
        planned_date: finalDate,
        planned_time: finalTime,
        status: 'pending'
      });

      onSuccess();
      onClose();
    } catch (err) {
      console.error('Failed to create task:', err);
      setError('Не удалось создать задачу');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <Typography.Title variant="medium-strong">Новая задача</Typography.Title>
          <button className={styles.closeButton} onClick={onClose}>✕</button>
        </div>

        <div className={styles.content}>
          {goals.length === 0 ? (
            <div style={{
              padding: '20px',
              textAlign: 'center',
              color: 'var(--text-secondary)'
            }}>
              <p>Сначала создайте цель, чтобы добавить к ней задачу</p>
            </div>
          ) : (
            <>
              <div className={styles.field}>
                <label className={styles.label}>Название * (3-200 символов)</label>
                <Input
                  placeholder="Например: Прочитать главу 5"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  maxLength={200}
                />
              </div>

              <div className={styles.field}>
                <label className={styles.label}>Цель *</label>
                <select
                  className={styles.select}
                  value={goalId}
                  onChange={(e) => setGoalId(e.target.value)}
                >
                  <option value="">Выберите цель</option>
                  {goals.map((goal) => (
                    <option key={goal.id} value={goal.id}>
                      {goal.title}
                    </option>
                  ))}
                </select>
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
            </>
          )}
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
          {goals.length > 0 && (
            <Button
              mode="primary"
              appearance="themed"
              onClick={handleSubmit}
              disabled={loading}
            >
              {loading ? 'Создание...' : 'Создать задачу'}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
};
