-- Mailing list for the weekly digest (objective.md §7.3, §8): who receives the email
-- and which topics they care about.

create table subscribers (
    id bigint generated always as identity primary key,
    email text not null unique,
    interests text[] not null default '{}',   -- categorization topic titles; empty = all topics
    is_active boolean not null default true,
    created_at timestamptz not null default now()
);
create index subscribers_active_idx on subscribers (is_active);

-- RLS: subscriber emails are private (PII), unlike the public papers tables. No anon/authenticated
-- policy is defined, so only the table-owner role the backend connects with (which bypasses RLS)
-- can read them. Add a policy here if a future authenticated UI needs subscriber access.
alter table subscribers enable row level security;

-- Seeding is left out of version control (this repo is public). Add your own recipients in
-- Supabase Studio or a local, uncommitted SQL file, e.g.:
--   insert into subscribers (email) values ('you@example.com');                 -- all topics
--   insert into subscribers (email, interests) values ('you@example.com', '{LLMs,Reasoning}');
