import type { TopicCount } from '@/data/types';
import type { FilterControls } from '@/hooks/useFilterParams';
import { CategoryFacetList } from './CategoryFacetList';
import { DateRangeControl } from './DateRangeControl';
import { TopicFacetList } from './TopicFacetList';
import styles from './FilterSidebar.module.css';

interface FilterSidebarProps {
  controls: FilterControls;
  topics: TopicCount[];
  categories: string[];
}

export function FilterSidebar({ controls, topics, categories }: FilterSidebarProps) {
  const { filters, activeCount, toggleTopic, toggleCategory, setDateRange, clearAll } = controls;

  return (
    <aside className={styles.sidebar} aria-label="Filters">
      <div className={styles.head}>
        <span className="label">Filters</span>
        {activeCount > 0 && (
          <button type="button" className={styles.clear} onClick={clearAll}>
            Clear ({activeCount})
          </button>
        )}
      </div>

      <section className={styles.section}>
        <h2 className={styles.heading}>Topics</h2>
        <TopicFacetList
          topics={topics}
          selected={filters.topics ?? []}
          onToggle={toggleTopic}
        />
      </section>

      <section className={styles.section}>
        <h2 className={styles.heading}>arXiv category</h2>
        <CategoryFacetList
          available={categories}
          selected={filters.categories ?? []}
          onToggle={toggleCategory}
        />
      </section>

      <section className={styles.section}>
        <h2 className={styles.heading}>Published</h2>
        <DateRangeControl from={filters.from} to={filters.to} onChange={setDateRange} />
      </section>
    </aside>
  );
}
