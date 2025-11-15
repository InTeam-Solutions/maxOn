import { useState, useEffect, useMemo } from 'react';
import { Typography, Button } from '@maxhub/max-ui';
import { LineChart, Line, PieChart, Pie, BarChart, Bar, Cell, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
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

      // TODO: Replace with real API call when backend is ready
      // const stats = await apiClient.getStatistics();
      // const leaderboardData = await apiClient.getLeaderboard();
      // setLeaderboard(leaderboardData);

      // Mock leaderboard for now
      setLeaderboard([
        { userId: '1', displayName: 'User #1', streakDays: 45, rank: 1 },
        { userId: '2', displayName: 'User #2', streakDays: 38, rank: 2 },
        { userId: '3', displayName: 'User #3', streakDays: 32, rank: 3 },
        { userId: '4', displayName: 'User #4', streakDays: 28, rank: 4 },
        { userId: '5', displayName: 'User #5', streakDays: 25, rank: 5 },
      ]);
    } catch (err) {
      console.error('[StatisticsView] Failed to load data:', err);
    } finally {
      setLoading(false);
    }
  };

  // Calculate statistics from goals data
  const statistics: StatisticsData = useMemo(() => {
    const totalGoals = goals.length;
    const completedGoals = goals.filter(g => g.status === 'completed').length;
    const activeGoals = goals.filter(g => g.status === 'active').length;

    // Calculate streak (simplified - count days with activity in last 30 days)
    const allTasks = extractTasksFromGoals(goals);
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
  }, [goals, timeRange]);

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

      {/* Progress Line Chart */}
      <div className="card">
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
              strokeWidth={2}
              dot={{ fill: '#6366f1', r: 4 }}
              activeDot={{ r: 6 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Category Pie Chart and Weekday Bar Chart - Side by Side */}
      <div className={styles.chartsRow}>
        <div className="card" style={{ flex: 1 }}>
          <Typography.Title variant="small-strong" style={{ marginBottom: '16px' }}>
            Распределение по категориям
          </Typography.Title>
          {statistics.categoryDistribution.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={statistics.categoryDistribution}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={(entry) => entry.name}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {statistics.categoryDistribution.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    background: 'var(--bg-elevated)',
                    border: '1px solid var(--border-soft)',
                    borderRadius: '8px'
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className={styles.emptyChart}>Нет данных</div>
          )}
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
          {leaderboard.map((entry) => (
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
    </div>
  );
};
