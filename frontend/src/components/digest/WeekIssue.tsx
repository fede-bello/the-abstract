import type { WeekIssueData } from '@/data/types';
import { PaperFeed } from '@/components/papers/PaperFeed';
import { Masthead } from './Masthead';

interface WeekIssueProps {
  issue: WeekIssueData;
  /** Header kicker, e.g. "This week" on Home or "Archive issue" on a past week. */
  kicker: string;
}

/** One weekly issue: masthead + the paper index. Reused by Home and the Archive week page. */
export function WeekIssue({ issue, kicker }: WeekIssueProps) {
  return (
    <section>
      <Masthead
        kicker={kicker}
        title={issue.week.label}
        count={issue.week.count}
        dateRange={{ start: issue.week.start, end: issue.week.end }}
      />
      <PaperFeed papers={issue.papers} />
    </section>
  );
}
