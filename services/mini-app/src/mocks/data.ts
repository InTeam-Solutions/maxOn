import dayjs from 'dayjs';
import type { Goal, LeaderboardEntry, Task } from '../types/domain';

const today = dayjs();

export const mockGoals: Goal[] = [
  {
    id: 'goal-1',
    title: 'Подготовить резюме под junior frontend',
    description: 'Обновить портфолио, собрать ключевые проекты и сопроводительное письмо.',
    targetDate: today.add(7, 'day').toISOString(),
    progress: 62,
    category: 'Карьера',
    priority: 'high',
    status: 'active',
    steps: [
      { id: 'goal-1-step-1', title: 'Переписать summary', completed: true },
      { id: 'goal-1-step-2', title: 'Обновить блок проектов', completed: false },
      { id: 'goal-1-step-3', title: 'Заказать ревью у наставника', completed: false }
    ]
  },
  {
    id: 'goal-2',
    title: 'Подготовиться к экзамену по ML',
    description: 'Повторить теорию, решить три пробных варианта, наметить план на экзаменационную неделю.',
    targetDate: today.add(12, 'day').toISOString(),
    progress: 48,
    category: 'Обучение',
    priority: 'medium',
    status: 'active',
    steps: [
      { id: 'goal-2-step-1', title: 'Пересмотреть конспекты', completed: true },
      { id: 'goal-2-step-2', title: 'Решить пробный вариант', completed: false },
      { id: 'goal-2-step-3', title: 'Собрать вопросы к преподавателю', completed: false }
    ]
  },
  {
    id: 'goal-3',
    title: 'Регулярные тренировки',
    description: 'Вернуться к режиму 3 тренировок в неделю и отслеживать прогресс.',
    targetDate: today.add(21, 'day').toISOString(),
    progress: 35,
    category: 'Здоровье',
    priority: 'medium',
    status: 'active',
    steps: [
      { id: 'goal-3-step-1', title: 'Составить микро-мезо план', completed: false },
      { id: 'goal-3-step-2', title: 'Забронировать тренировки', completed: false },
      { id: 'goal-3-step-3', title: 'Отметить первые результаты', completed: false }
    ]
  }
];

export const mockTasks: Task[] = [
  {
    id: 'task-1',
    title: 'Собрать подборку вакансий',
    goalId: 'goal-1',
    goalTitle: 'Найти первую работу',
    dueDate: today.hour(10).minute(0).toISOString(),
    status: 'in-progress',
    focusArea: 'Карьера'
  },
  {
    id: 'task-2',
    title: 'Подготовить презентацию проекта',
    goalId: 'goal-1',
    goalTitle: 'Найти первую работу',
    dueDate: today.add(1, 'day').hour(19).toISOString(),
    status: 'scheduled',
    focusArea: 'Карьера'
  },
  {
    id: 'task-3',
    title: 'Пройти тест по вероятности',
    goalId: 'goal-2',
    goalTitle: 'Закончить курс',
    dueDate: today.add(2, 'day').hour(12).toISOString(),
    status: 'scheduled',
    focusArea: 'Обучение'
  },
  {
    id: 'task-4',
    title: 'Вечерняя тренировка',
    goalId: 'goal-3',
    goalTitle: 'Регулярные тренировки',
    dueDate: today.add(3, 'day').hour(20).toISOString(),
    status: 'scheduled',
    focusArea: 'Здоровье'
  },
  {
    id: 'task-5',
    title: 'Созвон с ментором',
    goalId: 'goal-1',
    goalTitle: 'Найти первую работу',
    dueDate: today.subtract(1, 'day').hour(18).toISOString(),
    status: 'done',
    focusArea: 'Карьера'
  }
];

export const leaderboardMock: LeaderboardEntry[] = [
  { id: 'lead-1', name: 'Аня', username: '@anya', streakDays: 21, avatarColor: '#2563ff', delta: 2 },
  { id: 'lead-2', name: 'Марк', username: '@mark', streakDays: 18, avatarColor: '#8b5cff', delta: 1 },
  { id: 'lead-3', name: 'Вика', username: '@vika', streakDays: 16, avatarColor: '#21a038', delta: 0 },
  { id: 'lead-4', name: 'Роберт', username: '@robert', streakDays: 13, avatarColor: '#f9a826', delta: -1 },
  { id: 'lead-5', name: 'Артём', username: '@artem', streakDays: 9, avatarColor: '#f87171', delta: 3 }
];

export const todaySummary = {
  activeGoals: mockGoals.filter((goal) => goal.status === 'active').length,
  stepsToday: 7
};

