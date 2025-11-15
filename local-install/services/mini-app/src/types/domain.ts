export type TaskStatus = 'scheduled' | 'in-progress' | 'done';

export interface GoalStep {
  id: string;
  title: string;
  completed: boolean;
  status?: string; // Backend status: 'pending' | 'in_progress' | 'completed'
  linked_event_id?: number | null; // Link to calendar event if step is scheduled
  planned_date?: string | null; // When this step is scheduled (YYYY-MM-DD)
  planned_time?: string | null; // Time of day for this step (HH:MM:SS)
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
  isEvent?: boolean; // True if this is a standalone event (not a goal step)
  isDeadline?: boolean; // True if this is a goal deadline (target_date)
  eventData?: any; // Original event data if isEvent=true
  stepId?: string; // ID of the related goal step if this is a goal task
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
  requiresAction?: boolean;
  showScheduleSelector?: boolean; // Shows the week schedule selector widget
  scheduleContext?: {
    goalTitle?: string;
    goalId?: string;
  };
}

