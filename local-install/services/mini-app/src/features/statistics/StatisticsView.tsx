import { useState, useEffect, useMemo } from 'react';
import { Typography, Button } from '@maxhub/max-ui';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import dayjs from 'dayjs';
import { apiClient } from '../../services/api';
import type { Goal } from '../../types/domain';
import { extractTasksFromGoals } from '../../utils/taskHelpers';
import styles from './StatisticsView.module.css';

// Color palette
const COLORS = ['#6366f1', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981', '#06b6d4'];

interface StatisticsData {
  totalGoals: number;
  completedGoals: number;
  activeGoals: number;
  streakDays: number;
  progressTimeline: { date: string; completed: number }[];
  categoryDistribution: { name: string; value: number }[];
  activityHeatmap: { date: string; count: number }[];
  weekdayStats: { day: string; steps: number }[];
}

interface LeaderboardEntry {
  userId: string;
  displayName: string;
  streakDays: number;
  rank: number;
}

export const StatisticsView = () => {
  const [timeRange, setTimeRange] = useState<7 | 30>(7);
  const [goals, setGoals] = useState<Goal[]>([]);
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [useMockData, setUseMockData] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);

      // Load goals (we'll use this for now until backend endpoints are ready)
      const goalsData = await apiClient.getGoals();
      const transformedGoals: Goal[] = goalsData.map((g: any) => ({
        id: String(g.id),
        title: g.title,
        description: g.description || '',
        targetDate: g.target_date || new Date().toISOString(),
        progress: Math.round(g.progress_percent || 0),
        category: g.category || 'Общее',
        priority: g.priority || 'medium',
        status: g.status || 'active',
        steps: (g.steps || []).map((s: any) => ({
          id: String(s.id),
          title: s.title,
          completed: s.status === 'completed',
          status: s.status,
          planned_date: s.planned_date,
          planned_time: s.planned_time
        }))
      }));
      setGoals(transformedGoals);

      // Load leaderboard from backend
      try {
        const leaderboardData = await apiClient.getLeaderboard(20);
        setLeaderboard(leaderboardData);
      } catch (err) {
        console.error('[StatisticsView] Failed to load leaderboard, using fallback:', err);
        // Fallback to empty leaderboard if API fails
        setLeaderboard([]);
      }
    } catch (err) {
      console.error('[StatisticsView] Failed to load data:', err);
    } finally {
      setLoading(false);
    }
  };

  // Generate mock data for demo purposes
  const generateMockData = (): { goals: Goal[], leaderboard: LeaderboardEntry[] } => {
    const today = dayjs();

    // Create mock goals with completed steps spread over time
    const mockGoals: Goal[] = [
      {
        id: 'mock-1',
        title: 'Изучить React',
        description: 'Полный курс React с hooks',
        targetDate: today.add(30, 'day').toISOString(),
        progress: 75,
        category: 'Обучение',
        priority: 'high',
        status: 'active',
        steps: [
          { id: 's1', title: 'Основы React', completed: true, status: 'completed', planned_date: today.subtract(6, 'day').format('YYYY-MM-DD'), planned_time: '10:00' },
          { id: 's2', title: 'Hooks', completed: true, status: 'completed', planned_date: today.subtract(5, 'day').format('YYYY-MM-DD'), planned_time: '11:00' },
          { id: 's3', title: 'Context API', completed: true, status: 'completed', planned_date: today.subtract(4, 'day').format('YYYY-MM-DD'), planned_time: '12:00' },
          { id: 's4', title: 'Redux', completed: false, status: 'pending', planned_date: today.add(1, 'day').format('YYYY-MM-DD'), planned_time: '10:00' }
        ]
      },
      {
        id: 'mock-2',
        title: 'Фитнес программа',
        description: 'Тренировки 5 раз в неделю',
        targetDate: today.add(60, 'day').toISOString(),
        progress: 60,
        category: 'Здоровье',
        priority: 'medium',
        status: 'active',
        steps: [
          { id: 's5', title: 'Тренировка 1', completed: true, status: 'completed', planned_date: today.subtract(3, 'day').format('YYYY-MM-DD'), planned_time: '07:00' },
          { id: 's6', title: 'Тренировка 2', completed: true, status: 'completed', planned_date: today.subtract(2, 'day').format('YYYY-MM-DD'), planned_time: '07:00' },
          { id: 's7', title: 'Тренировка 3', completed: true, status: 'completed', planned_date: today.subtract(1, 'day').format('YYYY-MM-DD'), planned_time: '07:00' },
          { id: 's8', title: 'Тренировка 4', completed: true, status: 'completed', planned_date: today.format('YYYY-MM-DD'), planned_time: '07:00' }
        ]
      },
      {
        id: 'mock-3',
        title: 'Написать книгу',
        description: 'Роман на 200 страниц',
        targetDate: today.add(90, 'day').toISOString(),
        progress: 40,
        category: 'Творчество',
        priority: 'medium',
        status: 'active',
        steps: [
          { id: 's9', title: 'Глава 1', completed: true, status: 'completed', planned_date: today.subtract(20, 'day').format('YYYY-MM-DD'), planned_time: '19:00' },
          { id: 's10', title: 'Глава 2', completed: true, status: 'completed', planned_date: today.subtract(15, 'day').format('YYYY-MM-DD'), planned_time: '19:00' },
          { id: 's11', title: 'Глава 3', completed: false, status: 'pending', planned_date: today.add(5, 'day').format('YYYY-MM-DD'), planned_time: '19:00' }
        ]
      },
      {
        id: 'mock-4',
        title: 'Запустить стартап',
        description: 'SaaS продукт для малого бизнеса',
        targetDate: today.add(120, 'day').toISOString(),
        progress: 85,
        category: 'Карьера',
        priority: 'high',
        status: 'active',
        steps: [
          { id: 's12', title: 'Исследование рынка', completed: true, status: 'completed', planned_date: today.subtract(25, 'day').format('YYYY-MM-DD'), planned_time: '14:00' },
          { id: 's13', title: 'MVP', completed: true, status: 'completed', planned_date: today.subtract(10, 'day').format('YYYY-MM-DD'), planned_time: '14:00' },
          { id: 's14', title: 'Первые клиенты', completed: true, status: 'completed', planned_date: today.subtract(5, 'day').format('YYYY-MM-DD'), planned_time: '14:00' }
        ]
      },
      {
        id: 'mock-5',
        title: 'Выучить испанский',
        description: 'Уровень B2',
        targetDate: today.add(180, 'day').toISOString(),
        progress: 30,
        category: 'Обучение',
        priority: 'low',
        status: 'active',
        steps: [
          { id: 's15', title: 'Базовая грамматика', completed: true, status: 'completed', planned_date: today.subtract(30, 'day').format('YYYY-MM-DD'), planned_time: '20:00' },
          { id: 's16', title: '500 слов', completed: true, status: 'completed', planned_date: today.subtract(20, 'day').format('YYYY-MM-DD'), planned_time: '20:00' }
        ]
      },
      {
        id: 'mock-6',
        title: 'Марафон',
        description: 'Пробежать 42км',
        targetDate: today.subtract(10, 'day').toISOString(),
        progress: 100,
        category: 'Здоровье',
        priority: 'high',
        status: 'completed',
        steps: [
          { id: 's17', title: 'Тренировки', completed: true, status: 'completed', planned_date: today.subtract(60, 'day').format('YYYY-MM-DD'), planned_time: '06:00' },
          { id: 's18', title: 'Полумарафон', completed: true, status: 'completed', planned_date: today.subtract(30, 'day').format('YYYY-MM-DD'), planned_time: '06:00' },
          { id: 's19', title: 'Марафон', completed: true, status: 'completed', planned_date: today.subtract(10, 'day').format('YYYY-MM-DD'), planned_time: '06:00' }
        ]
      }
    ];

    const mockLeaderboard: LeaderboardEntry[] = [
      { userId: 'user1', displayName: 'User #1', streakDays: 42, rank: 1 },
      { userId: 'user2', displayName: 'User #2', streakDays: 38, rank: 2 },
      { userId: 'user3', displayName: 'User #3', streakDays: 31, rank: 3 },
      { userId: 'user4', displayName: 'User #4', streakDays: 28, rank: 4 },
      { userId: 'user5', displayName: 'User #5', streakDays: 25, rank: 5 },
      { userId: 'user6', displayName: 'User #6', streakDays: 21, rank: 6 },
      { userId: 'user7', displayName: 'User #7', streakDays: 18, rank: 7 },
      { userId: 'user8', displayName: 'User #8', streakDays: 15, rank: 8 },
      { userId: 'user9', displayName: 'User #9', streakDays: 12, rank: 9 },
      { userId: 'user10', displayName: 'User #10', streakDays: 10, rank: 10 },
    ];

    return { goals: mockGoals, leaderboard: mockLeaderboard };
  };

  // Calculate statistics from goals data
  const statistics: StatisticsData = useMemo(() => {
    const dataToUse = useMockData ? generateMockData().goals : goals;

    const totalGoals = dataToUse.length;
    const completedGoals = dataToUse.filter(g => g.status === 'completed').length;
    const activeGoals = dataToUse.filter(g => g.status === 'active').length;

    // Calculate streak (simplified - count days with activity in last 30 days)
    const allTasks = extractTasksFromGoals(dataToUse);
    const today = dayjs();
    let streakDays = 0;
    for (let i = 0; i < 30; i++) {
      const checkDate = today.subtract(i, 'day').format('YYYY-MM-DD');
      const hasActivity = allTasks.some(task =>
        dayjs(task.dueDate).format('YYYY-MM-DD') === checkDate && task.status === 'done'
      );
      if (hasActivity) {
        streakDays++;
      } else if (i > 0) {
        break; // Streak broken
      }
    }

    // Progress timeline (completed steps per day)
    const progressTimeline: { date: string; completed: number }[] = [];
    const daysToShow = timeRange;
    for (let i = daysToShow - 1; i >= 0; i--) {
      const date = today.subtract(i, 'day');
      const dateStr = date.format('YYYY-MM-DD');
      const completedCount = allTasks.filter(task =>
        dayjs(task.dueDate).format('YYYY-MM-DD') === dateStr && task.status === 'done'
      ).length;
      progressTimeline.push({
        date: date.format('DD MMM'),
        completed: completedCount
      });
    }

    // Category distribution
    const categoryMap = new Map<string, number>();
    goals.forEach(goal => {
      const category = goal.category || 'Общее';
      categoryMap.set(category, (categoryMap.get(category) || 0) + 1);
    });
    const categoryDistribution = Array.from(categoryMap.entries()).map(([name, value]) => ({
      name,
      value
    }));

    // Activity heatmap (last 12 weeks = 84 days)
    const activityHeatmap: { date: string; count: number }[] = [];
    for (let i = 83; i >= 0; i--) {
      const date = today.subtract(i, 'day');
      const dateStr = date.format('YYYY-MM-DD');
      const count = allTasks.filter(task =>
        dayjs(task.dueDate).format('YYYY-MM-DD') === dateStr && task.status === 'done'
      ).length;
      activityHeatmap.push({
        date: dateStr,
        count
      });
    }

    // Weekday statistics
    const weekdayMap = new Map<number, number>();
    allTasks.forEach(task => {
      if (task.status === 'done') {
        const weekday = dayjs(task.dueDate).day();
        weekdayMap.set(weekday, (weekdayMap.get(weekday) || 0) + 1);
      }
    });
    const weekdayNames = ['Вс', 'Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб'];
    const weekdayStats = weekdayNames.map((day, index) => ({
      day,
      steps: weekdayMap.get(index) || 0
    }));

    return {
      totalGoals,
      completedGoals,
      activeGoals,
      streakDays,
      progressTimeline,
      categoryDistribution,
      activityHeatmap,
      weekdayStats
    };
  }, [goals, timeRange, useMockData]);

  // Get leaderboard data (mock or real)
  const displayLeaderboard = useMockData ? generateMockData().leaderboard : leaderboard;

  if (loading) {
    return (
      <div className={styles.statistics}>
        <div className="card" style={{ padding: '60px', textAlign: 'center' }}>
          <Typography.Title variant="medium-strong">Загрузка...</Typography.Title>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.statistics}>
      {/* Header */}
      <div className={styles.header}>
        <Typography.Title variant="medium-strong">
          Статистика
        </Typography.Title>
        <Typography.Body variant="small" className={styles.subtitle}>
          Твой прогресс и достижения
        </Typography.Body>
      </div>

      {/* Metric Cards */}
      <div className={styles.metricsGrid}>
        <div className={styles.metricCard}>
          <div className={styles.metricValue}>{statistics.totalGoals}</div>
          <div className={styles.metricLabel}>Всего целей</div>
        </div>
        <div className={styles.metricCard}>
          <div className={styles.metricValue}>{statistics.completedGoals}</div>
          <div className={styles.metricLabel}>Завершено</div>
        </div>
        <div className={styles.metricCard}>
          <div className={styles.metricValue}>{statistics.activeGoals}</div>
          <div className={styles.metricLabel}>Активных</div>
        </div>
        <div className={`${styles.metricCard} ${styles.streakCard}`}>
          <div className={styles.metricValue}>{statistics.streakDays} 🔥</div>
          <div className={styles.metricLabel}>Дней streak</div>
        </div>
      </div>

      {/* Progress Line Chart and Weekday Bar Chart - Side by Side */}
      <div className={styles.chartsRow}>
        <div className="card" style={{ flex: 1 }}>
          <div className={styles.chartHeader}>
            <Typography.Title variant="small-strong">Прогресс по целям</Typography.Title>
            <div className={styles.toggleButtons}>
              <Button
                mode={timeRange === 7 ? 'primary' : 'tertiary'}
                appearance="neutral"
                onClick={() => setTimeRange(7)}
                className={styles.toggleButton}
              >
                7 дней
              </Button>
              <Button
                mode={timeRange === 30 ? 'primary' : 'tertiary'}
                appearance="neutral"
                onClick={() => setTimeRange(30)}
                className={styles.toggleButton}
              >
                30 дней
              </Button>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={statistics.progressTimeline}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
              <XAxis dataKey="date" stroke="var(--text-secondary)" fontSize={12} />
              <YAxis stroke="var(--text-secondary)" fontSize={12} />
              <Tooltip
                contentStyle={{
                  background: 'var(--bg-elevated)',
                  border: '1px solid var(--border-soft)',
                  borderRadius: '8px'
                }}
              />
              <Line
                type="monotone"
                dataKey="completed"
                stroke="#6366f1"
                strokeWidth={3}
                dot={false}
                activeDot={{ r: 6 }}
                strokeLinecap="round"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="card" style={{ flex: 1 }}>
          <Typography.Title variant="small-strong" style={{ marginBottom: '16px' }}>
            Активность по дням недели
          </Typography.Title>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={statistics.weekdayStats}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
              <XAxis dataKey="day" stroke="var(--text-secondary)" fontSize={12} />
              <YAxis stroke="var(--text-secondary)" fontSize={12} />
              <Tooltip
                contentStyle={{
                  background: 'var(--bg-elevated)',
                  border: '1px solid var(--border-soft)',
                  borderRadius: '8px'
                }}
              />
              <Bar dataKey="steps" fill="#8b5cf6" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Activity Heatmap */}
      <div className="card">
        <Typography.Title variant="small-strong" style={{ marginBottom: '16px' }}>
          Активность (последние 12 недель)
        </Typography.Title>
        <div className={styles.heatmapContainer}>
          <div className={styles.heatmap}>
            {statistics.activityHeatmap.map((day, index) => {
              const intensity = Math.min(day.count / 3, 1); // Normalize to 0-1
              const opacity = day.count === 0 ? 0.1 : 0.2 + intensity * 0.8;
              return (
                <div
                  key={day.date}
                  className={styles.heatmapCell}
                  style={{
                    backgroundColor: `rgba(99, 102, 241, ${opacity})`,
                  }}
                  title={`${day.date}: ${day.count} задач`}
                />
              );
            })}
          </div>
          <div className={styles.heatmapLegend}>
            <span>Меньше</span>
            <div className={styles.legendBoxes}>
              <div className={styles.legendBox} style={{ backgroundColor: 'rgba(99, 102, 241, 0.1)' }} />
              <div className={styles.legendBox} style={{ backgroundColor: 'rgba(99, 102, 241, 0.3)' }} />
              <div className={styles.legendBox} style={{ backgroundColor: 'rgba(99, 102, 241, 0.5)' }} />
              <div className={styles.legendBox} style={{ backgroundColor: 'rgba(99, 102, 241, 0.7)' }} />
              <div className={styles.legendBox} style={{ backgroundColor: 'rgba(99, 102, 241, 1)' }} />
            </div>
            <span>Больше</span>
          </div>
        </div>
      </div>

      {/* Leaderboard */}
      <div className="card">
        <Typography.Title variant="small-strong" style={{ marginBottom: '16px' }}>
          Лидерборд по streak
        </Typography.Title>
        <Typography.Body variant="small" className={styles.leaderboardSubtitle}>
          Топ пользователей по количеству дней подряд с активностью
        </Typography.Body>
        <ul className={styles.leaderboardList}>
          {displayLeaderboard.map((entry) => (
            <li key={entry.userId} className={styles.leaderboardRow}>
              <div className={styles.leaderboardLeft}>
                <span className={styles.rank}>{entry.rank}</span>
                <span className={styles.avatar} style={{ background: COLORS[entry.rank % COLORS.length] }}>
                  {entry.rank}
                </span>
                <div className={styles.name}>{entry.displayName}</div>
              </div>
              <div className={styles.leaderboardRight}>
                <span className={styles.streak}>{entry.streakDays} дней 🔥</span>
              </div>
            </li>
          ))}
        </ul>
      </div>

      {/* Mock Data Toggle Button */}
      <div className={styles.mockDataToggle}>
        <Button
          mode={useMockData ? 'primary' : 'secondary'}
          appearance="themed"
          stretched
          onClick={() => setUseMockData(!useMockData)}
        >
          {useMockData ? '✓ Моковые данные включены' : 'Показать моковые данные'}
        </Button>
      </div>
    </div>
  );
};
