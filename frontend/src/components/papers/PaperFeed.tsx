import type { Paper } from '@/data/types';
import { EmptyState } from '@/components/common/EmptyState';
import { PaperIndexRow } from './PaperIndexRow';
import styles from './PaperFeed.module.css';

interface PaperFeedProps {
  papers: Paper[];
  emptyTitle?: string;
  emptyHint?: string;
}

/** The numbered index of papers — the repeated unit across Home, Browse, and Archive issues. */
export function PaperFeed({ papers, emptyTitle, emptyHint }: PaperFeedProps) {
  if (papers.length === 0) {
    return (
      <EmptyState
        title={emptyTitle ?? 'No papers here'}
        hint={emptyHint ?? 'Try widening your filters.'}
      />
    );
  }

  return (
    <div className={styles.feed}>
      {papers.map((paper, i) => (
        <PaperIndexRow key={paper.arxiv_id} paper={paper} position={i + 1} />
      ))}
    </div>
  );
}
