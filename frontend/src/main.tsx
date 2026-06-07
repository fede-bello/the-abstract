import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { RouterProvider } from 'react-router-dom';
import { SWRConfig } from 'swr';

import { router } from '@/router';
import './styles/fonts';
import './styles/global.css';

// SWR is the server-state cache. Mock/REST data rarely changes within a session, so we
// disable focus revalidation and dedupe aggressively. Each hook passes its own fetcher.
const swrConfig = {
  revalidateOnFocus: false,
  dedupingInterval: 60_000,
  shouldRetryOnError: false,
};

const rootElement = document.getElementById('root');
if (!rootElement) throw new Error('Root element #root not found');

createRoot(rootElement).render(
  <StrictMode>
    <SWRConfig value={swrConfig}>
      <RouterProvider router={router} />
    </SWRConfig>
  </StrictMode>,
);
