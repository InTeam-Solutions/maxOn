import { useEffect, useRef, useState } from 'react';
import dayjs from 'dayjs';
import { Input, Typography } from '@maxhub/max-ui';
import clsx from 'clsx';
import { useChat } from '../../store/ChatContext';
import type { ChatAttachment, ChatButton, ChatMessage as ChatMessageType } from '../../types/domain';
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

const ButtonRow = ({ buttons, onButtonClick }: { buttons: ChatButton[]; onButtonClick: (button: ChatButton) => void }) => {
  return (
    <div className={styles.buttonRow}>
      {buttons.map((button, index) => (
        <button
          key={index}
          className={styles.chatButton}
          onClick={() => onButtonClick(button)}
        >
          {button.text}
        </button>
      ))}
    </div>
  );
};

const HtmlMessage = ({ html }: { html: string }) => {
  return <div className={styles.htmlContent} dangerouslySetInnerHTML={{ __html: html }} />;
};

export const ChatPanel = ({ elevated, onClose }: ChatPanelProps) => {
  const { messages, isSending, sendMessage } = useChat();
  const [draft, setDraft] = useState('');
  const listRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    if (!draft.trim()) return;
    await sendMessage(draft);
    setDraft('');
    // Don't auto-close chat after sending - let user continue conversation
  };

  const handleButtonClick = async (button: ChatButton) => {
    // Send button action as a message
    await sendMessage(button.action, button.data);
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
              message.author === 'user' ? styles.userBubble : styles.botBubble
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
            {message.buttons && message.buttons.length > 0 && (
              <div className={styles.buttons}>
                {message.buttons.map((row, rowIndex) => (
                  <ButtonRow key={rowIndex} buttons={row} onButtonClick={handleButtonClick} />
                ))}
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
