import { Link } from 'react-router-dom';

import { ROUTES } from '@/lib/constants';
import styles from './NotFoundPage.module.css';

export default function NotFoundPage() {
  return (
    <div className={styles.page}>
      <p className={styles.code}>404</p>
      <h1 className={styles.title}>Nothing filed here.</h1>
      <p className={styles.hint}>The page you’re after doesn’t exist or has moved.</p>
      <Link to={ROUTES.home} className={styles.link}>
        ← Back to this week
      </Link>
    </div>
  );
}
