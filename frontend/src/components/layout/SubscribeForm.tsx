import { useState, type FormEvent } from 'react';

import { getClient } from '@/data/client';
import styles from './SubscribeForm.module.css';

type Status = 'idle' | 'submitting' | 'confirmation-sent' | 'already-subscribed' | 'error';

// A client-side guard for quick feedback; the Edge Function validates again server-side.
const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

/** Newsletter signup, used in the footer and the home hero. Calls the `subscribe` Edge Function,
 *  which records a pending row and emails a double opt-in confirmation link — nothing arrives
 *  until the recipient clicks it. */
export function SubscribeForm() {
  const [email, setEmail] = useState('');
  // Remembered after submit so the success panel can name the address we mailed.
  const [submittedEmail, setSubmittedEmail] = useState('');
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
      setSubmittedEmail(email);
      setStatus(result);
      setEmail('');
    } catch {
      setStatus('error');
    }
  }

  // On success, swap the input row for a prominent panel — the whole point of double opt-in is
  // that the user MUST go check their email, so we make that the loud, unmissable next step.
  if (status === 'confirmation-sent' || status === 'already-subscribed') {
    const sent = status === 'confirmation-sent';
    return (
      <div className={styles.success} role="status" aria-live="polite">
        <span className={styles.successIcon} aria-hidden="true">
          {sent ? '✉' : '✓'}
        </span>
        <div>
          <p className={styles.successTitle}>{sent ? 'Check your inbox' : 'Already subscribed'}</p>
          <p className={styles.successText}>
            {sent ? (
              <>
                We just emailed a confirmation link to <strong>{submittedEmail}</strong>. Click it
                to start receiving the weekly digest — it won’t arrive until you do.
              </>
            ) : (
              <>
                <strong>{submittedEmail}</strong> is already confirmed for the weekly digest.
              </>
            )}
          </p>
        </div>
      </div>
    );
  }

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
        {status === 'error' ? 'Something went wrong — please try again.' : ' '}
      </p>
    </form>
  );
}
