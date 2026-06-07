import { Link } from 'react-router-dom';

import type { WeekSummary } from '@/data/types';
import { ROUTES } from '@/lib/constants';
import { indexLabel, pluralize } from '@/lib/format';
import styles from './ArchiveIndex.module.css';

interface ArchiveIndexProps {
  weeks: WeekSummary[];
}

interface MonthGroup {
  label: string;
  weeks: WeekSummary[];
}

/** Group week summaries by calendar month, newest first (input is already sorted desc). */
function groupByMonth(weeks: WeekSummary[]): MonthGroup[] {
  const groups: MonthGroup[] = [];
  for (const week of weeks) {
    const d = new Date(week.start);
    const label = d.toLocaleDateString('en-US', {
      month: 'long',
      year: 'numeric',
      timeZone: 'UTC',
    });
    const last = groups[groups.length - 1];
    if (last && last.label === label) last.weeks.push(week);
    else groups.push({ label, weeks: [week] });
  }
  return groups;
}

export function ArchiveIndex({ weeks }: ArchiveIndexProps) {
  const months = groupByMonth(weeks);

  return (
    <div className={styles.wrap}>
      {months.map((month) => (
        <section key={month.label} className={styles.month}>
          <h2 className={styles.monthLabel}>{month.label}</h2>
          <ul className={styles.weeks}>
            {month.weeks.map((week, i) => (
              <li key={week.weekKey}>
                <Link to={ROUTES.week(week.weekKey)} className={styles.week} viewTransition>
                  <span className={`mono ${styles.num}`}>{indexLabel(i + 1)}</span>
                  <span className={styles.label}>{week.label}</span>
                  <span className={styles.key}>{week.weekKey}</span>
                  <span className={styles.count}>{pluralize(week.count, 'paper')}</span>
                  <span className={styles.arrow} aria-hidden="true">
                    →
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
