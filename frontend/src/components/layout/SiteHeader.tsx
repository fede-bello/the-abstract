import { NavLink } from 'react-router-dom';

import { useCommandPalette } from '@/components/command/CommandPaletteProvider';
import { NAV_ITEMS, ROUTES } from '@/lib/constants';
import { ThemeToggle } from './ThemeToggle';
import styles from './SiteHeader.module.css';

export function SiteHeader() {
  const { open } = useCommandPalette();

  return (
    <header className={styles.header}>
      <div className={styles.inner}>
        <NavLink to={ROUTES.home} className={styles.brand} aria-label="the abstract — home">
          <span className={styles.brandMark} aria-hidden="true" />
          <span className={styles.brandText}>
            the
            <br />
            abstract
          </span>
        </NavLink>

        <button type="button" className={styles.search} onClick={open}>
          <span aria-hidden="true">Search</span>
          <kbd className={styles.kbd}>⌘K</kbd>
        </button>

        <nav className={styles.nav} aria-label="Primary">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === ROUTES.home}
              viewTransition
              className={({ isActive }) =>
                isActive ? `${styles.link} ${styles.linkActive}` : styles.link
              }
            >
              {item.label}
              {item.beta && <sup className={styles.beta}>β</sup>}
            </NavLink>
          ))}
          <ThemeToggle />
        </nav>
      </div>
    </header>
  );
}
