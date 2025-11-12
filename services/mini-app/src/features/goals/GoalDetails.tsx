import { useEffect, useState } from 'react';
import dayjs from 'dayjs';
import { Button, Typography } from '@maxhub/max-ui';
import type { Goal, GoalStep } from '../../types/domain';
import { ProgressBar } from '../../components/ProgressBar';
import { useChat } from '../../store/ChatContext';
import { useAppState } from '../../store/AppStateContext';
import styles from './GoalDetails.module.css';

interface GoalDetailsProps {
  goal: Goal;
}

export const GoalDetails = ({ goal }: GoalDetailsProps) => {
  const [steps, setSteps] = useState<GoalStep[]>(goal.steps);
  const { setChatOpen } = useAppState();
  const { sendMessage } = useChat();

  useEffect(() => {
    setSteps(goal.steps);
  }, [goal]);

  const toggleStep = (id: string) => {
    setSteps((prev) =>
      prev.map((step) =>
        step.id === id ? { ...step, completed: !step.completed } : step
      )
    );
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
            <button
              key={step.id}
              type="button"
              className={`${styles.stepRow} ${step.completed ? styles.completed : ''}`}
              onClick={() => toggleStep(step.id)}
            >
              <span className={styles.checkbox} aria-hidden />
              <span>{step.title}</span>
            </button>
          ))}
        </div>
      </div>

      <Button
        mode="primary"
        appearance="themed"
        stretched
        className={styles.gradientButton}
        onClick={handleDiscuss}
      >
        Обсудить с maxOn
      </Button>
    </div>
  );
};
