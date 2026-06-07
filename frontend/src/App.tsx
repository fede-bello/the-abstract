import { Suspense } from 'react';
import { Outlet, ScrollRestoration } from 'react-router-dom';

import { CommandPaletteProvider } from '@/components/command/CommandPaletteProvider';
import { SiteFooter } from '@/components/layout/SiteFooter';
import { SiteHeader } from '@/components/layout/SiteHeader';
import { RouteFallback } from '@/components/common/RouteFallback';
import { ThemeProvider } from '@/components/theme/ThemeProvider';
import styles from './App.module.css';

export function App() {
  return (
    <ThemeProvider>
      <CommandPaletteProvider>
        <div className={styles.shell}>
          <a className="skip-link" href="#main">
            Skip to content
          </a>
          <SiteHeader />
          <main id="main" className={styles.main}>
            <Suspense fallback={<RouteFallback />}>
              <Outlet />
            </Suspense>
          </main>
          <SiteFooter />
          <ScrollRestoration />
        </div>
      </CommandPaletteProvider>
    </ThemeProvider>
  );
}
