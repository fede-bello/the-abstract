-- Cost/usage tracking: one row per *paid* external call so the weekly digest's spend can be
-- rolled up. Two kinds are recorded: 'llm' (LiteLLM API completions, with token counts and the
-- LiteLLM-computed cost) and 'parse' (every LlamaParse job, with pages and an estimated cost from
-- config rates). Claude Code subscription completions are intentionally NOT recorded — they carry
-- no token data and cost $0 at the margin.

create table usage_events (
    id bigint generated always as identity primary key,
    created_at timestamptz not null default now(),
    kind text not null,                            -- 'llm' | 'parse'
    stage text,                                    -- classification | categorization | summarization | distribution | parsing
    model text,                                    -- LLM model id ('llm' rows)
    input_tokens int,                              -- 'llm' rows
    output_tokens int,                             -- 'llm' rows
    pages int,                                     -- 'parse' rows
    tier text,                                     -- LlamaParse tier ('parse' rows)
    cost_usd numeric(10, 6) not null default 0     -- LiteLLM-computed ('llm') or estimated ('parse')
);
create index usage_events_created_idx on usage_events (created_at);

-- Weekly roll-up for the `arxiv-digest usage` report.
create view weekly_usage as
select
    date_trunc('week', created_at)                          as week,
    count(*) filter (where kind = 'llm')                    as llm_calls,
    coalesce(sum(input_tokens), 0)                          as input_tokens,
    coalesce(sum(output_tokens), 0)                         as output_tokens,
    count(*) filter (where kind = 'parse')                  as parse_jobs,
    coalesce(sum(pages), 0)                                 as parse_pages,
    coalesce(sum(cost_usd) filter (where kind = 'llm'), 0)   as llm_cost_usd,
    coalesce(sum(cost_usd) filter (where kind = 'parse'), 0) as parse_cost_usd,
    coalesce(sum(cost_usd), 0)                              as total_cost_usd
from usage_events
group by 1
order by 1 desc;

-- RLS: usage is internal accounting, not public like papers. No anon/authenticated policy, so only
-- the table-owner role the backend connects with (which bypasses RLS) can read it — same as subscribers.
alter table usage_events enable row level security;
