import { createContext, useContext, useMemo, useState, type ReactNode } from 'react';
import type { ChatMessage } from '../types/domain';
import { initialChatMessages } from '../mocks/chat';
import { chatService, type ChatContextPayload } from '../services/chatService';
import { generateId } from '../utils/id';

interface ChatContextValue {
  messages: ChatMessage[];
  isSending: boolean;
  sendMessage: (text: string, context?: ChatContextPayload) => Promise<void>;
  resetChat: () => void;
}

const ChatContext = createContext<ChatContextValue | null>(null);

export const ChatProvider = ({ children }: { children: ReactNode }) => {
  const [messages, setMessages] = useState<ChatMessage[]>(initialChatMessages);
  const [isSending, setIsSending] = useState(false);

  const sendMessage = async (text: string, context?: ChatContextPayload) => {
    const trimmed = text.trim();
    if (!trimmed) return;

    const userMessage: ChatMessage = {
      id: `user-${generateId()}`,
      author: 'user',
      text: trimmed,
      timestamp: new Date().toISOString()
    };
    setMessages((prev) => [...prev, userMessage]);
    setIsSending(true);
    try {
      const reply = await chatService.sendMessageToBot(trimmed, context);
      setMessages((prev) => [...prev, reply]);
    } finally {
      setIsSending(false);
    }
  };

  const resetChat = () => setMessages(initialChatMessages);

  const value = useMemo<ChatContextValue>(
    () => ({
      messages,
      isSending,
      sendMessage,
      resetChat
    }),
    [messages, isSending]
  );

  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>;
};

export const useChat = () => {
  const context = useContext(ChatContext);
  if (!context) {
    throw new Error('useChat must be used within ChatProvider');
  }
  return context;
};
