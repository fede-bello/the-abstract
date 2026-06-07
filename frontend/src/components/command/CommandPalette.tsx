import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { useThemeContext } from '@/components/theme/ThemeProvider';
import { fuzzyScore } from '@/lib/fuzzy';
import { useCommandItems } from './useCommandItems';
import type { CommandItem } from './useCommandItems';
import styles from './CommandPalette.module.css';

interface CommandPaletteProps {
  onClose: () => void;
}

const KIND_LABEL: Record<CommandItem['kind'], string> = {
  page: 'Go',
  paper: 'Paper',
  topic: 'Topic',
  week: 'Issue',
  action: 'Action',
};

export function CommandPalette({ onClose }: CommandPaletteProps) {
  const navigate = useNavigate();
  const { toggle } = useThemeContext();
  const items = useCommandItems({ toggleTheme: toggle });

  const [query, setQuery] = useState('');
  const [active, setActive] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLUListElement>(null);

  const results = useMemo(() => {
    if (!query.trim()) return items.slice(0, 24);
    return items
      .map((item) => ({ item, score: fuzzyScore(query, `${item.label} ${item.keywords}`) }))
      .filter((r): r is { item: CommandItem; score: number } => r.score !== null)
      .sort((a, b) => b.score - a.score)
      .slice(0, 40)
      .map((r) => r.item);
  }, [items, query]);

  useEffect(() => setActive(0), [query]);
  useEffect(() => inputRef.current?.focus(), []);

  useEffect(() => {
    const el = listRef.current?.children[active] as HTMLElement | undefined;
    el?.scrollIntoView({ block: 'nearest' });
  }, [active]);

  const select = (item: CommandItem | undefined) => {
    if (!item) return;
    item.run?.();
    if (item.to) navigate(item.to);
    onClose();
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActive((i) => Math.min(i + 1, results.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActive((i) => Math.max(i - 1, 0));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      select(results[active]);
    } else if (e.key === 'Escape') {
      e.preventDefault();
      onClose();
    }
  };

  return (
    <div className={styles.overlay} onMouseDown={onClose}>
      <div
        className={styles.dialog}
        role="dialog"
        aria-modal="true"
        aria-label="Command palette"
        onMouseDown={(e) => e.stopPropagation()}
        onKeyDown={onKeyDown}
      >
        <div className={styles.searchRow}>
          <span className={styles.prompt} aria-hidden="true">
            ⌘
          </span>
          <input
            ref={inputRef}
            className={styles.input}
            placeholder="Search papers, topics, issues…"
            aria-label="Search papers, topics, and issues"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <kbd className={styles.esc}>esc</kbd>
        </div>

        {results.length === 0 ? (
          <p className={styles.empty}>No matches for “{query}”.</p>
        ) : (
          <ul ref={listRef} className={styles.list}>
            {results.map((item, i) => (
              <li
                key={item.id}
                className={i === active ? `${styles.item} ${styles.activeItem}` : styles.item}
                onMouseEnter={() => setActive(i)}
                onClick={() => select(item)}
              >
                <span className={styles.kind}>{KIND_LABEL[item.kind]}</span>
                <span className={styles.label}>{item.label}</span>
                {item.hint && <span className={styles.hint}>{item.hint}</span>}
              </li>
            ))}
          </ul>
        )}

        <footer className={styles.footer}>
          <span>
            <kbd>↑</kbd>
            <kbd>↓</kbd> navigate
          </span>
          <span>
            <kbd>↵</kbd> open
          </span>
          <span>
            <kbd>esc</kbd> close
          </span>
        </footer>
      </div>
    </div>
  );
}
