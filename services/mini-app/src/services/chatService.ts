import dayjs from 'dayjs';
import type { ChatAttachment, ChatMessage } from '../types/domain';
import { generateId } from '../utils/id';
import { apiClient } from './api';

export interface ChatContextPayload {
  type: 'goal' | 'task' | 'general';
  title?: string;
  description?: string;
  dueDate?: string;
  progress?: number;
}

const USE_REAL_API = import.meta.env.VITE_USE_REAL_API?.trim() === 'true';

// Debug logging
console.log('[chatService] Environment:', {
  VITE_USE_REAL_API: import.meta.env.VITE_USE_REAL_API,
  VITE_USE_REAL_API_TRIMMED: import.meta.env.VITE_USE_REAL_API?.trim(),
  USE_REAL_API,
  ORCHESTRATOR_URL: import.meta.env.VITE_ORCHESTRATOR_API_URL
});

// Fallback responses for mock mode
const BOT_RESPONSES = [
  'Я рядом — могу подсказать следующий шаг или собрать краткий план.',
  'Зафиксировала. Хочешь добавить это в цель или отправить в напоминания?',
  'Звучит мощно! Давай разобьём это на шаги и распределим по дням.',
  'Готово. Ещё помочь с чем-то из ближайших задач?'
];

const formatContextFragment = (context?: ChatContextPayload) => {
  if (!context || context.type === 'general') return '';
  if (context.type === 'goal') {
    return `Про цель «${context.title ?? 'без названия'}» вижу прогресс ${context.progress ?? 0}%`;
  }
  return `В повестке есть задача «${context.title ?? 'новая задача'}» до ${context.dueDate ? dayjs(context.dueDate).format('DD MMM HH:mm') : 'неизвестно'}`;
};

const buildAttachments = (context?: ChatContextPayload): ChatAttachment[] | undefined => {
  if (!context || context.type === 'general') return undefined;
  if (context.type === 'goal') {
    return [
      {
        type: 'goal',
        payload: {
          id: generateId(),
          title: context.title ?? 'Цель без названия',
          description: context.description ?? 'Обсуждаем сессию с maxOn',
          progress: context.progress ?? 0
        }
      }
    ];
  }
  return [
    {
      type: 'task',
      payload: {
        id: generateId(),
        title: context.title ?? 'Задача без названия',
        goalTitle: 'Связанная цель',
        dueDate: context.dueDate ?? dayjs().toISOString(),
        status: 'scheduled'
      }
    }
  ];
};

// Mock mode response
async function sendMockMessage(
  text: string,
  context?: ChatContextPayload
): Promise<ChatMessage> {
  const delay = 600 + Math.random() * 900;
  await new Promise((resolve) => setTimeout(resolve, delay));

  const contextFragment = formatContextFragment(context);
  const answer =
    (contextFragment ? `${contextFragment}. ` : '') +
    BOT_RESPONSES[Math.floor(Math.random() * BOT_RESPONSES.length)];

  return {
    id: `bot-${generateId()}`,
    author: 'maxon',
    text: answer,
    timestamp: dayjs().toISOString(),
    attachments: buildAttachments(context)
  };
}

// Real API mode response
async function sendRealMessage(
  text: string,
  context?: ChatContextPayload
): Promise<ChatMessage> {
  try {
    const response = await apiClient.sendMessage(text, context);

    // Parse orchestrator response
    // Response format: { success, response_type, text, items, set_id, buttons, error? }
    let responseText = 'Понял вас!';

    if (response.text) {
      responseText = response.text;
    } else if (response.response) {
      responseText = response.response;
    }

    // Log for debugging
    console.log('[chatService] Orchestrator response:', response);

    return {
      id: `bot-${generateId()}`,
      author: 'maxon',
      text: responseText,
      timestamp: dayjs().toISOString(),
      attachments: response.attachments || buildAttachments(context),
      buttons: response.buttons || undefined,
      isHtml: true // Orchestrator returns HTML formatted text
    };
  } catch (error) {
    console.error('[chatService] Failed to send message to API:', error);

    // Return a user-friendly error message instead of falling back to mock
    return {
      id: `bot-${generateId()}`,
      author: 'maxon',
      text: 'Извини, сейчас у меня проблемы с обработкой запроса. Попробуй написать в бота @t623_hakaton_bot или повтори позже.',
      timestamp: dayjs().toISOString(),
      isHtml: false
    };
  }
}

export const chatService = {
  async sendMessageToBot(
    text: string,
    context?: ChatContextPayload
  ): Promise<ChatMessage> {
    console.log('[chatService] sendMessageToBot called, USE_REAL_API:', USE_REAL_API);
    if (USE_REAL_API) {
      console.log('[chatService] Using REAL API');
      return sendRealMessage(text, context);
    }
    console.log('[chatService] Using MOCK API');
    return sendMockMessage(text, context);
  }
};
