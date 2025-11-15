import { useMemo, useState, useEffect } from 'react';
import dayjs from 'dayjs';
import { Button, Input, Typography, IconButton } from '@maxhub/max-ui';
import { TaskCard } from '../../components/TaskCard';
import { TaskCheckbox } from '../../components/TaskCheckbox';
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
  const [loading, setLoading] = useState(true);
  const [showAddGoalModal, setShowAddGoalModal] = useState(false);
  const [showAddTaskModal, setShowAddTaskModal] = useState(false);
  const [showAllTasks, setShowAllTasks] = useState(false);

  // Load goals and events from API
  useEffect(() => {
    const loadData = async () => {
      try {
        // Wait for apiClient to be configured with userId
        await apiClient.waitUntilReady();
        console.log('[TodayView] API client ready, loading data...');

        // Load goals and events in parallel
        await Promise.all([loadGoals(), loadEvents()]);
      } catch (error) {
        console.error('[TodayView] Failed to load data:', error);
      } finally {
        setLoading(false);
      }
    };

    loadData();
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
    }
  };

  // Convert events to Task format
  const eventTasks = useMemo(() => {
    return events.map((event) => {
      // Find the goal if this event is linked to one
      let goalTitle = 'Событие';
      let goalId = '';
      let stepStatus: 'done' | 'scheduled' = 'scheduled';

      if (event.event_type === 'goal_step' && event.linked_goal_id) {
        const linkedGoal = goals.find(g => String(g.id) === String(event.linked_goal_id));
        if (linkedGoal) {
          goalTitle = linkedGoal.title;
          goalId = String(linkedGoal.id);

          // Find the step status
          if (event.linked_step_id) {
            const linkedStep = linkedGoal.steps?.find(s => String(s.id) === String(event.linked_step_id));
            if (linkedStep) {
              stepStatus = linkedStep.completed ? 'done' : 'scheduled';
            }
          }
        }
      }

      return {
        id: `event-${event.id}`,
        title: event.title,
        goalId,
        goalTitle,
        dueDate: event.time
          ? dayjs(`${event.date}T${event.time}`).toISOString()
          : dayjs(event.date).toISOString(),
        status: stepStatus,
        focusArea: goalId ? 'Цели' : 'События',
        isEvent: true,
        isDeadline: false,
        eventData: event,
        stepId: event.linked_step_id ? String(event.linked_step_id) : undefined
      };
    });
  }, [events, goals]);

  // Extract tasks from goals (steps with planned_date)
  const goalTasks = useMemo(() => extractTasksFromGoals(goals), [goals]);

  // Create deadline tasks from active goals
  const deadlineTasks = useMemo(() => {
    return goals
      .filter(goal => goal.status === 'active' && goal.targetDate)
      .map(goal => ({
        id: `deadline-${goal.id}`,
        title: `Дедлайн: ${goal.title}`,
        goalId: goal.id,
        goalTitle: goal.title,
        dueDate: dayjs(goal.targetDate).startOf('day').toISOString(),
        status: 'scheduled' as const,
        focusArea: goal.category,
        isDeadline: true,
        isEvent: false
      }));
  }, [goals]);

  // Combine all tasks: deadlines first, then events and goal tasks
  const allTasks = useMemo(() => {
    const combined = [...deadlineTasks, ...eventTasks, ...goalTasks];
    // Sort: deadlines first, then by date
    return combined.sort((a, b) => {
      if (a.isDeadline && !b.isDeadline) return -1;
      if (!a.isDeadline && b.isDeadline) return 1;
      return dayjs(a.dueDate).valueOf() - dayjs(b.dueDate).valueOf();
    });
  }, [deadlineTasks, eventTasks, goalTasks]);

  const tasksToday = useMemo(() => getTodayTasks(allTasks), [allTasks]);

  const nextThreeDays = useMemo(() => getUpcomingTasks(allTasks, 3), [allTasks]);

  const calendarDays = buildMiniCalendar(selectedDate);
  const tasksByDay = useMemo(() => countTasksByDate(allTasks), [allTasks]);

  const activeGoalsCount = goals.filter(g => g.status === 'active').length;
  const stepsToday = tasksToday.length;

  const handleTaskClick = (task: Task) => {
    // For deadlines and goal tasks, navigate to the goal
    if (task.isDeadline || task.goalId) {
      selectGoal(task.goalId);
      setActiveTab('goals');
      return;
    }

    // For standalone events
    const isEvent = (task as any).isEvent;
    if (isEvent) {
      alert('Это событие, оно не связано с целью. Откройте календарь для подробностей.');
      return;
    }
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

  const handleToggleTask = async (task: Task, newStatus: 'done' | 'scheduled') => {
    const isLinkedToGoal = task.stepId && task.goalId;

    try {
      if (isLinkedToGoal) {
        const backendStatus = newStatus === 'done' ? 'completed' : 'pending';

        // Optimistically update UI
        setGoals((prevGoals) =>
          prevGoals.map(goal => {
            if (goal.id !== task.goalId) return goal;

            const updatedSteps = goal.steps?.map(step =>
              step.id === task.stepId
                ? { ...step, status: backendStatus, completed: backendStatus === 'completed' }
                : step
            ) || [];

            const completedSteps = updatedSteps.filter(s => s.completed).length;
            const totalSteps = updatedSteps.length;
            const newProgress = totalSteps > 0 ? Math.round((completedSteps / totalSteps) * 100) : 0;

            return {
              ...goal,
              steps: updatedSteps,
              progress: newProgress
            };
          })
        );

        await apiClient.updateStep(task.stepId!, { status: backendStatus });
      }
    } catch (error) {
      console.error('[TodayView] Failed to toggle task:', error);
      alert('Не удалось обновить задачу');

      // Revert on error
      loadGoals();
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
          <div className={`${styles.calendarDay} ${styles.active} ${styles.today}`}>
            <span className={styles.calendarWeekday}>{dayjs().format('dd')}</span>
            <span className={styles.calendarDate}>{dayjs().format('D')}</span>
            <span className={styles.calendarDot} style={{ opacity: tasksByDay.get(dayjs().format('YYYY-MM-DD')) ? 1 : 0 }} />
          </div>
        </div>
      </div>

      <section>
        <SectionHeading title="Задачи на сегодня" subtitle={dayjs().format('dddd, DD MMMM')} />
        <div className={styles.taskList}>
          {tasksToday.length === 0 && (
            <div className={styles.placeholder}>Сегодня всё выполнено 👏</div>
          )}
          {(showAllTasks ? tasksToday : tasksToday.slice(0, 3)).map((task) => {
            const hasCheckbox = task.stepId || !task.isEvent;
            const isDeadline = task.isDeadline;

            return (
              <div
                key={task.id}
                className={`${styles.taskItem} ${isDeadline ? styles.deadlineItem : ''}`}
              >
                {!isDeadline && hasCheckbox && (
                  <TaskCheckbox task={task} onToggle={handleToggleTask} />
                )}
                {isDeadline && (
                  <div className={styles.deadlineIcon}>🎯</div>
                )}
                <div
                  className={styles.taskContent}
                  onClick={(e) => {
                    // Only handle click if it's not from a button or checkbox
                    if ((e.target as HTMLElement).closest('button')) return;
                    handleTaskClick(task);
                  }}
                >
                  <Typography.Title variant="small-strong">{task.title}</Typography.Title>
                  <Typography.Body variant="small" className={styles.taskMeta}>
                    {isDeadline
                      ? `Цель: ${task.goalTitle}`
                      : `${task.goalTitle} • ${dayjs(task.dueDate).format('HH:mm')}`
                    }
                  </Typography.Body>
                </div>
                {!isDeadline && (
                  <IconButton
                    size="small"
                    mode="tertiary"
                    appearance="neutral"
                    aria-label="Удалить"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteTask(task);
                    }}
                  >
                    🗑️
                  </IconButton>
                )}
              </div>
            );
          })}
          {tasksToday.length > 3 && (
            <Button
              mode="tertiary"
              appearance="neutral"
              stretched
              onClick={() => setShowAllTasks(!showAllTasks)}
              className={styles.showMoreButton}
            >
              {showAllTasks ? '↑ Скрыть' : `↓ Показать все (${tasksToday.length - 3})`}
            </Button>
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
