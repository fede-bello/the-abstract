import { ROUTES } from '@/lib/constants';
import { TopicTag } from './TopicTag';
import styles from './TopicTagList.module.css';

interface TopicTagListProps {
  topics: string[];
  /** Link each tag to Browse filtered by that topic. */
  linked?: boolean;
}

export function TopicTagList({ topics, linked = false }: TopicTagListProps) {
  if (topics.length === 0) return null;
  return (
    <ul className={styles.list}>
      {topics.map((topic) => (
        <li key={topic}>
          <TopicTag
            label={topic}
            to={linked ? `${ROUTES.browse}?topic=${encodeURIComponent(topic)}` : undefined}
          />
        </li>
      ))}
    </ul>
  );
}
