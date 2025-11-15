import { useState } from 'react';
import { Button, Input, Typography } from '@maxhub/max-ui';
import { apiClient } from '../services/api';
import styles from './AddGoalModal.module.css'; // Reuse same styles

interface AddEventModalProps {
  onClose: () => void;
  onSuccess: () => void;
  selectedDate?: string;
}

export const AddEventModal = ({ onClose, onSuccess, selectedDate }: AddEventModalProps) => {
  const [title, setTitle] = useState('');
  const [date, setDate] = useState(selectedDate || '');
  const [time, setTime] = useState('');
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async () => {
    // Валидация названия
    if (!title.trim()) {
      setError('Введите название события');
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
    if (!date) {
      setError('Выберите дату');
      return;
    }

    const selectedDate = new Date(date);
    const minDate = new Date();
    minDate.setFullYear(minDate.getFullYear() - 1); // Можно создавать события на год назад
    minDate.setHours(0, 0, 0, 0);

    if (selectedDate < minDate) {
      setError('Дата события слишком далеко в прошлом (максимум 1 год назад)');
      return;
    }

    const maxDate = new Date();
    maxDate.setFullYear(maxDate.getFullYear() + 5);
    if (selectedDate > maxDate) {
      setError('Дата события слишком далеко в будущем (максимум 5 лет)');
      return;
    }

    // Валидация заметок
    if (notes.trim().length > 500) {
      setError('Заметки слишком длинные (максимум 500 символов)');
      return;
    }

    try {
      setLoading(true);
      setError('');

      await apiClient.createEvent({
        title: title.trim(),
        date,
        time: time || undefined,
        notes: notes.trim() || undefined
      });

      onSuccess();
      onClose();
    } catch (err) {
      console.error('Failed to create event:', err);
      setError('Не удалось создать событие');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <Typography.Title variant="medium-strong">Новое событие</Typography.Title>
          <button className={styles.closeButton} onClick={onClose}>✕</button>
        </div>

        <div className={styles.content}>
          <div className={styles.field}>
            <label className={styles.label}>Название * (3-200 символов)</label>
            <Input
              placeholder="Например: Встреча с клиентом"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              maxLength={200}
            />
          </div>

          <div className={styles.row}>
            <div className={styles.field}>
              <label className={styles.label}>Дата *</label>
              <Input
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
              />
            </div>

            <div className={styles.field}>
              <label className={styles.label}>Время</label>
              <Input
                type="time"
                value={time}
                onChange={(e) => setTime(e.target.value)}
              />
            </div>
          </div>

          <div className={styles.field}>
            <label className={styles.label}>Заметки (макс. 500 символов)</label>
            <textarea
              className={styles.textarea}
              placeholder="Дополнительная информация..."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
              maxLength={500}
            />
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
              {notes.length}/500
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
            {loading ? 'Создание...' : 'Создать событие'}
          </Button>
        </div>
      </div>
    </div>
  );
};
