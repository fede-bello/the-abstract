import { useState, type FormEvent } from 'react';

import { getClient } from '@/data/client';
import styles from './SubscribeForm.module.css';

type Status = 'idle' | 'submitting' | 'confirmation-sent' | 'already-subscribed' | 'error';

// A client-side guard for quick feedback; the Edge Function validates again server-side.
const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

const MESSAGES: Record<Exclude<Status, 'idle' | 'submitting'>, string> = {
  'confirmation-sent': 'Almost there — check your inbox to confirm.',
  'already-subscribed': 'You’re already on the list.',
  error: 'Something went wrong — please try again.',
};

/** Footer newsletter signup. Inserts the email straight into Supabase via the anon key. */
export function SubscribeForm() {
  const [email, setEmail] = useState('');
  const [status, setStatus] = useState<Status>('idle');

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!EMAIL_RE.test(email)) {
      setStatus('error');
      return;
    }
    setStatus('submitting');
    try {
      const result = await getClient().subscribe(email);
      setStatus(result);
      setEmail('');
    } catch {
      setStatus('error');
    }
  }

  const showMessage = status !== 'idle' && status !== 'submitting';

  return (
    <form className={styles.form} onSubmit={handleSubmit} noValidate>
      <label className={styles.label} htmlFor="subscribe-email">
        Get the weekly digest
      </label>
      <div className={styles.row}>
        <input
          id="subscribe-email"
          className={styles.input}
          type="email"
          name="email"
          placeholder="you@example.com"
          value={email}
          onChange={(event) => {
            setEmail(event.target.value);
            if (status !== 'idle') setStatus('idle');
          }}
          autoComplete="email"
          disabled={status === 'submitting'}
        />
        <button
          className={styles.button}
          type="submit"
          disabled={status === 'submitting' || email.length === 0}
        >
          {status === 'submitting' ? '…' : 'Subscribe'}
        </button>
      </div>
      <p className={styles.status} aria-live="polite" data-tone={status === 'error' ? 'error' : 'ok'}>
        {showMessage ? MESSAGES[status] : ' '}
      </p>
    </form>
  );
}
