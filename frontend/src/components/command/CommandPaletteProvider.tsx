import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';

import { CommandPalette } from './CommandPalette';

interface CommandPaletteContextValue {
  open: () => void;
}

const CommandPaletteContext = createContext<CommandPaletteContextValue | null>(null);

/** Owns the palette's open state, the global ⌘K / Ctrl+K shortcut, and renders the dialog. */
export function CommandPaletteProvider({ children }: { children: ReactNode }) {
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setIsOpen((v) => !v);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  const value = useMemo(() => ({ open: () => setIsOpen(true) }), []);
  const close = useCallback(() => setIsOpen(false), []);

  return (
    <CommandPaletteContext.Provider value={value}>
      {children}
      {isOpen && <CommandPalette onClose={close} />}
    </CommandPaletteContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useCommandPalette(): CommandPaletteContextValue {
  const ctx = useContext(CommandPaletteContext);
  if (!ctx) throw new Error('useCommandPalette must be used within CommandPaletteProvider');
  return ctx;
}
