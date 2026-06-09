// Route paths and primary navigation — single source of truth for links across the app.

export const ROUTES = {
  home: '/',
  browse: '/browse',
  paper: (arxivId: string) => `/paper/${arxivId}`,
  archive: '/archive',
  week: (weekKey: string) => `/archive/${weekKey}`,
} as const;

export interface NavItem {
  label: string;
  to: string;
}

export const NAV_ITEMS: NavItem[] = [
  { label: 'This week', to: ROUTES.home },
  { label: 'Browse', to: ROUTES.browse },
  { label: 'Archive', to: ROUTES.archive },
];

export const SITE = {
  name: 'the abstract',
  tagline: 'The machine-learning papers worth your attention, weekly, from arXiv.',
} as const;
