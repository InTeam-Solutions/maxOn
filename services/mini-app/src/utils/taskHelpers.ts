import dayjs from 'dayjs';
import type { Goal, Task, TaskStatus } from '../types/domain';

/**
 * Converts backend Step data to frontend Task format
 */
export function stepToTask(
  step: any,
  goal: Goal
): Task | null {
  // Convert steps with planned_date OR without (treat null as "today without time")
  let dueDate: string;

  if (step.planned_date) {
    // Has date - combine with time
    const date = step.planned_date;
    const time = step.planned_time || '00:00:00';
    console.log('[stepToTask] Converting step with date:', { step, date, time });
    dueDate = dayjs(`${date}T${time}`).toISOString();
  } else {
    // No date - use today with special marker
    console.log('[stepToTask] Converting step WITHOUT date (showing as today):', step);
    dueDate = dayjs().toISOString();
  }

  // Map backend status to frontend TaskStatus
  const statusMap: Record<string, TaskStatus> = {
    'pending': 'scheduled',
    'in_progress': 'in-progress',
    'completed': 'done'
  };

  return {
    id: String(step.id),
    title: step.title,
    goalId: String(goal.id),
    goalTitle: goal.title,
    dueDate,
    status: statusMap[step.status] || 'scheduled',
    focusArea: goal.category || 'Общее',
    hasNoTime: !step.planned_date  // Flag to show "без времени"
  } as any;
}

/**
 * Extracts all tasks from goals (steps with planned_date)
 * Excludes steps that are already linked to calendar events (to avoid duplicates)
 */
export function extractTasksFromGoals(goals: Goal[]): Task[] {
  const tasks: Task[] = [];

  for (const goal of goals) {
    if (!goal.steps) continue;

    for (const step of goal.steps) {
      // Skip steps that are already linked to events
      if (step.linked_event_id) {
        console.log('[extractTasksFromGoals] Skipping step linked to event:', {
          stepId: step.id,
          stepTitle: step.title,
          linkedEventId: step.linked_event_id
        });
        continue;
      }

      const task = stepToTask(step, goal);
      if (task) {
        tasks.push(task);
      }
    }
  }

  return tasks;
}

/**
 * Filters tasks for today
 */
export function getTodayTasks(tasks: Task[]): Task[] {
  const today = dayjs().format('YYYY-MM-DD');
  console.log('[getTodayTasks] Today is:', today);
  console.log('[getTodayTasks] All tasks:', tasks.map(t => ({
    title: t.title,
    dueDate: t.dueDate,
    dueDateFormatted: dayjs(t.dueDate).format('YYYY-MM-DD')
  })));

  return tasks.filter(task => {
    const isSame = dayjs(task.dueDate).isSame(dayjs(), 'day');
    console.log(`[getTodayTasks] Task "${task.title}" on ${dayjs(task.dueDate).format('YYYY-MM-DD')} is today? ${isSame}`);
    return isSame;
  });
}

/**
 * Filters tasks for next N days (excluding today)
 */
export function getUpcomingTasks(tasks: Task[], days: number = 3): Task[] {
  const now = dayjs();
  return tasks.filter(task => {
    const taskDate = dayjs(task.dueDate);
    const diff = taskDate.startOf('day').diff(now.startOf('day'), 'day');
    return diff > 0 && diff <= days;
  });
}

/**
 * Groups tasks by date (YYYY-MM-DD format)
 */
export function groupTasksByDate(tasks: Task[]): Map<string, Task[]> {
  const map = new Map<string, Task[]>();

  for (const task of tasks) {
    const key = dayjs(task.dueDate).format('YYYY-MM-DD');
    const existing = map.get(key) || [];
    existing.push(task);
    map.set(key, existing);
  }

  return map;
}

/**
 * Counts tasks per date
 */
export function countTasksByDate(tasks: Task[]): Map<string, number> {
  const map = new Map<string, number>();

  for (const task of tasks) {
    const key = dayjs(task.dueDate).format('YYYY-MM-DD');
    map.set(key, (map.get(key) || 0) + 1);
  }

  return map;
}
