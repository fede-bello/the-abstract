-- Read-only views the web SPA queries directly via the anon key (papers RLS already allows
-- public select; see 0001_init.sql). These express the aggregations PostgREST can't do over a
-- plain table: per-ISO-week counts, per-topic counts, and the distinct categories present.
-- The frontend builds week labels/bounds itself (src/data/week.ts), so the week view returns
-- only the key, count, and Monday/Sunday dates.

-- One row per ISO week (Mon-Sun) that has papers. `date_trunc('week', ...)` is the week's Monday.
create view week_summaries as
select
    to_char(date_trunc('week', published), 'IYYY"-W"IW') as week_key,
    count(*) as count,
    date_trunc('week', published)::date as start,
    (date_trunc('week', published) + interval '6 days')::date as "end"
from papers
group by date_trunc('week', published);

-- Paper count per topic display title, over the `topics` array.
create view topic_counts as
select topic, count(*) as count
from papers, unnest(topics) as topic
group by topic;

-- The distinct arXiv category codes present across all papers.
create view category_list as
select distinct unnest(categories) as category from papers;

-- Expose the views to the browser roles. They read from `papers`, whose RLS already permits
-- public select, and they contain only public arXiv-derived aggregates.
grant select on week_summaries, topic_counts, category_list to anon, authenticated;
