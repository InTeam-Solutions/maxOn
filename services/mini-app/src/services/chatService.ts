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

const USE_REAL_API = import.meta.env.VITE_USE_REAL_API === 'true';

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
    const responseText = response.text || response.response || 'Понял вас!';

    return {
      id: `bot-${generateId()}`,
      author: 'maxon',
      text: responseText,
      timestamp: dayjs().toISOString(),
      attachments: response.attachments || buildAttachments(context)
    };
  } catch (error) {
    console.error('Failed to send message to API:', error);
    // Fallback to mock mode on error
    return sendMockMessage(text, context);
  }
}

export const chatService = {
  async sendMessageToBot(
    text: string,
    context?: ChatContextPayload
  ): Promise<ChatMessage> {
    if (USE_REAL_API) {
      return sendRealMessage(text, context);
    }
    return sendMockMessage(text, context);
  }
};
