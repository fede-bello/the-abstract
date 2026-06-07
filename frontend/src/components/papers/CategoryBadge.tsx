import { CATEGORY_LABEL } from '@/data/categories';
import styles from './CategoryBadge.module.css';

interface CategoryBadgeProps {
  code: string;
}

/** Monospace arXiv category code (e.g. cs.LG) with the full name as a tooltip. */
export function CategoryBadge({ code }: CategoryBadgeProps) {
  return (
    <span className={styles.badge} title={CATEGORY_LABEL[code] ?? code}>
      {code}
    </span>
  );
}
