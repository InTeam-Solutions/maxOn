import { useEffect, useState } from 'react';
import { Typography } from '@maxhub/max-ui';
import { mockGoals } from '../../mocks/data';
import { useAppState } from '../../store/AppStateContext';
import { GoalCard } from '../../components/GoalCard';
import { GoalDetails } from './GoalDetails';
import { apiClient } from '../../services/api';
import type { Goal } from '../../types/domain';
import styles from './GoalsView.module.css';

const USE_REAL_API = true; // Force real API in production

export const GoalsView = () => {
  const { selectedGoalId, selectGoal } = useAppState();
  const [goals, setGoals] = useState<Goal[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const currentGoal = goals.find((goal) => goal.id === selectedGoalId) ?? goals[0];

  useEffect(() => {
    if (USE_REAL_API) {
      loadGoals();
    }
  }, []);

  useEffect(() => {
    if (!selectedGoalId && goals[0]) {
      selectGoal(goals[0].id);
    }
  }, [selectedGoalId, selectGoal, goals]);

  const loadGoals = async (preserveSelection = false) => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiClient.getGoals();

      // Transform API response to match UI format
      const transformedGoals: Goal[] = data.map((g: any) => ({
        id: String(g.id),
        title: g.title,
        description: g.description || '',
        targetDate: g.target_date || new Date().toISOString(),
        progress: calculateProgress(g.steps || []),
        category: g.category || 'Общее',
        priority: g.priority || 'medium',
        status: g.status || 'active',
        steps: (g.steps || []).map((s: any) => ({
          id: String(s.id),
          title: s.title,
          completed: s.status === 'completed'
        }))
      }));

      setGoals(transformedGoals);

      // If goal was deleted and we're not preserving selection, select first goal
      if (!preserveSelection && transformedGoals.length > 0) {
        selectGoal(transformedGoals[0].id);
      }

      console.log('[GoalsView] Loaded goals:', transformedGoals);
    } catch (err) {
      console.error('[GoalsView] Failed to load goals:', err);
      setError('Не удалось загрузить цели');
      setGoals([]);
    } finally {
      setLoading(false);
    }
  };

  const handleGoalUpdated = () => {
    loadGoals(true); // Preserve current selection
  };

  const handleGoalDeleted = () => {
    loadGoals(false); // Don't preserve selection, select first goal
  };

  const calculateProgress = (steps: any[]): number => {
    if (!steps || steps.length === 0) return 0;
    const completed = steps.filter(s => s.status === 'completed').length;
    return Math.round((completed / steps.length) * 100);
  };

  // Check if user_id is from URL
  const urlParams = new URLSearchParams(window.location.search);
  const userIdFromUrl = urlParams.get('user_id');

  return (
    <div className={styles.goalsPage}>
      <div>
        <Typography.Title variant="medium-strong">
          Цели
        </Typography.Title>
        <Typography.Body variant="small" className={styles.subtitle}>
          {loading ? 'Загрузка...' : error ? error : 'Управляй прогрессом и отмечай шаги'}
        </Typography.Body>
        {userIdFromUrl && !USE_REAL_API && (
          <div style={{
            background: 'rgba(59, 130, 246, 0.1)',
            border: '1px solid rgba(59, 130, 246, 0.3)',
            borderRadius: '8px',
            padding: '12px',
            marginTop: '12px',
            fontSize: '14px',
            color: '#94a3b8'
          }}>
            💡 Открыто для User ID: <code style={{color: '#3b82f6'}}>{userIdFromUrl}</code>
            <br/>
            <span style={{fontSize: '12px'}}>Сейчас показываются демо-данные. Для просмотра ваших целей нужно задеплоить бэкенд.</span>
          </div>
        )}
      </div>
      <div className={styles.columns}>
        <div className={styles.list}>
          {goals.map((goal) => (
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
            <GoalDetails
              goal={currentGoal}
              onGoalUpdated={handleGoalUpdated}
              onGoalDeleted={handleGoalDeleted}
            />
          ) : (
            <div className={styles.placeholder}>Выбери цель слева, чтобы увидеть детали.</div>
          )}
        </div>
      </div>
    </div>
  );
};
