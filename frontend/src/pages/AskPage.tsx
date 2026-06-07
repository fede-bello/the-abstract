import { useSearchParams } from 'react-router-dom';

import { ChatShell } from '@/components/chat/ChatShell';
import { usePaper } from '@/hooks/usePapers';
import styles from './AskPage.module.css';

export default function AskPage() {
  const [params] = useSearchParams();
  const paperId = params.get('paper') ?? undefined;
  const topics = params.getAll('topic');

  // Resolve the paper title for the scope chip + suggestions (skips when no paper scope).
  const { data: paper } = usePaper(paperId);

  return (
    <div className={styles.page}>
      <header className={styles.head}>
        <span className="label">
          Ask <span className={styles.beta}>β</span>
        </span>
        <h1 className={styles.title}>Question the archive</h1>
      </header>

      <ChatShell scope={{ paperId, topics }} paperTitle={paper?.title} />
    </div>
  );
}
