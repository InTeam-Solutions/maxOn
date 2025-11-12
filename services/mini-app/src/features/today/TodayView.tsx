import { useMemo, useState } from 'react';
import dayjs from 'dayjs';
import { Button, Input, Typography } from '@maxhub/max-ui';
import { TaskCard } from '../../components/TaskCard';
import { SectionHeading } from '../../components/SectionHeading';
import { useAppState } from '../../store/AppStateContext';
import { useChat } from '../../store/ChatContext';
import { mockTasks, todaySummary } from '../../mocks/data';
import styles from './TodayView.module.css';

const buildMiniCalendar = (date: string) => {
  const center = dayjs(date);
  const start = center.subtract(3, 'day');
  return Array.from({ length: 7 }, (_, index) => start.add(index, 'day'));
};

export const TodayView = () => {
  const { setActiveTab, selectGoal, selectedDate, setSelectedDate, setChatOpen } = useAppState();
  const { sendMessage } = useChat();
  const [prompt, setPrompt] = useState('');

  const tasksToday = useMemo(
    () => mockTasks.filter((task) => dayjs(task.dueDate).isSame(dayjs(), 'day')),
    []
  );

  const nextThreeDays = useMemo(
    () =>
      mockTasks.filter((task) => {
        const diff = dayjs(task.dueDate).startOf('day').diff(dayjs().startOf('day'), 'day');
        return diff > 0 && diff <= 3;
      }),
    []
  );

  const calendarDays = buildMiniCalendar(selectedDate);
  const tasksByDay = useMemo(() => {
    const collection = new Map<string, number>();
    mockTasks.forEach((task) => {
      const key = dayjs(task.dueDate).format('YYYY-MM-DD');
      collection.set(key, (collection.get(key) ?? 0) + 1);
    });
    return collection;
  }, []);

  const handleTaskClick = (goalId: string) => {
    selectGoal(goalId);
    setActiveTab('goals');
  };

  const handlePromptSubmit = async () => {
    if (!prompt.trim()) return;
    setChatOpen(true);
    await sendMessage(prompt, { type: 'general' });
    setPrompt('');
  };

  return (
    <div className={styles.today}>
      <div className="card">
        <div className={styles.headerRow}>
          <div className={styles.headingGroup}>
            <Typography.Title variant="large-strong" className={styles.title}>
              Главная
            </Typography.Title>
            <Typography.Body variant="medium" className={styles.subtitle}>
              {todaySummary.activeGoals} активные цели · {todaySummary.stepsToday} шагов на сегодня
            </Typography.Body>
          </div>
          <span className={styles.fireEmoji}>🔥</span>
        </div>
        <div className={styles.miniCalendar}>
          {calendarDays.map((day) => {
            const key = day.format('YYYY-MM-DD');
            const isActive = key === selectedDate;
            const hasTasks = tasksByDay.get(key);
            return (
              <button
                key={key}
                type="button"
                className={`${styles.calendarDay} ${isActive ? styles.active : ''}`}
                onClick={() => setSelectedDate(key)}
              >
                <span className={styles.calendarWeekday}>{day.format('dd')}</span>
                <span className={styles.calendarDate}>{day.format('D')}</span>
                {hasTasks ? <span className={styles.calendarDot} /> : null}
              </button>
            );
          })}
        </div>
      </div>

      <section>
        <SectionHeading title="Сегодня позже" subtitle="Что осталось закрыть" />
        <div className={styles.list}>
          {tasksToday.map((task) => (
            <TaskCard key={task.id} task={task} onClick={() => handleTaskClick(task.goalId)} />
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
              onClick={() => handleTaskClick(task.goalId)}
            />
          ))}
        </div>
      </section>

      <div className={styles.actionsRow}>
        <Button
          mode="primary"
          appearance="themed"
          className={styles.gradientButton}
          onClick={() => setActiveTab('goals')}
        >
          + Цель
        </Button>
      </div>

      <div className={styles.promptBox}>
        <Input
          placeholder="Сформулируй цель или спроси maxOn…"
          value={prompt}
          onChange={(event) => setPrompt(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter') {
              handlePromptSubmit();
            }
          }}
        />
        <Button
          mode="secondary"
          appearance="neutral-themed"
          onClick={handlePromptSubmit}
          disabled={!prompt.trim()}
        >
          Отправить
        </Button>
      </div>
    </div>
  );
};
