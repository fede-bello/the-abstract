import { SITE } from '@/lib/constants';
import { SubscribeForm } from './SubscribeForm';
import styles from './SiteFooter.module.css';

export function SiteFooter() {
  return (
    <footer className={styles.footer}>
      <div className={styles.inner}>
        <p className={styles.tagline}>{SITE.tagline}</p>
        <SubscribeForm />
        <p className={styles.meta}>
          <span>{SITE.name}</span>
          <span className={styles.dot}>/</span>
          <span>open source</span>
          <span className={styles.dot}>/</span>
          <a
            className={styles.link}
            href="https://arxiv.org"
            target="_blank"
            rel="noreferrer noopener"
          >
            arXiv ↗
          </a>
        </p>
      </div>
    </footer>
  );
}
