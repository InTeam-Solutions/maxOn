import { useEffect, useState } from 'react';
import dayjs from 'dayjs';
import { Button, Typography, IconButton } from '@maxhub/max-ui';
import type { Goal, GoalStep, Task } from '../../types/domain';
import { ProgressBar } from '../../components/ProgressBar';
import { useChat } from '../../store/ChatContext';
import { useAppState } from '../../store/AppStateContext';
import { apiClient } from '../../services/api';
import { AddStepModal } from '../../components/AddStepModal';
import { TaskCheckbox } from '../../components/TaskCheckbox';
import styles from './GoalDetails.module.css';

interface GoalDetailsProps {
  goal: Goal;
  onGoalUpdated?: () => void;
  onGoalDeleted?: () => void;
}

export const GoalDetails = ({ goal, onGoalUpdated, onGoalDeleted }: GoalDetailsProps) => {
  const [steps, setSteps] = useState<GoalStep[]>(goal.steps);
  const [deletingStepId, setDeletingStepId] = useState<string | null>(null);
  const [showAddStepModal, setShowAddStepModal] = useState(false);
  const { setChatOpen } = useAppState();
  const { sendMessage } = useChat();

  useEffect(() => {
    setSteps(goal.steps);
  }, [goal.id]); // Only reset steps when goal ID changes, not on every goal update

  const handleToggleStep = async (task: Task, newStatus: 'done' | 'scheduled') => {
    const stepId = task.stepId!;
    const backendStatus = newStatus === 'done' ? 'completed' : 'pending';

    // Optimistically update UI immediately
    setSteps((prev) =>
      prev.map((s) =>
        s.id === stepId ? { ...s, completed: backendStatus === 'completed', status: backendStatus } : s
      )
    );

    try {
      console.log('[GoalDetails] Toggling step:', stepId, 'to', backendStatus);
      // Update in API
      await apiClient.updateStep(stepId, { status: backendStatus });
      console.log('[GoalDetails] Step updated successfully');

      // Refresh parent to update goal progress
      setTimeout(() => {
        console.log('[GoalDetails] Calling onGoalUpdated to refresh progress');
        onGoalUpdated?.();
      }, 300);
    } catch (err) {
      console.error('[GoalDetails] Failed to toggle step:', err);
      alert('Не удалось обновить шаг');

      // Revert optimistic update on error
      setSteps((prev) =>
        prev.map((s) =>
          s.id === stepId ? { ...s, completed: !backendStatus, status: backendStatus === 'completed' ? 'pending' : 'completed' } : s
        )
      );
    }
  };

  const handleDeleteStep = async (stepId: string) => {
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
        <div className={styles.stepsHeader}>
          <Typography.Body variant="small" className={styles.label}>
            Подзадачи
          </Typography.Body>
          <Button
            size="small"
            mode="secondary"
            appearance="neutral-themed"
            onClick={() => setShowAddStepModal(true)}
          >
            + Подцель
          </Button>
        </div>
        <div className={styles.stepsList}>
          {steps.map((step) => {
            // Convert step to Task format for TaskCheckbox
            const stepTask: Task = {
              id: `step-${step.id}`,
              title: step.title,
              goalId: goal.id,
              goalTitle: goal.title,
              dueDate: (step as any).planned_date
                ? dayjs(`${(step as any).planned_date}T${(step as any).planned_time || '00:00:00'}`).toISOString()
                : dayjs().toISOString(),
              status: step.completed ? 'done' : 'scheduled',
              focusArea: goal.category,
              stepId: step.id,
              isEvent: false
            };

            return (
              <div key={step.id} className={styles.stepRow}>
                <div className={styles.stepContent}>
                  <TaskCheckbox
                    task={stepTask}
                    onToggle={handleToggleStep}
                    disabled={deletingStepId === step.id}
                  />
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: '4px', flex: 1 }}>
                    <span>{step.title}</span>
                    {(step as any).planned_date && (
                      <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                        📅 {dayjs((step as any).planned_date).format('DD.MM.YYYY')}
                        {(step as any).planned_time && ` в ${(step as any).planned_time}`}
                      </span>
                    )}
                    <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                      ID: {step.id} • Статус: {(step as any).status || 'pending'}
                    </span>
                  </div>
                </div>
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
            );
          })}
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

      {showAddStepModal && (
        <AddStepModal
          goalId={goal.id}
          onClose={() => setShowAddStepModal(false)}
          onSuccess={() => {
            onGoalUpdated?.();
            setShowAddStepModal(false);
          }}
        />
      )}
    </div>
  );
};
