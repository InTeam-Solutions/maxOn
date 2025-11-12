import { useEffect } from 'react';
import { Typography } from '@maxhub/max-ui';
import { mockGoals } from '../../mocks/data';
import { useAppState } from '../../store/AppStateContext';
import { GoalCard } from '../../components/GoalCard';
import { GoalDetails } from './GoalDetails';
import styles from './GoalsView.module.css';

export const GoalsView = () => {
  const { selectedGoalId, selectGoal } = useAppState();
  const currentGoal = mockGoals.find((goal) => goal.id === selectedGoalId) ?? mockGoals[0];

  useEffect(() => {
    if (!selectedGoalId && mockGoals[0]) {
      selectGoal(mockGoals[0].id);
    }
  }, [selectedGoalId, selectGoal]);

  return (
    <div className={styles.goalsPage}>
      <div>
        <Typography.Title variant="medium-strong">
          Цели
        </Typography.Title>
        <Typography.Body variant="small" className={styles.subtitle}>
          Управляй прогрессом и отмечай шаги
        </Typography.Body>
      </div>
      <div className={styles.columns}>
        <div className={styles.list}>
          {mockGoals.map((goal) => (
            <GoalCard
              key={goal.id}
              goal={goal}
              isActive={goal.id === currentGoal?.id}
              onSelect={selectGoal}
            />
          ))}
        </div>
        <div className={styles.details}>
          {currentGoal ? (
            <GoalDetails goal={currentGoal} />
          ) : (
            <div className={styles.placeholder}>Выбери цель слева, чтобы увидеть детали.</div>
          )}
        </div>
      </div>
    </div>
  );
};
