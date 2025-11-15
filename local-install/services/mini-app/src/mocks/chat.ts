import dayjs from 'dayjs';
import type { ChatMessage } from '../types/domain';

export const initialChatMessages: ChatMessage[] = [
  {
    id: 'msg-1',
    author: 'maxon',
    text: 'Привет! Чем могу помочь сегодня?',
    timestamp: dayjs().subtract(20, 'minute').toISOString()
  },
  {
    id: 'msg-2',
    author: 'user',
    text: 'Покажи, что по шагам на сегодня?',
    timestamp: dayjs().subtract(19, 'minute').toISOString()
  },
  {
    id: 'msg-3',
    author: 'maxon',
    text: 'У тебя 3 цели в работе и 7 шагов в повестке. Могу подсветить ближайшие задачи или помочь разбить большую цель.',
    timestamp: dayjs().subtract(18, 'minute').toISOString()
  }
];

