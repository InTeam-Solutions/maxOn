export type TaskStatus = 'scheduled' | 'in-progress' | 'done';

export interface GoalStep {
  id: string;
  title: string;
  completed: boolean;
}

export interface Goal {
  id: string;
  title: string;
  description: string;
  targetDate: string;
  progress: number;
  category: string;
  priority: 'low' | 'medium' | 'high';
  status: 'active' | 'paused' | 'completed';
  steps: GoalStep[];
}

export interface Task {
  id: string;
  title: string;
  goalId: string;
  goalTitle: string;
  dueDate: string;
  status: TaskStatus;
  focusArea: string;
}

export interface LeaderboardEntry {
  id: string;
  name: string;
  username: string;
  streakDays: number;
  avatarColor: string;
  delta: number;
}

export type ChatAttachment =
  | {
      type: 'task';
      payload: Pick<Task, 'id' | 'title' | 'goalTitle' | 'dueDate' | 'status'>;
    }
  | {
      type: 'goal';
      payload: Pick<Goal, 'id' | 'title' | 'description' | 'progress'>;
    };

export interface ChatButton {
  text: string;
  callback_data: string;
  data?: any;
}

export interface ChatMessage {
  id: string;
  author: 'user' | 'maxon';
  text: string;
  timestamp: string;
  attachments?: ChatAttachment[];
  buttons?: ChatButton[][];
  isHtml?: boolean;
}

