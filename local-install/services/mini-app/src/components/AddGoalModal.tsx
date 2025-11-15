import { useState } from 'react';
import { Button, Input, Typography } from '@maxhub/max-ui';
import { apiClient } from '../services/api';
import styles from './AddGoalModal.module.css';

interface AddGoalModalProps {
  onClose: () => void;
  onSuccess: () => void;
}

export const AddGoalModal = ({ onClose, onSuccess }: AddGoalModalProps) => {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [targetDate, setTargetDate] = useState('');
  const [category, setCategory] = useState('Общее');
  const [priority, setPriority] = useState<'low' | 'medium' | 'high'>('medium');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async () => {
    // Валидация названия
    if (!title.trim()) {
      setError('Введите название цели');
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

    // Валидация описания
    if (description.trim().length > 1000) {
      setError('Описание слишком длинное (максимум 1000 символов)');
      return;
    }

    // Валидация даты
    if (targetDate) {
      const selectedDate = new Date(targetDate);
      const today = new Date();
      today.setHours(0, 0, 0, 0);

      if (selectedDate < today) {
        setError('Целевая дата не может быть в прошлом');
        return;
      }

      // Проверка на слишком далекую дату (например, не более 10 лет)
      const maxDate = new Date();
      maxDate.setFullYear(maxDate.getFullYear() + 10);
      if (selectedDate > maxDate) {
        setError('Целевая дата слишком далеко в будущем (максимум 10 лет)');
        return;
      }
    }

    try {
      setLoading(true);
      setError('');

      await apiClient.createGoal({
        title: title.trim(),
        description: description.trim(),
        target_date: targetDate || new Date().toISOString().split('T')[0],
        category,
        priority,
        status: 'active'
      });

      onSuccess();
      onClose();
    } catch (err) {
      console.error('Failed to create goal:', err);
      setError('Не удалось создать цель');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <Typography.Title variant="medium-strong">Новая цель</Typography.Title>
          <button className={styles.closeButton} onClick={onClose}>✕</button>
        </div>

        <div className={styles.content}>
          <div className={styles.field}>
            <label className={styles.label}>Название * (3-200 символов)</label>
            <Input
              placeholder="Например: Изучить React"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              maxLength={200}
            />
          </div>

          <div className={styles.field}>
            <label className={styles.label}>Описание (макс. 1000 символов)</label>
            <textarea
              className={styles.textarea}
              placeholder="Опишите вашу цель подробнее..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              maxLength={1000}
            />
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
              {description.length}/1000
            </div>
          </div>

          <div className={styles.field}>
            <label className={styles.label}>Категория</label>
            <select
              className={styles.select}
              value={category}
              onChange={(e) => setCategory(e.target.value)}
            >
              <option value="Общее">Общее</option>
              <option value="Работа">Работа</option>
              <option value="Обучение">Обучение</option>
              <option value="Здоровье">Здоровье</option>
              <option value="Личное">Личное</option>
            </select>
          </div>

          <div className={styles.row}>
            <div className={styles.field}>
              <label className={styles.label}>Приоритет</label>
              <select
                className={styles.select}
                value={priority}
                onChange={(e) => setPriority(e.target.value as 'low' | 'medium' | 'high')}
              >
                <option value="low">Низкий</option>
                <option value="medium">Средний</option>
                <option value="high">Высокий</option>
              </select>
            </div>

            <div className={styles.field}>
              <label className={styles.label}>Целевая дата</label>
              <Input
                type="date"
                value={targetDate}
                onChange={(e) => setTargetDate(e.target.value)}
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
            {loading ? 'Создание...' : 'Создать цель'}
          </Button>
        </div>
      </div>
    </div>
  );
};
