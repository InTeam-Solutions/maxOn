import { useEffect, useState } from 'react';
import dayjs from 'dayjs';
import { Button, Typography, IconButton } from '@maxhub/max-ui';
import type { Goal, GoalStep } from '../../types/domain';
import { ProgressBar } from '../../components/ProgressBar';
import { useChat } from '../../store/ChatContext';
import { useAppState } from '../../store/AppStateContext';
import { apiClient } from '../../services/api';
import styles from './GoalDetails.module.css';

interface GoalDetailsProps {
  goal: Goal;
  onGoalUpdated?: () => void;
  onGoalDeleted?: () => void;
}

export const GoalDetails = ({ goal, onGoalUpdated, onGoalDeleted }: GoalDetailsProps) => {
  const [steps, setSteps] = useState<GoalStep[]>(goal.steps);
  const [deletingStepId, setDeletingStepId] = useState<string | null>(null);
  const { setChatOpen } = useAppState();
  const { sendMessage } = useChat();

  useEffect(() => {
    setSteps(goal.steps);
  }, [goal]);

  const toggleStep = async (step: GoalStep) => {
    const newStatus = step.completed ? 'pending' : 'completed';

    try {
      // Update in API
      await apiClient.updateStep(step.id, { status: newStatus });

      // Update local state
      setSteps((prev) =>
        prev.map((s) =>
          s.id === step.id ? { ...s, completed: !s.completed } : s
        )
      );

      // Notify parent to refresh
      onGoalUpdated?.();
    } catch (err) {
      console.error('[GoalDetails] Failed to toggle step:', err);
      alert('Не удалось обновить шаг');
    }
  };

  const handleDeleteStep = async (stepId: string) => {
    if (!confirm('Удалить этот шаг?')) return;

    setDeletingStepId(stepId);
    try {
      await apiClient.deleteStep(stepId);

      // Update local state
      setSteps((prev) => prev.filter((s) => s.id !== stepId));

      // Notify parent to refresh
      onGoalUpdated?.();
    } catch (err) {
      console.error('[GoalDetails] Failed to delete step:', err);
      alert('Не удалось удалить шаг');
    } finally {
      setDeletingStepId(null);
    }
  };

  const handleDeleteGoal = async () => {
    if (!confirm(`Удалить цель "${goal.title}"? Это действие нельзя отменить.`)) return;

    try {
      await apiClient.deleteGoal(goal.id);
      onGoalDeleted?.();
    } catch (err) {
      console.error('[GoalDetails] Failed to delete goal:', err);
      alert('Не удалось удалить цель');
    }
  };

  const handleDiscuss = () => {
    setChatOpen(true);
    void sendMessage(`Обсудим цель ${goal.title}`, {
      type: 'goal',
      title: goal.title,
      progress: goal.progress,
      description: goal.description
    });
  };

  return (
    <div className={styles.details}>
      <Typography.Title variant="medium-strong">
        {goal.title}
      </Typography.Title>
      <Typography.Body variant="medium" className={styles.description}>
        {goal.description}
      </Typography.Body>
      <div className={styles.meta}>
        <div>
          <span className={styles.label}>Крайний срок</span>
          <span>{dayjs(goal.targetDate).format('DD MMM YYYY')}</span>
        </div>
        <div>
          <span className={styles.label}>Категория</span>
          <span>{goal.category}</span>
        </div>
      </div>
      <div>
        <div className={styles.progressHeader}>
          <span>Прогресс</span>
          <span>{goal.progress}%</span>
        </div>
        <ProgressBar value={goal.progress} accent="violet" />
      </div>

      <div className={styles.steps}>
        <Typography.Body variant="small" className={styles.label}>
          Подзадачи
        </Typography.Body>
        <div className={styles.stepsList}>
          {steps.map((step) => (
            <div key={step.id} className={styles.stepRow}>
              <button
                type="button"
                className={`${styles.stepButton} ${step.completed ? styles.completed : ''}`}
                onClick={() => toggleStep(step)}
                disabled={deletingStepId === step.id}
              >
                <span className={styles.checkbox} aria-hidden />
                <span>{step.title}</span>
              </button>
              <IconButton
                size="small"
                mode="tertiary"
                appearance="neutral"
                aria-label="Удалить шаг"
                onClick={() => handleDeleteStep(step.id)}
                disabled={deletingStepId === step.id}
              >
                🗑️
              </IconButton>
            </div>
          ))}
        </div>
      </div>

      <div className={styles.actions}>
        <Button
          mode="primary"
          appearance="themed"
          stretched
          className={styles.gradientButton}
          onClick={handleDiscuss}
        >
          Обсудить с maxOn
        </Button>
        <Button
          mode="secondary"
          appearance="negative"
          stretched
          onClick={handleDeleteGoal}
        >
          Удалить цель
        </Button>
      </div>
    </div>
  );
};
