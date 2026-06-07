import type { TopicCount } from '@/data/types';
import styles from './FacetList.module.css';

interface TopicFacetListProps {
  topics: TopicCount[];
  selected: string[];
  onToggle: (topic: string) => void;
}

export function TopicFacetList({ topics, selected, onToggle }: TopicFacetListProps) {
  return (
    <ul className={styles.list}>
      {topics.map((topic) => {
        const isOn = selected.includes(topic.title);
        return (
          <li key={topic.title}>
            <button
              type="button"
              className={isOn ? `${styles.facet} ${styles.on}` : styles.facet}
              aria-pressed={isOn}
              onClick={() => onToggle(topic.title)}
            >
              <span className={styles.box} aria-hidden="true" />
              <span className={styles.name}>{topic.title}</span>
              <span className={styles.count}>{topic.count}</span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
