import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import type { ChatMessage } from '../types/domain';
import { chatService, type ChatContextPayload } from '../services/chatService';
import { generateId } from '../utils/id';
import { apiClient } from '../services/api';

interface ChatContextValue {
  messages: ChatMessage[];
  isSending: boolean;
  sendMessage: (text: string, context?: ChatContextPayload) => Promise<void>;
  sendCallback: (callback_data: string) => Promise<void>;
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
  // TODO: Uncomment when backend implements /api/reset-state endpoint
  // useEffect(() => {
  //   apiClient.resetChatState().catch(() => {
  //     // Silently ignore if endpoint doesn't exist - not critical
  //   });
  // }, []);

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
      // Handle both single message and array of messages
      if (Array.isArray(reply)) {
        setMessages((prev) => [...prev, ...reply]);
      } else {
        setMessages((prev) => [...prev, reply]);
      }
    } finally {
      setIsSending(false);
    }
  };

  const sendCallback = async (callback_data: string) => {
    setIsSending(true);
    try {
      const reply = await chatService.sendCallbackToBot(callback_data);

      // Replace last bot message with buttons instead of adding new one
      setMessages((prev) => {
        const newMessages = Array.isArray(reply) ? reply : [reply];

        // Find last message from bot with buttons
        const lastBotIndex = prev.length - 1;
        if (lastBotIndex >= 0 && prev[lastBotIndex].author === 'maxon' && prev[lastBotIndex].buttons) {
          // Replace the last bot message
          return [...prev.slice(0, lastBotIndex), ...newMessages];
        }

        // Otherwise, append as usual
        return [...prev, ...newMessages];
      });
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
      sendCallback,
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
