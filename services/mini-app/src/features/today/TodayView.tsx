import { useMemo, useState, useEffect } from 'react';
import dayjs from 'dayjs';
import { Button, Input, Typography } from '@maxhub/max-ui';
import { TaskCard } from '../../components/TaskCard';
import { SectionHeading } from '../../components/SectionHeading';
import { AddGoalModal } from '../../components/AddGoalModal';
import { AddTaskModal } from '../../components/AddTaskModal';
import { useAppState } from '../../store/AppStateContext';
import { useChat } from '../../store/ChatContext';
import { apiClient } from '../../services/api';
import type { Goal, Task } from '../../types/domain';
import {
  extractTasksFromGoals,
  getTodayTasks,
  getUpcomingTasks,
  countTasksByDate
} from '../../utils/taskHelpers';
import styles from './TodayView.module.css';

const buildMiniCalendar = (date: string) => {
  const center = dayjs(date);
  const start = center.subtract(2, 'day');
  return Array.from({ length: 5 }, (_, index) => start.add(index, 'day'));
};

export const TodayView = () => {
  const { setActiveTab, selectGoal, selectedDate, setSelectedDate, setChatOpen } = useAppState();
  const { sendMessage } = useChat();
  const [prompt, setPrompt] = useState('');
  const [goals, setGoals] = useState<Goal[]>([]);
  const [events, setEvents] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [showAddGoalModal, setShowAddGoalModal] = useState(false);
  const [showAddTaskModal, setShowAddTaskModal] = useState(false);

  // Load goals and events from API
  useEffect(() => {
    loadGoals();
    loadEvents();
  }, []);

  const loadEvents = async () => {
    try {
      console.log('[TodayView] Loading events for user:', apiClient.getUserId());
      const data = await apiClient.getEvents();
      console.log('[TodayView] Events API response:', data);
      setEvents(data || []);
    } catch (err) {
      console.error('[TodayView] Failed to load events:', err);
      setEvents([]);
    }
  };

  const loadGoals = async () => {
    try {
      setLoading(true);
      const data = await apiClient.getGoals();

      // Transform API response to match UI format
      const transformedGoals: Goal[] = data.map((g: any) => ({
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
      console.log('[TodayView] Loaded goals:', transformedGoals);

      // Debug: Check what tasks we extract
      const tasks = extractTasksFromGoals(transformedGoals);
      console.log('[TodayView] Extracted tasks:', tasks);
      console.log('[TodayView] Today tasks:', getTodayTasks(tasks));
    } catch (err) {
      console.error('[TodayView] Failed to load goals:', err);
      setGoals([]);
    } finally {
      setLoading(false);
    }
  };

  // Convert events to Task format
  const eventTasks = useMemo(() => {
    return events.map((event) => ({
      id: `event-${event.id}`,
      title: event.title,
      goalId: '', // Events don't belong to goals
      goalTitle: 'Событие',
      dueDate: event.time
        ? dayjs(`${event.date}T${event.time}`).toISOString()
        : dayjs(event.date).toISOString(),
      status: 'scheduled' as const,
      focusArea: 'События',
      isEvent: true,
      eventData: event
    }));
  }, [events]);

  // Extract tasks from goals (steps with planned_date)
  const goalTasks = useMemo(() => extractTasksFromGoals(goals), [goals]);

  // Combine events and goal tasks
  const allTasks = useMemo(() => [...eventTasks, ...goalTasks], [eventTasks, goalTasks]);

  const tasksToday = useMemo(() => getTodayTasks(allTasks), [allTasks]);

  const nextThreeDays = useMemo(() => getUpcomingTasks(allTasks, 3), [allTasks]);

  const calendarDays = buildMiniCalendar(selectedDate);
  const tasksByDay = useMemo(() => countTasksByDate(allTasks), [allTasks]);

  const activeGoalsCount = goals.filter(g => g.status === 'active').length;
  const stepsToday = tasksToday.length;

  const handleTaskClick = (task: Task) => {
    const isEvent = (task as any).isEvent;
    if (isEvent) {
      alert('Это событие, оно не связано с целью. Откройте календарь для подробностей.');
      return;
    }
    selectGoal(task.goalId);
    setActiveTab('goals');
  };

  const handleDeleteTask = async (task: Task) => {
    const isEvent = (task as any).isEvent;

    try {
      if (isEvent) {
        // Extract event ID from task ID (format: "event-{id}")
        const eventId = task.id.replace('event-', '');
        await apiClient.deleteEvent(eventId);
        // Reload events to update list
        loadEvents();
      } else {
        await apiClient.deleteStep(task.id);
        // Reload goals to update task list
        loadGoals();
      }
    } catch (err: any) {
      console.error('[TodayView] Failed to delete:', err);
      if (err.message?.includes('404')) {
        alert('Событие уже было удалено');
        // Reload to sync state
        if (isEvent) {
          loadEvents();
        } else {
          loadGoals();
        }
      } else {
        alert('Не удалось удалить: ' + (err.message || 'Неизвестная ошибка'));
      }
    }
  };

  const handlePromptSubmit = async () => {
    if (!prompt.trim()) return;
    setChatOpen(true);
    await sendMessage(prompt, { type: 'general' });
    setPrompt('');
  };

  // Show loading state until data is loaded
  if (loading) {
    return (
      <div className={styles.today}>
        <div className="card" style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          minHeight: '400px'
        }}>
          <div style={{ textAlign: 'center' }}>
            <Typography.Title variant="large-strong">Загрузка...</Typography.Title>
            <Typography.Body variant="medium" style={{ marginTop: '12px', color: 'var(--text-secondary)' }}>
              Подгружаем ваши цели и задачи
            </Typography.Body>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.today}>
      <div className="card">
        <div className={styles.headerRow}>
          <div className={styles.headingGroup}>
            <Typography.Title variant="large-strong" className={styles.title}>
              Главная
            </Typography.Title>
            <Typography.Body variant="medium" className={styles.subtitle}>
              {`${activeGoalsCount} активные цели · ${stepsToday} шагов на сегодня`}
            </Typography.Body>
          </div>
          <span className={styles.fireEmoji}>🔥</span>
        </div>
        <div className={styles.miniCalendar}>
          {calendarDays.map((day) => {
            const key = day.format('YYYY-MM-DD');
            const isActive = key === selectedDate;
            const isToday = key === dayjs().format('YYYY-MM-DD');
            const hasTasks = tasksByDay.get(key);
            return (
              <button
                key={key}
                type="button"
                className={`${styles.calendarDay} ${isActive ? styles.active : ''} ${isToday ? styles.today : ''}`}
                onClick={() => setSelectedDate(key)}
              >
                <span className={styles.calendarWeekday}>{day.format('dd')}</span>
                <span className={styles.calendarDate}>{day.format('D')}</span>
                <span className={styles.calendarDot} style={{ opacity: hasTasks ? 1 : 0 }} />
              </button>
            );
          })}
        </div>
      </div>

      <section>
        <SectionHeading title="Задачи на сегодня" subtitle={dayjs().format('dddd, DD MMMM')} />
        <div className={styles.list}>
          {tasksToday.map((task) => (
            <TaskCard
              key={task.id}
              task={task}
              onClick={() => handleTaskClick(task)}
              onDelete={handleDeleteTask}
            />
          ))}
          {tasksToday.length === 0 && (
            <div className={styles.placeholder}>Сегодня всё выполнено 👏</div>
          )}
        </div>
      </section>

      <section>
        <SectionHeading title="Ближайшие 3 дня" subtitle="Сфокусируйся заранее" />
        <div className={styles.list}>
          {nextThreeDays.map((task) => (
            <TaskCard
              key={task.id}
              task={task}
              accent="violet"
              onClick={() => handleTaskClick(task)}
              onDelete={handleDeleteTask}
            />
          ))}
        </div>
      </section>

      <div className={styles.actionsRow}>
        <Button
          mode="secondary"
          appearance="neutral-themed"
          onClick={() => setShowAddTaskModal(true)}
        >
          + Задача
        </Button>
        <Button
          mode="primary"
          appearance="themed"
          className={styles.gradientButton}
          onClick={() => setShowAddGoalModal(true)}
        >
          + Цель
        </Button>
      </div>

      {showAddGoalModal && (
        <AddGoalModal
          onClose={() => setShowAddGoalModal(false)}
          onSuccess={() => loadGoals()}
        />
      )}

      {showAddTaskModal && (
        <AddTaskModal
          onClose={() => setShowAddTaskModal(false)}
          onSuccess={() => loadGoals()}
          selectedDate={selectedDate}
        />
      )}
    </div>
  );
};
