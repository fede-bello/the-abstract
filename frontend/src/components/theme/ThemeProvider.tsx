import { createContext, useContext, useMemo } from 'react';
import type { ReactNode } from 'react';

import { useTheme } from '@/hooks/useTheme';
import type { Theme } from '@/hooks/useTheme';

interface ThemeContextValue {
  theme: Theme;
  toggle: () => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

/** Single source of truth for the theme, so the header toggle and command palette agree. */
export function ThemeProvider({ children }: { children: ReactNode }) {
  const { theme, toggle } = useTheme();
  const value = useMemo(() => ({ theme, toggle }), [theme, toggle]);
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useThemeContext(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error('useThemeContext must be used within ThemeProvider');
  return ctx;
}
