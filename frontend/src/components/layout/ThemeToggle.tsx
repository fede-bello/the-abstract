import { useThemeContext } from '@/components/theme/ThemeProvider';
import styles from './ThemeToggle.module.css';

export function ThemeToggle() {
  const { theme, toggle } = useThemeContext();
  const isDark = theme === 'dark';

  return (
    <button
      type="button"
      className={styles.toggle}
      onClick={toggle}
      aria-pressed={isDark}
      aria-label={`Switch to ${isDark ? 'light' : 'dark'} theme`}
      title={`Switch to ${isDark ? 'light' : 'dark'} theme`}
    >
      <span className={isDark ? styles.track : `${styles.track} ${styles.light}`}>
        <span className={styles.thumb} />
      </span>
      <span className={styles.glyph} aria-hidden="true">
        {isDark ? '☾' : '☀'}
      </span>
    </button>
  );
}
