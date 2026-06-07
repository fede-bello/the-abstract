import { CATEGORIES } from '@/data/mock/categories';
import styles from './FacetList.module.css';

interface CategoryFacetListProps {
  /** Category codes present in the corpus; others are hidden. */
  available: string[];
  selected: string[];
  onToggle: (code: string) => void;
}

export function CategoryFacetList({ available, selected, onToggle }: CategoryFacetListProps) {
  const shown = CATEGORIES.filter((c) => available.includes(c.code));
  return (
    <ul className={styles.list}>
      {shown.map((category) => {
        const isOn = selected.includes(category.code);
        return (
          <li key={category.code}>
            <button
              type="button"
              className={isOn ? `${styles.facet} ${styles.on}` : styles.facet}
              aria-pressed={isOn}
              onClick={() => onToggle(category.code)}
            >
              <span className={styles.box} aria-hidden="true" />
              <span className={styles.name}>
                <span className="mono">{category.code}</span> {category.label}
              </span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
