import { Link } from 'react-router-dom';

import type { ChatMessage } from '@/data/types';
import { ROUTES } from '@/lib/constants';
import styles from './MessageBubble.module.css';

interface MessageBubbleProps {
  message: ChatMessage;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user';
  return (
    <div className={isUser ? `${styles.row} ${styles.userRow}` : styles.row}>
      <span className={styles.role}>{isUser ? 'You' : 'Abstract'}</span>
      <div className={isUser ? `${styles.bubble} ${styles.user}` : styles.bubble}>
        {message.pending ? (
          <span className={styles.typing} aria-label="Thinking">
            <span />
            <span />
            <span />
          </span>
        ) : (
          <p className={styles.text}>{message.content}</p>
        )}

        {message.citations && message.citations.length > 0 && (
          <ul className={styles.citations}>
            {message.citations.map((c) => (
              <li key={c.arxiv_id}>
                <Link to={ROUTES.paper(c.arxiv_id)} className={styles.citation}>
                  <span className="mono">{c.arxiv_id}</span> {c.title}
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
