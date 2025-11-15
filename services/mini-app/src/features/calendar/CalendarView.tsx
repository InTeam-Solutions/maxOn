import { useMemo, useState, useEffect, useRef } from 'react';
import dayjs, { Dayjs } from 'dayjs';
import { IconButton, Button, Typography } from '@maxhub/max-ui';
import clsx from 'clsx';
import { AddEventModal } from '../../components/AddEventModal';
import { TaskCheckbox } from '../../components/TaskCheckbox';
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

interface EventLayout {
  task: Task;
  top: number;
  height: number;
  column: number;
  totalColumns: number;
}

/**
 * Calculate layout for overlapping events
 * Events that overlap in time are placed in adjacent columns
 */
const calculateEventLayout = (tasks: Task[]): EventLayout[] => {
  if (tasks.length === 0) return [];

  // Parse events with time bounds
  const events = tasks.map(task => {
    const taskDateTime = dayjs(task.dueDate);
    const hours = taskDateTime.hour();
    const minutes = taskDateTime.minute();
    const startMinutes = hours * 60 + minutes;
    // Default duration: 1 hour
    const endMinutes = startMinutes + 60;

    return {
      task,
      startMinutes,
      endMinutes,
      top: (startMinutes / 14.4), // Convert to percentage
      height: 60 / 14.4 // 1 hour height in percentage
    };
  });

  // Sort by start time, then by end time
  events.sort((a, b) => a.startMinutes - b.startMinutes || a.endMinutes - b.endMinutes);

  // Group overlapping events into columns
  type EventWithBounds = { task: Task; startMinutes: number; endMinutes: number; top: number; height: number };
  const columns: EventWithBounds[][] = [];
  const eventLayouts: EventLayout[] = [];

  events.forEach(event => {
    // Find which column this event fits in
    let placed = false;
    for (let i = 0; i < columns.length; i++) {
      const column = columns[i];
      const lastInColumn = column[column.length - 1];

      // Check if this event overlaps with the last event in this column
      if (event.startMinutes >= lastInColumn.endMinutes) {
        // No overlap, can place in this column
        column.push(event);
        placed = true;
        break;
      }
    }

    if (!placed) {
      // Need a new column
      columns.push([event]);
    }
  });

  // Now assign column positions to each event
  events.forEach(event => {
    // Find which columns this event overlaps with
    const overlappingColumns: number[] = [];
    columns.forEach((column, colIndex) => {
      const overlaps = column.some(e =>
        !(e.endMinutes <= event.startMinutes || e.startMinutes >= event.endMinutes)
      );
      if (overlaps) {
        overlappingColumns.push(colIndex);
      }
    });

    // Find which column this event is actually in
    let myColumn = 0;
    for (let i = 0; i < columns.length; i++) {
      if (columns[i].includes(event)) {
        myColumn = i;
        break;
      }
    }

    const totalColumns = overlappingColumns.length;
    const columnIndex = overlappingColumns.indexOf(myColumn);

    eventLayouts.push({
      task: event.task,
      top: event.top,
      height: event.height,
      column: columnIndex,
      totalColumns: totalColumns
    });
  });

  return eventLayouts;
};

type ViewMode = 'day' | 'week' | 'month';

export const CalendarView = () => {
  const { selectedDate, setSelectedDate, setActiveTab, selectGoal, setChatOpen } = useAppState();
  const { sendMessage } = useChat();
  const [viewMode, setViewMode] = useState<ViewMode>('week');
  const [visibleMonth, setVisibleMonth] = useState(dayjs(selectedDate).startOf('month'));
  const [completedTasks, setCompletedTasks] = useState<Record<string, boolean>>({});
  const [goals, setGoals] = useState<Goal[]>([]);
  const [events, setEvents] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [showAddEventModal, setShowAddEventModal] = useState(false);
  const weekGridRef = useRef<HTMLDivElement>(null);

  // Load goals and events from API
  useEffect(() => {
    loadGoals();
    loadEvents();
  }, []);

  // Auto-scroll to current day in week view
  useEffect(() => {
    if (viewMode === 'week' && weekGridRef.current) {
      // Add delay to ensure DOM is fully rendered
      setTimeout(() => {
        if (!weekGridRef.current) return;

        const today = dayjs();
        const displayedWeekStart = dayjs(selectedDate).startOf('week');

        // Calculate which column index is today (0 = Monday, 6 = Sunday)
        const dayIndex = (today.day() + 6) % 7; // Convert Sunday=0 to Sunday=6

        // Only scroll if we're viewing the current week
        const isCurrentWeek = today.isSame(displayedWeekStart, 'week');

        console.log('[CalendarView] Auto-scroll debug:', {
          today: today.format('YYYY-MM-DD dddd'),
          todayDayOfWeek: today.day(),
          calculatedIndex: dayIndex,
          displayedWeekStart: displayedWeekStart.format('YYYY-MM-DD'),
          isCurrentWeek,
          hasColumns: weekGridRef.current?.children.length,
        });

        if (isCurrentWeek && dayIndex >= 0 && dayIndex < 7) {
          const dayColumns = weekGridRef.current.children;
          console.log('[CalendarView] Scrolling to column', dayIndex, dayColumns[dayIndex]);
          if (dayColumns[dayIndex]) {
            dayColumns[dayIndex].scrollIntoView({
              behavior: 'smooth',
              block: 'nearest',
              inline: 'center'
            });
          }
        }
      }, 300);
    }
  }, [viewMode, selectedDate]);

  const loadEvents = async () => {
    try {
      console.log('[CalendarView] Loading events for user:', apiClient.getUserId());
      const data = await apiClient.getEvents();
      console.log('[CalendarView] Events API response:', data);
      setEvents(data || []);
    } catch (err) {
      console.error('[CalendarView] Failed to load events:', err);
      setEvents([]);
    }
  };

  const loadGoals = async () => {
    try {
      setLoading(true);
      console.log('[CalendarView] Loading goals for user:', apiClient.getUserId());
      const data = await apiClient.getGoals();
      console.log('[CalendarView] Raw API response:', data);

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
          planned_time: s.planned_time,
          linked_event_id: s.linked_event_id
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

  // Convert events to Task format
  const eventTasks = useMemo(() => {
    return events.map((event) => {
      // Find the goal if this event is linked to one
      let goalTitle = 'Событие';
      let goalId = '';

      if (event.event_type === 'goal_step' && event.linked_goal_id) {
        const linkedGoal = goals.find(g => String(g.id) === String(event.linked_goal_id));
        if (linkedGoal) {
          goalTitle = linkedGoal.title;
          goalId = String(linkedGoal.id);
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
        status: 'scheduled' as const,
        focusArea: goalId ? 'Цели' : 'События',
        isEvent: true,
        eventData: event,
        stepId: event.linked_step_id ? String(event.linked_step_id) : undefined
      };
    });
  }, [events, goals]);

  // Extract tasks from goals (steps with planned_date)
  const goalTasks = useMemo(() => extractTasksFromGoals(goals), [goals]);

  // Combine events and goal tasks
  const allTasks = useMemo(() => [...eventTasks, ...goalTasks], [eventTasks, goalTasks]);

  const tasksByDate = useMemo(() => groupTasksByDate(allTasks), [allTasks]);

  const agendaTasks = tasksByDate.get(selectedDate) ?? [];
  const monthDays = generateMonthGrid(visibleMonth);

  const handleTaskAction = async (task: Task, action: 'complete' | 'goal' | 'chat' | 'delete') => {
    const isEvent = (task as any).isEvent;

    if (action === 'complete') {
      if (isEvent) {
        alert('События нельзя отмечать как выполненные');
        return;
      }
      // Toggle step completion status
      const newStatus = completedTasks[task.id] ? 'pending' : 'completed';
      try {
        console.log('[CalendarView] Updating step status:', task.id, newStatus);
        await apiClient.updateStep(task.id, { status: newStatus });
        console.log('[CalendarView] Step status updated successfully');

        // Update local state immediately for better UX
        setCompletedTasks((prev) => ({ ...prev, [task.id]: newStatus === 'completed' }));

        // Update the goals state locally instead of reloading from API
        setGoals((prevGoals) =>
          prevGoals.map(goal => ({
            ...goal,
            steps: goal.steps?.map(step =>
              step.id === task.id ? { ...step, status: newStatus, completed: newStatus === 'completed' } : step
            )
          }))
        );
      } catch (err) {
        console.error('[CalendarView] Failed to toggle step:', err);
        alert('Не удалось обновить задачу');
      }
      return;
    }
    if (action === 'goal') {
      if (isEvent) {
        alert('Это событие, оно не связано с целью');
        return;
      }
      selectGoal(task.goalId);
      setActiveTab('goals');
      return;
    }
    if (action === 'chat') {
      setChatOpen(true);
      void sendMessage(`Что с ${isEvent ? 'событием' : 'задачей'} ${task.title}?`, {
        type: 'task', // Keep as 'task' for now, backend doesn't distinguish
        title: task.title,
        dueDate: task.dueDate
      });
      return;
    }
    if (action === 'delete') {
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
        console.error('[CalendarView] Failed to delete:', err);
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
    }
  };

  // Handle checkbox toggle for tasks/events
  const handleToggleTask = async (task: Task, newStatus: 'done' | 'scheduled') => {
    const isEvent = task.isEvent;
    const isLinkedToGoal = task.stepId && task.goalId;

    console.log('[CalendarView] handleToggleTask called:', {
      taskId: task.id,
      stepId: task.stepId,
      goalId: task.goalId,
      newStatus,
      isEvent,
      isLinkedToGoal
    });

    try {
      // Both events linked to goals and regular goal tasks should update step status
      if (isLinkedToGoal) {
        // Update goal step via API
        const backendStatus = newStatus === 'done' ? 'completed' : 'pending';
        console.log('[CalendarView] Updating step status:', task.stepId, backendStatus);

        await apiClient.updateStep(task.stepId!, { status: backendStatus });
        console.log('[CalendarView] Step status updated successfully');

        // Update local goals state to reflect the change immediately
        setGoals((prevGoals) =>
          prevGoals.map(goal => {
            if (goal.id !== task.goalId) return goal;

            const updatedSteps = goal.steps?.map(step =>
              step.id === task.stepId
                ? { ...step, status: backendStatus, completed: backendStatus === 'completed' }
                : step
            ) || [];

            // Recalculate progress
            const completedSteps = updatedSteps.filter(s => s.completed).length;
            const totalSteps = updatedSteps.length;
            const newProgress = totalSteps > 0 ? Math.round((completedSteps / totalSteps) * 100) : 0;

            console.log('[CalendarView] Updated goal progress:', {
              goalId: goal.id,
              completedSteps,
              totalSteps,
              newProgress
            });

            return {
              ...goal,
              steps: updatedSteps,
              progress: newProgress
            };
          })
        );

        // No need to reload - UI updates via state
      } else if (isEvent) {
        // Standalone event (not linked to a goal) - no completion tracking yet
        console.log('[CalendarView] Standalone event completion not yet supported:', task);
        return;
      }
    } catch (error) {
      console.error('[CalendarView] Failed to toggle task:', error);
      alert('Не удалось обновить задачу');
    }
  };

  // Show loading state until data is loaded
  if (loading) {
    return (
      <div className={styles.calendarPage}>
        <div className="card" style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          minHeight: '400px'
        }}>
          <div style={{ textAlign: 'center' }}>
            <Typography.Title variant="large-strong">Загрузка...</Typography.Title>
            <Typography.Body variant="medium" style={{ marginTop: '12px', color: 'var(--text-secondary)' }}>
              Подгружаем события и задачи
            </Typography.Body>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.calendarPage}>
      {/* View Mode Selector */}
      <div className={styles.viewModeSelector}>
        <button
          className={clsx(styles.viewModeButton, viewMode === 'day' && styles.active)}
          onClick={() => setViewMode('day')}
        >
          День
        </button>
        <button
          className={clsx(styles.viewModeButton, viewMode === 'week' && styles.active)}
          onClick={() => setViewMode('week')}
        >
          Неделя
        </button>
        <button
          className={clsx(styles.viewModeButton, viewMode === 'month' && styles.active)}
          onClick={() => setViewMode('month')}
        >
          Месяц
        </button>
      </div>

      {/* Day View - Timeline for today only */}
      {viewMode === 'day' && (
        <div className="card">
          <div className={styles.dayViewContainer}>
            <div className={styles.dayHeader}>
              <IconButton
                mode='tertiary'
                appearance='neutral'
                aria-label="Предыдущий день"
                onClick={() => setSelectedDate(dayjs(selectedDate).subtract(1, 'day').format('YYYY-MM-DD'))}
              >
                ‹
              </IconButton>
              <Typography.Title variant="medium-strong">
                {dayjs(selectedDate).format('dddd, DD MMMM')}
              </Typography.Title>
              <IconButton
                mode='tertiary'
                appearance='neutral'
                aria-label="Следующий день"
                onClick={() => setSelectedDate(dayjs(selectedDate).add(1, 'day').format('YYYY-MM-DD'))}
              >
                ›
              </IconButton>
            </div>
            <div className={styles.timelineContainer}>
              <div className={styles.timeColumn}>
                {Array.from({ length: 24 }, (_, hour) => (
                  <div key={hour} className={styles.hourSlot}>
                    <span className={styles.hourLabel}>{hour.toString().padStart(2, '0')}:00</span>
                  </div>
                ))}
              </div>
              <div className={styles.eventsColumn}>
                {/* Current time indicator line - only show if viewing today */}
                {dayjs(selectedDate).isSame(dayjs(), 'day') && (
                  <div
                    className={styles.currentTimeLine}
                    style={{ top: `${(dayjs().hour() * 60 + dayjs().minute()) / 14.4}%` }}
                  />
                )}
                {/* Day's events positioned on timeline with column layout for overlaps */}
                {(() => {
                  const eventLayouts = calculateEventLayout(agendaTasks);
                  return eventLayouts.map(({ task, top, height, column, totalColumns }) => {
                    const taskDateTime = dayjs(task.dueDate);
                    const taskTime = taskDateTime.format('HH:mm');

                    // Calculate width and left position based on columns
                    const widthPercent = totalColumns > 1 ? (100 / totalColumns) : 100;
                    const leftPercent = totalColumns > 1 ? (column * widthPercent) : 0;

                    return (
                      <div
                        key={task.id}
                        className={styles.dayEventCard}
                        style={{
                          top: `${top}%`,
                          height: `${height}%`,
                          left: `${leftPercent}%`,
                          width: `${widthPercent}%`
                        }}
                        onClick={() => handleTaskAction(task, 'goal')}
                      >
                        <div className={styles.dayEventHeader}>
                          <div className={styles.dayEventTime}>{taskTime}</div>
                        </div>
                        <div className={styles.dayEventTitle}>{task.title}</div>
                      </div>
                    );
                  });
                })()}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Week View - Event cards for 7 days */}
      {viewMode === 'week' && (
        <div className="card">
          <div className={styles.weekHeader}>
            <IconButton
              mode='tertiary'
              appearance='neutral'
              aria-label="Предыдущая неделя"
              onClick={() => setSelectedDate(dayjs(selectedDate).subtract(7, 'day').format('YYYY-MM-DD'))}
            >
              ‹
            </IconButton>
            <Typography.Title variant="medium-strong">
              {dayjs(selectedDate).startOf('week').format('DD MMM')} - {dayjs(selectedDate).endOf('week').format('DD MMM')}
            </Typography.Title>
            <IconButton
              mode='tertiary'
              appearance='neutral'
              aria-label="Следующая неделя"
              onClick={() => setSelectedDate(dayjs(selectedDate).add(7, 'day').format('YYYY-MM-DD'))}
            >
              ›
            </IconButton>
          </div>
          <div className={styles.weekGrid} ref={weekGridRef}>
            {Array.from({ length: 7 }, (_, i) => {
              const day = dayjs(selectedDate).startOf('week').add(i, 'day');
              const dayKey = day.format('YYYY-MM-DD');
              const dayTasks = tasksByDate.get(dayKey) ?? [];
              const isToday = day.isSame(dayjs(), 'day');
              const isSelectedDay = dayKey === selectedDate;

              return (
                <div
                  key={dayKey}
                  className={clsx(
                    styles.weekDayColumn,
                    isToday && styles.todayColumn,
                    isSelectedDay && styles.selectedColumn
                  )}
                  onClick={() => setSelectedDate(dayKey)}
                >
                  <div className={styles.weekDayHeader}>
                    <span className={styles.weekDayName}>{day.format('ddd')}</span>
                    <span className={clsx(styles.weekDayNumber, isToday && styles.todayNumber)}>
                      {day.format('D')}
                    </span>
                  </div>
                  <div className={styles.weekDayEvents}>
                    {dayTasks.length === 0 ? (
                      <div className={styles.noEvents}>—</div>
                    ) : (
                      dayTasks.map((task) => (
                        <div
                          key={task.id}
                          className={styles.weekEventCard}
                          onClick={(e) => {
                            e.stopPropagation();
                            handleTaskAction(task, 'goal');
                          }}
                        >
                          <div className={styles.weekEventHeader}>
                            <div className={styles.weekEventTime}>
                              {dayjs(task.dueDate).format('HH:mm')}
                            </div>
                          </div>
                          <div className={styles.weekEventTitle}>
                            {task.title.length > 30 ? `${task.title.slice(0, 30)}...` : task.title}
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Month View - Grid with event indicators */}
      {viewMode === 'month' && (
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
              const dayTasks = tasksByDate.get(key) || [];
              const hasAgenda = dayTasks.length > 0;
              const isToday = day.isSame(dayjs(), 'day');
              return (
                <button
                  key={key}
                  type="button"
                  className={clsx(
                    styles.dayCell,
                    !isCurrentMonth && styles.dimmed,
                    isSelected && styles.active,
                    isToday && styles.today,
                    hasAgenda && styles.hasEvents
                  )}
                  onClick={() => {
                    setSelectedDate(key);
                    setVisibleMonth(day.startOf('month'));
                  }}
                >
                  <span className={styles.dayCellNumber}>{day.format('D')}</span>
                  {hasAgenda && (
                    <div className={styles.eventIndicators}>
                      {dayTasks.slice(0, 3).map((task, idx) => (
                        <span key={task.id} className={styles.eventDot} />
                      ))}
                      {dayTasks.length > 3 && (
                        <span className={styles.eventCount}>+{dayTasks.length - 3}</span>
                      )}
                    </div>
                  )}
                </button>
              );
            })}
          </div>
        </div>
      )}

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
              <div className={styles.agendaCheckboxContainer}>
                <TaskCheckbox task={task} onToggle={handleToggleTask} />
              </div>
              <div className={styles.agendaContent}>
                <Typography.Title variant="small-strong">{task.title}</Typography.Title>
                <Typography.Body variant="small" className={styles.agendaMeta}>
                  Цель: {task.goalTitle}
                </Typography.Body>
              </div>
              <div className={styles.agendaActions}>
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
          onSuccess={() => loadEvents()}
          selectedDate={selectedDate}
        />
      )}
    </div>
  );
};
