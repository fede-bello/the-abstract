import { lazy } from 'react';
import { createBrowserRouter } from 'react-router-dom';

import { App } from '@/App';

// Lazy per-route so the chat and detail bundles only load when visited.
const HomePage = lazy(() => import('@/pages/HomePage'));
const BrowsePage = lazy(() => import('@/pages/BrowsePage'));
const PaperDetailPage = lazy(() => import('@/pages/PaperDetailPage'));
const ArchivePage = lazy(() => import('@/pages/ArchivePage'));
const WeekIssuePage = lazy(() => import('@/pages/WeekIssuePage'));
const AskPage = lazy(() => import('@/pages/AskPage'));
const NotFoundPage = lazy(() => import('@/pages/NotFoundPage'));

export const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [
      { index: true, element: <HomePage /> },
      { path: 'browse', element: <BrowsePage /> },
      { path: 'paper/:arxivId', element: <PaperDetailPage /> },
      { path: 'archive', element: <ArchivePage /> },
      { path: 'archive/:weekKey', element: <WeekIssuePage /> },
      { path: 'ask', element: <AskPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
]);
