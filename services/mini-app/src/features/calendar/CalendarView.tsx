import { useMemo, useState } from 'react';
import dayjs, { Dayjs } from 'dayjs';
import { IconButton, Button, Typography } from '@maxhub/max-ui';
import clsx from 'clsx';
import { useAppState } from '../../store/AppStateContext';
import { useChat } from '../../store/ChatContext';
import { mockTasks } from '../../mocks/data';
import type { Task } from '../../types/domain';
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

  const tasksByDate = useMemo(() => {
    const map = new Map<string, Task[]>();
    mockTasks.forEach((task) => {
      const key = dayjs(task.dueDate).format('YYYY-MM-DD');
      const existing = map.get(key) ?? [];
      existing.push(task);
      map.set(key, existing);
    });
    return map;
  }, []);

  const agendaTasks = tasksByDate.get(selectedDate) ?? [];
  const monthDays = generateMonthGrid(visibleMonth);

  const handleTaskAction = (task: Task, action: 'complete' | 'goal' | 'chat') => {
    if (action === 'complete') {
      setCompletedTasks((prev) => ({ ...prev, [task.id]: !prev[task.id] }));
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
          Повестка дня
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
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
};
