import { useEffect, useRef, useState } from 'react';
import dayjs from 'dayjs';
import { Input, Typography } from '@maxhub/max-ui';
import clsx from 'clsx';
import { useChat } from '../../store/ChatContext';
import type { ChatAttachment, ChatButton, ChatMessage as ChatMessageType } from '../../types/domain';
import { WeekScheduleSelector } from '../../components/WeekScheduleSelector';
import styles from './ChatPanel.module.css';

interface ChatPanelProps {
  elevated?: boolean;
  onClose?: () => void;
}

const AttachmentCard = ({ attachment }: { attachment: ChatAttachment }) => {
  if (attachment.type === 'goal') {
    return (
      <div className={styles.attachment}>
        <span className={styles.attachmentLabel}>Цель</span>
        <div className={styles.attachmentTitle}>{attachment.payload.title}</div>
        <Typography.Body variant="small" className={styles.attachmentMeta}>
          Прогресс {attachment.payload.progress}%
        </Typography.Body>
      </div>
    );
  }
  return (
    <div className={styles.attachment}>
      <span className={styles.attachmentLabel}>Задача</span>
      <div className={styles.attachmentTitle}>{attachment.payload.title}</div>
      <Typography.Body variant="small" className={styles.attachmentMeta}>
        До {dayjs(attachment.payload.dueDate).format('DD MMM HH:mm')}
      </Typography.Body>
    </div>
  );
};

const ButtonRow = ({
  buttons,
  onButtonClick,
  multiSelect = false,
  selectedButtons = [],
  onConfirmSelection
}: {
  buttons: ChatButton[];
  onButtonClick: (button: ChatButton) => void;
  multiSelect?: boolean;
  selectedButtons?: string[];
  onConfirmSelection?: (selected: string[]) => void;
}) => {
  const [selected, setSelected] = useState<string[]>(selectedButtons);

  const handleClick = (button: ChatButton) => {
    if (!multiSelect) {
      onButtonClick(button);
      return;
    }

    // Toggle selection
    const buttonId = button.callback_data || button.text;
    setSelected(prev => {
      if (prev.includes(buttonId)) {
        return prev.filter(id => id !== buttonId);
      } else {
        return [...prev, buttonId];
      }
    });
  };

  const handleConfirm = () => {
    if (onConfirmSelection) {
      onConfirmSelection(selected);
    }
  };

  return (
    <div className={styles.buttonContainer}>
      <div className={styles.buttonRow}>
        {buttons.map((button, index) => {
          const buttonId = button.callback_data || button.text;
          const isSelected = selected.includes(buttonId);

          return (
            <button
              key={index}
              className={clsx(
                styles.chatButton,
                multiSelect && isSelected && styles.chatButtonSelected
              )}
              onClick={() => handleClick(button)}
            >
              {multiSelect && isSelected && '✓ '}
              {button.text}
            </button>
          );
        })}
      </div>
      {multiSelect && selected.length > 0 && (
        <button
          className={styles.confirmButton}
          onClick={handleConfirm}
        >
          Готово ({selected.length})
        </button>
      )}
    </div>
  );
};

const HtmlMessage = ({ html }: { html: string }) => {
  return <div className={styles.htmlContent} dangerouslySetInnerHTML={{ __html: html }} />;
};

export const ChatPanel = ({ elevated, onClose }: ChatPanelProps) => {
  const { messages, isSending, sendMessage, sendCallback } = useChat();
  const [draft, setDraft] = useState('');
  const listRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    // Auto-scroll to bottom when new messages arrive
    const scrollToBottom = () => {
      if (listRef.current) {
        listRef.current.scrollTo({
          top: listRef.current.scrollHeight,
          behavior: 'smooth'
        });
      }
    };

    // Small delay to ensure DOM is updated
    const timeoutId = setTimeout(scrollToBottom, 100);
    return () => clearTimeout(timeoutId);
  }, [messages]);

  const handleSend = async () => {
    if (!draft.trim()) return;
    await sendMessage(draft);
    setDraft('');
    // Don't auto-close chat after sending - let user continue conversation
  };

  const handleButtonClick = async (button: ChatButton) => {
    // Send button callback_data via callback endpoint
    if (!button.callback_data) {
      console.error('[ChatPanel] Button missing callback_data:', button);
      // If no callback_data, try using the button text as a message instead
      if (button.text) {
        await sendMessage(button.text);
      }
      return;
    }
    await sendCallback(button.callback_data);
  };

  const handleMultiSelectConfirm = async (selectedCallbacks: string[]) => {
    // Send selected callbacks individually to the backend
    if (selectedCallbacks.length === 0) return;

    // Send each callback individually in sequence
    for (const callback of selectedCallbacks) {
      await sendCallback(callback);
    }
  };

  // Detect if message requires multi-select based on text or button patterns
  const isMultiSelectMessage = (message: ChatMessageType): boolean => {
    const text = message.text.toLowerCase();

    // Check text hints for multi-select
    if (text.includes('можно выбрать несколько') ||
        text.includes('выбери несколько') ||
        text.includes('отметь все')) {
      return true;
    }

    // Check button patterns (time_pref, day_select, day_pref, etc.)
    if (message.buttons && message.buttons.length > 0) {
      const firstRow = message.buttons[0];
      if (firstRow.length > 0 && firstRow[0].callback_data) {
        const callback = firstRow[0].callback_data;
        // Patterns that typically allow multi-select
        if (callback.startsWith('time_pref:') ||
            callback.startsWith('day_select:') ||
            callback.startsWith('day_pref:') ||
            callback.startsWith('weekday:')) {
          return true;
        }
      }
    }

    return false;
  };

  const handleScheduleSelect = async (selectedDays: number[], preferredTime: string, messageId: string) => {
    // Format selected days as human-readable string
    const dayNames = ['понедельникам', 'вторникам', 'средам', 'четвергам', 'пятницам', 'субботам', 'воскресеньям'];
    const selectedDayNames = selectedDays.map(d => dayNames[d]).join(', ');

    // Send the selection as a message
    const message = `Мне удобно заниматься по ${selectedDayNames} в ${preferredTime}`;
    await sendMessage(message);
  };

  // Helper function to detect if message requires user action based on content
  const messageRequiresAction = (message: ChatMessageType): boolean => {
    if (message.author !== 'maxon') return false;
    if (message.requiresAction) return true;
    if (message.buttons && message.buttons.length > 0) return true;

    // Check for question patterns or action requests
    const text = message.text.toLowerCase();
    const actionPatterns = [
      '?', // Contains question mark
      'когда',
      'как',
      'что',
      'где',
      'почему',
      'попробуй',
      'попробуйте',
      'переформулиров',
      'уточни',
      'уточните',
      'напиши',
      'напишите',
      'скажи',
      'скажите',
      'укажи',
      'укажите',
      'выбери',
      'выберите'
    ];

    return actionPatterns.some(pattern => text.includes(pattern));
  };

  return (
    <section className={clsx(elevated && 'card', styles.chatPanel)}>
      <div className={styles.chatHeader}>
        <div>
          <div className={styles.chatTitle}>maxOn</div>
          <Typography.Body variant="small" className={styles.chatSubtitle}>
            Твой AI-коуч онлайн
          </Typography.Body>
        </div>
        {onClose && (
          <button className={styles.closeButton} onClick={onClose}>
            ✕
          </button>
        )}
      </div>
      <div className={styles.messages} ref={listRef}>
        {messages.map((message) => (
          <div
            key={message.id}
            className={clsx(
              styles.bubble,
              message.author === 'user' ? styles.userBubble : styles.botBubble,
              messageRequiresAction(message) && styles.requiresAction
            )}
          >
            {message.isHtml ? (
              <HtmlMessage html={message.text} />
            ) : (
              <Typography.Body variant="medium">{message.text}</Typography.Body>
            )}
            {message.attachments && (
              <div className={styles.attachments}>
                {message.attachments.map((attachment) => (
                  <AttachmentCard key={attachment.payload.id} attachment={attachment} />
                ))}
              </div>
            )}
            {message.buttons && message.buttons.length > 0 && (() => {
              // Flatten all button rows into a single array
              const allButtons = message.buttons.flat().filter(btn => btn.callback_data || btn.text);
              if (allButtons.length === 0) return null;

              const multiSelect = isMultiSelectMessage(message);

              // If multiSelect, filter out backend's "Готово" button and use it as confirmation callback
              let confirmCallback: string | undefined;
              let selectableButtons = allButtons;

              if (multiSelect) {
                // Find and extract the "Готово" button from backend
                const doneButton = allButtons.find(btn =>
                  btn.text.includes('Готово') ||
                  btn.callback_data?.includes('_done') ||
                  btn.callback_data?.includes('time_pref_done') ||
                  btn.callback_data?.includes('day_pref_done')
                );

                if (doneButton) {
                  confirmCallback = doneButton.callback_data;
                  // Remove the backend's "Готово" button from selectable buttons
                  selectableButtons = allButtons.filter(btn => btn !== doneButton);
                }
              }

              return (
                <div className={styles.buttons}>
                  <ButtonRow
                    buttons={selectableButtons}
                    onButtonClick={handleButtonClick}
                    multiSelect={multiSelect}
                    onConfirmSelection={multiSelect ? async (selected) => {
                      // First send all selected callbacks
                      await handleMultiSelectConfirm(selected);
                      // Then send the confirmation callback if available
                      if (confirmCallback) {
                        await sendCallback(confirmCallback);
                      }
                    } : undefined}
                  />
                </div>
              );
            })()}
            {message.showScheduleSelector && (
              <div className={styles.scheduleWidget}>
                <WeekScheduleSelector
                  onSelect={(days, time) => handleScheduleSelect(days, time, message.id)}
                  onCancel={() => {
                    // Optionally handle cancel - send a message like "Пропустить"
                    sendMessage('Пропустить расписание');
                  }}
                />
              </div>
            )}
            <div className={styles.time}>{dayjs(message.timestamp).format('HH:mm')}</div>
          </div>
        ))}
      </div>
      <div className={styles.composer}>
        <Input
          className={styles.messageInput}
          placeholder="Введите сообщение…"
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter') {
              handleSend();
            }
          }}
        />
        <button
          type="button"
          className={clsx(styles.sendButton, (!draft.trim() || isSending) && styles.sendButtonDisabled)}
          onClick={handleSend}
          disabled={!draft.trim() || isSending}
          aria-label="Отправить сообщение"
        >
          {isSending ? <span className={styles.loader} /> : <span className={styles.sendIcon}>➤</span>}
        </button>
      </div>
    </section>
  );
};
