import { useId, useState } from 'react';
import type { ReactNode } from 'react';

import styles from './Collapsible.module.css';

interface CollapsibleProps {
  label: string;
  children: ReactNode;
  defaultOpen?: boolean;
}

/** A disclosure region — used for the paper's "why we picked this" rationale. */
export function Collapsible({ label, children, defaultOpen = false }: CollapsibleProps) {
  const [open, setOpen] = useState(defaultOpen);
  const id = useId();

  return (
    <div className={styles.wrap}>
      <button
        type="button"
        className={styles.trigger}
        aria-expanded={open}
        aria-controls={id}
        onClick={() => setOpen((v) => !v)}
      >
        <span className={styles.sign} aria-hidden="true">
          {open ? '−' : '+'}
        </span>
        {label}
      </button>
      {open && (
        <div id={id} className={styles.body}>
          {children}
        </div>
      )}
    </div>
  );
}
