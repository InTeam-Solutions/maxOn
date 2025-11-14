import { useMemo, useState, useEffect } from 'react';
import dayjs, { Dayjs } from 'dayjs';
import { IconButton, Button, Typography } from '@maxhub/max-ui';
import clsx from 'clsx';
import { AddEventModal } from '../../components/AddEventModal';
import { useAppState } from '../../store/AppStateContext';
import { useChat } from '../../store/ChatContext';
import { apiClient } from '../../services/api';
import type { Goal, Task } from '../../types/domain';
import { extractTasksFromGoals, groupTasksByDate } from '../../utils/taskHelpers';
import styles from './CalendarView.module.css';

const weekdayLabels = ['ПН', 'ВТ', 'СР', 'ЧТ', 'ПТ', 'СБ', 'ВС'];

const generateMonthGrid = (month: Dayjs) => {
  const startOfMonth = month.startOf('month');
  const startOffset = (startOfMonth.day() + 6) % 7;
  const gridStart = startOfMonth.subtract(startOffset, 'day');
  return Array.from({ length: 42 }, (_, index) => gridStart.add(index, 'day'));
};

export const CalendarView = () => {
  const { selectedDate, setSelectedDate, setActiveTab, selectGoal, setChatOpen } = useAppState();
  const { sendMessage } = useChat();
  const [visibleMonth, setVisibleMonth] = useState(dayjs(selectedDate).startOf('month'));
  const [completedTasks, setCompletedTasks] = useState<Record<string, boolean>>({});
  const [goals, setGoals] = useState<Goal[]>([]);
  const [loading, setLoading] = useState(false);
  const [showAddEventModal, setShowAddEventModal] = useState(false);

  // Load goals from API
  useEffect(() => {
    loadGoals();
  }, []);

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
        progress: g.progress_percent || 0,
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
      console.log('[CalendarView] Loaded goals:', transformedGoals);
    } catch (err) {
      console.error('[CalendarView] Failed to load goals:', err);
      setGoals([]);
    } finally {
      setLoading(false);
    }
  };

  // Extract tasks from goals (steps with planned_date)
  const allTasks = useMemo(() => extractTasksFromGoals(goals), [goals]);

  const tasksByDate = useMemo(() => groupTasksByDate(allTasks), [allTasks]);

  const agendaTasks = tasksByDate.get(selectedDate) ?? [];
  const monthDays = generateMonthGrid(visibleMonth);

  const handleTaskAction = async (task: Task, action: 'complete' | 'goal' | 'chat' | 'delete') => {
    if (action === 'complete') {
      // Toggle step completion status
      const newStatus = completedTasks[task.id] ? 'pending' : 'completed';
      try {
        await apiClient.updateStep(task.id, { status: newStatus });
        setCompletedTasks((prev) => ({ ...prev, [task.id]: !prev[task.id] }));
        // Reload goals to update task list
        loadGoals();
      } catch (err) {
        console.error('[CalendarView] Failed to toggle step:', err);
        alert('Не удалось обновить задачу');
      }
      return;
    }
    if (action === 'goal') {
      selectGoal(task.goalId);
      setActiveTab('goals');
      return;
    }
    if (action === 'chat') {
      setChatOpen(true);
      void sendMessage(`Что с задачей ${task.title}?`, {
        type: 'task',
        title: task.title,
        dueDate: task.dueDate
      });
      return;
    }
    if (action === 'delete') {
      if (!confirm(`Удалить задачу "${task.title}"?`)) return;

      try {
        await apiClient.deleteStep(task.id);
        // Reload goals to update task list
        loadGoals();
      } catch (err) {
        console.error('[CalendarView] Failed to delete step:', err);
        alert('Не удалось удалить задачу');
      }
    }
  };

  return (
    <div className={styles.calendarPage}>
      <div className="card">
        <div className={styles.monthHeader}>
          <IconButton
            mode='tertiary'
            appearance='neutral'
            aria-label="Предыдущий месяц"
            onClick={() => setVisibleMonth((prev) => prev.subtract(1, 'month'))}
          >
            ‹
          </IconButton>
          <Typography.Title variant="medium-strong">
            {visibleMonth.format('MMMM YYYY')}
          </Typography.Title>
          <IconButton
            mode='tertiary'
            appearance='neutral'
            aria-label="Следующий месяц"
            onClick={() => setVisibleMonth((prev) => prev.add(1, 'month'))}
          >
            ›
          </IconButton>
        </div>
        <div className={styles.weekdays}>
          {weekdayLabels.map((label) => (
            <span key={label}>{label}</span>
          ))}
        </div>
        <div className={styles.grid}>
          {monthDays.map((day) => {
            const key = day.format('YYYY-MM-DD');
            const isCurrentMonth = day.month() === visibleMonth.month();
            const isSelected = key === selectedDate;
            const hasAgenda = tasksByDate.has(key);
            return (
              <button
                key={key}
                type="button"
                className={clsx(
                  styles.dayCell,
                  !isCurrentMonth && styles.dimmed,
                  isSelected && styles.active
                )}
                onClick={() => {
                  setSelectedDate(key);
                  setVisibleMonth(day.startOf('month'));
                }}
              >
                <span>{day.format('D')}</span>
                {hasAgenda && <span className={styles.marker} />}
              </button>
            );
          })}
        </div>
      </div>

      <section className="card">
        <Typography.Title variant="medium-strong">
          Задачи на день
        </Typography.Title>
        <Typography.Body variant="small" className={styles.agendaSubtitle}>
          {dayjs(selectedDate).format('dddd, DD MMMM')}
        </Typography.Body>

        <div className={styles.agendaList}>
          {agendaTasks.length === 0 && (
            <div className={styles.emptyState}>На этот день задач нет — можно сфокусироваться.</div>
          )}
          {agendaTasks.map((task) => (
            <div key={task.id} className={styles.agendaItem}>
              <div>
                <Typography.Title variant="small-strong">{task.title}</Typography.Title>
                <Typography.Body variant="small" className={styles.agendaMeta}>
                  Цель: {task.goalTitle}
                </Typography.Body>
              </div>
              <div className={styles.agendaActions}>
                <Button
                  size="small"
                  mode="secondary"
                  appearance={completedTasks[task.id] ? 'neutral-themed' : 'themed'}
                  onClick={() => handleTaskAction(task, 'complete')}
                >
                  {completedTasks[task.id] ? 'Вернуть' : 'Готово'}
                </Button>
                <IconButton
                  size="small"
                  mode="tertiary"
                  appearance="neutral"
                  aria-label="Перейти к цели"
                  onClick={() => handleTaskAction(task, 'goal')}
                >
                  🎯
                </IconButton>
                <IconButton
                  size="small"
                  mode="tertiary"
                  appearance="neutral"
                  aria-label="Открыть чат"
                  onClick={() => handleTaskAction(task, 'chat')}
                >
                  💬
                </IconButton>
                <IconButton
                  size="small"
                  mode="tertiary"
                  appearance="neutral"
                  aria-label="Удалить задачу"
                  onClick={() => handleTaskAction(task, 'delete')}
                >
                  🗑️
                </IconButton>
              </div>
            </div>
          ))}
        </div>

        <div className={styles.actionsRow}>
          <Button
            mode="primary"
            appearance="themed"
            onClick={() => setShowAddEventModal(true)}
          >
            + Событие
          </Button>
        </div>
      </section>

      {showAddEventModal && (
        <AddEventModal
          onClose={() => setShowAddEventModal(false)}
          onSuccess={() => loadGoals()}
          selectedDate={selectedDate}
        />
      )}
    </div>
  );
};
