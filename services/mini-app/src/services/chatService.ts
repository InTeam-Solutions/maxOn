import dayjs from 'dayjs';
import type { ChatAttachment, ChatMessage } from '../types/domain';
import { generateId } from '../utils/id';

export interface ChatContextPayload {
  type: 'goal' | 'task' | 'general';
  title?: string;
  description?: string;
  dueDate?: string;
  progress?: number;
}

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

export const chatService = {
  async sendMessageToBot(
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
};
