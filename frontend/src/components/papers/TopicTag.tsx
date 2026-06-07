import { Link } from 'react-router-dom';

import styles from './TopicTag.module.css';

interface TopicTagProps {
  label: string;
  /** When set, the tag links there (e.g. Browse filtered by this topic). */
  to?: string;
  active?: boolean;
  count?: number;
}

export function TopicTag({ label, to, active, count }: TopicTagProps) {
  const className = active ? `${styles.tag} ${styles.active}` : styles.tag;
  const content = (
    <>
      {label}
      {count !== undefined && <span className={styles.count}>{count}</span>}
    </>
  );

  if (to) {
    return (
      <Link to={to} className={className}>
        {content}
      </Link>
    );
  }
  return <span className={className}>{content}</span>;
}
