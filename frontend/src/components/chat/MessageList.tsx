import { useEffect, useRef } from 'react';

import type { ChatMessage } from '@/data/types';
import { MessageBubble } from './MessageBubble';
import styles from './MessageList.module.css';

interface MessageListProps {
  messages: ChatMessage[];
  suggestions: string[];
  onPickSuggestion: (text: string) => void;
}

export function MessageList({ messages, suggestions, onPickSuggestion }: MessageListProps) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className={styles.empty}>
        <p className={styles.prompt}>Ask anything about the papers in the digest.</p>
        <ul className={styles.suggestions}>
          {suggestions.map((s) => (
            <li key={s}>
              <button type="button" className={styles.suggestion} onClick={() => onPickSuggestion(s)}>
                {s}
              </button>
            </li>
          ))}
        </ul>
      </div>
    );
  }

  return (
    <div className={styles.list}>
      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} />
      ))}
      <div ref={endRef} />
    </div>
  );
}
