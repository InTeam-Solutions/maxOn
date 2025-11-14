import type { Goal } from '../types/domain';

const CORE_API_URL = import.meta.env.VITE_CORE_API_URL || 'http://localhost:8104';
const ORCHESTRATOR_API_URL = import.meta.env.VITE_ORCHESTRATOR_API_URL || 'http://localhost:8101';

interface ApiConfig {
  userId: string;
  baseUrl?: string;
}

class ApiClient {
  private userId: string = '';
  private coreUrl: string = CORE_API_URL;
  private orchestratorUrl: string = ORCHESTRATOR_API_URL;

  configure(config: ApiConfig) {
    this.userId = config.userId;
    if (config.baseUrl) {
      this.coreUrl = config.baseUrl;
    }
  }

  getUserId(): string {
    return this.userId;
  }

  private async request<T>(
    url: string,
    options: RequestInit = {}
  ): Promise<T> {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }

    return response.json();
  }

  // ==================== Goals API ====================

  async getGoals(): Promise<Goal[]> {
    return this.request<Goal[]>(
      `${this.coreUrl}/api/goals?user_id=${this.userId}`
    );
  }

  async getGoal(goalId: string): Promise<Goal> {
    return this.request<Goal>(
      `${this.coreUrl}/api/goals/${goalId}?user_id=${this.userId}`
    );
  }

  async createGoal(data: {
    title: string;
    description?: string;
    target_date?: string;
    category?: string;
    priority?: string;
    status?: string;
  }): Promise<Goal> {
    return this.request<Goal>(`${this.coreUrl}/api/goals?user_id=${this.userId}`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateGoal(
    goalId: string,
    data: Partial<{
      title: string;
      description: string;
      target_date: string;
      status: string;
    }>
  ): Promise<Goal> {
    return this.request<Goal>(
      `${this.coreUrl}/api/goals/${goalId}?user_id=${this.userId}`,
      {
        method: 'PATCH',
        body: JSON.stringify(data),
      }
    );
  }

  async deleteGoal(goalId: string): Promise<void> {
    await this.request<void>(
      `${this.coreUrl}/api/goals/${goalId}?user_id=${this.userId}`,
      {
        method: 'DELETE',
      }
    );
  }

  // ==================== Steps API ====================

  async createStep(data: {
    goal_id: number;
    title: string;
    order?: number;
    planned_date?: string;
    planned_time?: string;
    status?: string;
  }): Promise<any> {
    const goalId = data.goal_id;
    // Get max order from existing steps for this goal
    const goal = await this.getGoal(String(goalId));
    const maxOrder = goal.steps?.length ? Math.max(...goal.steps.map((s: any) => s.order || 0)) : 0;

    return this.request<any>(`${this.coreUrl}/api/goals/${goalId}/steps?user_id=${this.userId}`, {
      method: 'POST',
      body: JSON.stringify({
        ...data,
        order: data.order ?? (maxOrder + 1)
      }),
    });
  }

  async updateStep(
    stepId: string,
    data: { status?: string; title?: string }
  ): Promise<any> {
    return this.request<any>(
      `${this.coreUrl}/api/steps/${stepId}?user_id=${this.userId}`,
      {
        method: 'PUT',
        body: JSON.stringify(data),
      }
    );
  }

  async deleteStep(stepId: string): Promise<void> {
    await this.request<void>(
      `${this.coreUrl}/api/steps/${stepId}?user_id=${this.userId}`,
      {
        method: 'DELETE',
      }
    );
  }

  // ==================== Events API ====================

  async getEvents(params?: {
    start_date?: string;
    end_date?: string;
  }): Promise<any[]> {
    const queryParams = new URLSearchParams({
      user_id: this.userId,
      ...(params?.start_date && { start_date: params.start_date }),
      ...(params?.end_date && { end_date: params.end_date }),
    });

    return this.request<any[]>(
      `${this.coreUrl}/api/events?${queryParams.toString()}`
    );
  }

  async createEvent(data: {
    title: string;
    date: string;
    time?: string;
    description?: string;
    notes?: string;
  }): Promise<any> {
    return this.request<any>(`${this.coreUrl}/api/events?user_id=${this.userId}`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // ==================== Orchestrator API (Chat) ====================

  async resetChatState(): Promise<void> {
    try {
      await this.request<any>(`${this.orchestratorUrl}/api/reset-state?user_id=${this.userId}`, {
        method: 'POST',
      });
    } catch (error) {
      // Silently ignore - endpoint may not exist, not critical
    }
  }

  async sendMessage(message: string, context?: any): Promise<any> {
    return this.request<any>(`${this.orchestratorUrl}/api/process`, {
      method: 'POST',
      body: JSON.stringify({
        user_id: this.userId,
        message,
        context,
      }),
    });
  }

  async sendCallback(callback_data: string): Promise<any> {
    return this.request<any>(`${this.orchestratorUrl}/api/callback`, {
      method: 'POST',
      body: JSON.stringify({
        user_id: this.userId,
        callback_data,
      }),
    });
  }

  // ==================== User Profile ====================

  async getUserProfile(): Promise<any> {
    // This would typically come from context service
    return {
      user_id: this.userId,
      timezone: 'Europe/Moscow',
    };
  }
}

export const apiClient = new ApiClient();
export type { ApiConfig };
