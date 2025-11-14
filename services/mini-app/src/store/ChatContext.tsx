import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import type { ChatMessage } from '../types/domain';
import { chatService, type ChatContextPayload } from '../services/chatService';
import { generateId } from '../utils/id';
import { apiClient } from '../services/api';

interface ChatContextValue {
  messages: ChatMessage[];
  isSending: boolean;
  sendMessage: (text: string, context?: ChatContextPayload) => Promise<void>;
  resetChat: () => void;
}

const ChatContext = createContext<ChatContextValue | null>(null);

// Welcome message from maxOn
const welcomeMessage: ChatMessage = {
  id: 'welcome',
  author: 'maxon',
  text: 'Привет! Я maxOn — твой AI-коуч. Чем могу помочь сегодня? 🎯',
  timestamp: new Date().toISOString()
};

export const ChatProvider = ({ children }: { children: ReactNode }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([welcomeMessage]);
  const [isSending, setIsSending] = useState(false);

  // Reset chat state on mount to clear any previous dialog state
  useEffect(() => {
    apiClient.resetChatState();
  }, []);

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

  const resetChat = () => setMessages([welcomeMessage]);

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
