import { useCallback, useState } from 'react';

import type { AskScope, ChatMessage } from '@/data/types';
import { useAsk } from '@/hooks/useAsk';
import { ChatInput } from './ChatInput';
import { MessageList } from './MessageList';
import { PreviewBanner } from './PreviewBanner';
import { ScopeChips } from './ScopeChips';
import styles from './ChatShell.module.css';

interface ChatShellProps {
  scope: AskScope;
  paperTitle?: string;
}

function suggestionsFor(scope: AskScope): string[] {
  if (scope.paperId) {
    return [
      'Summarize the key contribution in one sentence.',
      'What are the main limitations?',
      'How does this compare to prior work?',
    ];
  }
  if (scope.topics && scope.topics.length > 0) {
    return [
      `What's new in ${scope.topics[0]} this week?`,
      'Which result is the most surprising?',
      'List the papers with strong empirical claims.',
    ];
  }
  return [
    'What were the biggest results this week?',
    'Find papers about efficient inference.',
    'Summarize the latest on reasoning in LLMs.',
  ];
}

export function ChatShell({ scope, paperTitle }: ChatShellProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const { trigger, isMutating } = useAsk();

  const send = useCallback(
    async (text: string) => {
      const pendingId = crypto.randomUUID();
      setMessages((prev) => [
        ...prev,
        { id: crypto.randomUUID(), role: 'user', content: text },
        { id: pendingId, role: 'assistant', content: '', pending: true },
      ]);

      const resolve = (content: string, citations?: ChatMessage['citations']) =>
        setMessages((prev) =>
          prev.map((m) =>
            m.id === pendingId ? { ...m, content, citations, pending: false } : m,
          ),
        );

      try {
        const res = await trigger({ question: text, scope });
        if (res) resolve(res.answer, res.citations);
        else resolve('No response. Please try again.');
      } catch {
        resolve('Something went wrong answering that. Please try again.');
      }
    },
    [scope, trigger],
  );

  return (
    <div className={styles.shell}>
      <PreviewBanner />
      <ScopeChips paperId={scope.paperId} paperTitle={paperTitle} topics={scope.topics ?? []} />

      <div className={styles.conversation}>
        <MessageList
          messages={messages}
          suggestions={suggestionsFor(scope)}
          onPickSuggestion={send}
        />
      </div>

      <ChatInput onSend={send} disabled={isMutating} />
    </div>
  );
}
