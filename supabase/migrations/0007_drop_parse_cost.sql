-- Parsing moved from LlamaParse (cloud, tiered, billed) to LiteParse (local, free). Parse rows
-- now track pages only, with no tier and no cost. Drop the vestigial `tier` column and remove
-- `parse_cost_usd` from the weekly roll-up; `parse_jobs`/`parse_pages` stay for volume tracking.
-- (The view must be dropped and recreated — Postgres can't drop a column a view depends on.)

drop view weekly_usage;

alter table usage_events drop column tier;

create view weekly_usage as
select
    date_trunc('week', created_at)                          as week,
    count(*) filter (where kind = 'llm')                    as llm_calls,
    coalesce(sum(input_tokens), 0)                          as input_tokens,
    coalesce(sum(output_tokens), 0)                         as output_tokens,
    count(*) filter (where kind = 'parse')                  as parse_jobs,
    coalesce(sum(pages), 0)                                 as parse_pages,
    coalesce(sum(cost_usd) filter (where kind = 'llm'), 0)  as llm_cost_usd,
    coalesce(sum(cost_usd), 0)                              as total_cost_usd
from usage_events
group by 1
order by 1 desc;
