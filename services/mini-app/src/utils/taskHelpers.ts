import dayjs from 'dayjs';
import type { Goal, Task, TaskStatus } from '../types/domain';

/**
 * Converts backend Step data to frontend Task format
 */
export function stepToTask(
  step: any,
  goal: Goal
): Task | null {
  // Only convert steps that have a planned_date
  if (!step.planned_date) {
    return null;
  }

  // Combine planned_date and planned_time into dueDate
  const date = step.planned_date;
  const time = step.planned_time || '00:00:00';
  const dueDate = dayjs(`${date}T${time}`).toISOString();

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
    focusArea: goal.category || 'Общее'
  };
}

/**
 * Extracts all tasks from goals (steps with planned_date)
 */
export function extractTasksFromGoals(goals: Goal[]): Task[] {
  const tasks: Task[] = [];

  for (const goal of goals) {
    if (!goal.steps) continue;

    for (const step of goal.steps) {
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
  return tasks.filter(task =>
    dayjs(task.dueDate).isSame(dayjs(), 'day')
  );
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
