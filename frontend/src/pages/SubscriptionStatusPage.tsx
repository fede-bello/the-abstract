import { Link, useSearchParams } from 'react-router-dom';

import { ROUTES } from '@/lib/constants';
import styles from './SubscriptionStatusPage.module.css';

// Landing page for the email confirm/unsubscribe links. The Edge Functions do the DB work and
// redirect here with ?status=… (see supabase/functions/_shared/redirect.ts) — the SPA renders the
// result on-brand, which the Supabase functions domain can't do itself.
type Status = 'confirmed' | 'already-confirmed' | 'unsubscribed' | 'invalid' | 'error';

interface Copy {
  kicker: string;
  title: string;
  body: string;
  tone: 'ok' | 'warn';
}

const COPY: Record<Status, Copy> = {
  confirmed: {
    kicker: 'Subscription confirmed',
    title: 'You’re subscribed.',
    body: 'Thanks for confirming — the next weekly digest lands in your inbox on Monday.',
    tone: 'ok',
  },
  'already-confirmed': {
    kicker: 'Already confirmed',
    title: 'You’re already on the list.',
    body: 'This email is already confirmed for the weekly digest. Nothing else to do.',
    tone: 'ok',
  },
  unsubscribed: {
    kicker: 'Unsubscribed',
    title: 'You’re unsubscribed.',
    body: 'You won’t receive the digest anymore. You can re-subscribe anytime from the site.',
    tone: 'ok',
  },
  invalid: {
    kicker: 'Invalid link',
    title: 'This link isn’t valid.',
    body: 'It may have expired or already been used. Try subscribing again from the site.',
    tone: 'warn',
  },
  error: {
    kicker: 'Something went wrong',
    title: 'We hit a snag.',
    body: 'Please try the link again in a little while.',
    tone: 'warn',
  },
};

function toStatus(raw: string | null): Status {
  return raw !== null && raw in COPY ? (raw as Status) : 'invalid';
}

export default function SubscriptionStatusPage() {
  const [params] = useSearchParams();
  const status = toStatus(params.get('status'));
  const copy = COPY[status];

  return (
    <section className={styles.page}>
      <p className={styles.kicker} data-tone={copy.tone}>
        {copy.kicker}
      </p>
      <h1 className={styles.title}>{copy.title}</h1>
      <p className={styles.body}>{copy.body}</p>
      <Link to={ROUTES.home} className={styles.link}>
        ← This week’s issue
      </Link>
    </section>
  );
}
