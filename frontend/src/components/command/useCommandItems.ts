import { useMemo } from 'react';

import { usePapers } from '@/hooks/usePapers';
import { useTopics } from '@/hooks/useTopics';
import { useWeeks } from '@/hooks/useWeeks';
import { ROUTES } from '@/lib/constants';
import { formatAuthors } from '@/lib/format';

export type CommandKind = 'page' | 'paper' | 'topic' | 'week' | 'action';

export interface CommandItem {
  id: string;
  kind: CommandKind;
  label: string;
  hint?: string;
  /** Search target — defaults to label + hint. */
  keywords: string;
  to?: string;
  run?: () => void;
}

interface ExtraActions {
  toggleTheme: () => void;
}

/** Builds the flat command list from the corpus + static navigation/actions. */
export function useCommandItems({ toggleTheme }: ExtraActions): CommandItem[] {
  const { data: papers = [] } = usePapers({});
  const { data: topics = [] } = useTopics();
  const { data: weeks = [] } = useWeeks();

  return useMemo(() => {
    const pages: CommandItem[] = [
      { id: 'go-home', kind: 'page', label: 'This week', keywords: 'this week home latest', to: ROUTES.home },
      { id: 'go-browse', kind: 'page', label: 'Browse', keywords: 'browse all papers filter', to: ROUTES.browse },
      { id: 'go-archive', kind: 'page', label: 'Archive', keywords: 'archive past issues weeks', to: ROUTES.archive },
    ];

    const actions: CommandItem[] = [
      { id: 'toggle-theme', kind: 'action', label: 'Toggle light / dark theme', keywords: 'theme dark light mode toggle', run: toggleTheme },
    ];

    const paperItems: CommandItem[] = papers.map((p) => ({
      id: `paper-${p.arxiv_id}`,
      kind: 'paper',
      label: p.title,
      hint: `${formatAuthors(p.authors, 2)} · ${p.arxiv_id}`,
      keywords: `${p.title} ${p.authors.map((a) => a.name).join(' ')} ${p.arxiv_id} ${p.topics.join(' ')}`,
      to: ROUTES.paper(p.arxiv_id),
    }));

    const topicItems: CommandItem[] = topics.map((t) => ({
      id: `topic-${t.title}`,
      kind: 'topic',
      label: t.title,
      hint: `${t.count} paper${t.count === 1 ? '' : 's'}`,
      keywords: `${t.title} topic`,
      to: `${ROUTES.browse}?topic=${encodeURIComponent(t.title)}`,
    }));

    const weekItems: CommandItem[] = weeks.map((w) => ({
      id: `week-${w.weekKey}`,
      kind: 'week',
      label: w.label,
      hint: `${w.weekKey} · ${w.count} papers`,
      keywords: `${w.label} ${w.weekKey} issue week`,
      to: ROUTES.week(w.weekKey),
    }));

    return [...pages, ...actions, ...topicItems, ...weekItems, ...paperItems];
  }, [papers, topics, weeks, toggleTheme]);
}
