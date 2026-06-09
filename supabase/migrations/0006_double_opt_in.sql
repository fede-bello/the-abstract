-- Double opt-in + unsubscribe.
--
-- Signups now start inactive (pending) and only receive the digest after confirming via an
-- emailed link. Confirm and unsubscribe each use an unguessable token. Signup flows through the
-- `subscribe` Edge Function (service role), so the public anon INSERT path from 0005 is removed.
--
-- Lifecycle on `is_active`: signup -> false (pending), confirm -> true, unsubscribe -> false.
-- `confirmed_at` distinguishes "never confirmed" from "unsubscribed after confirming".

alter table subscribers
    add column confirmed_at timestamptz,
    add column confirm_token uuid not null default gen_random_uuid(),
    add column unsubscribe_token uuid not null default gen_random_uuid();

create unique index subscribers_confirm_token_idx on subscribers (confirm_token);
create unique index subscribers_unsubscribe_token_idx on subscribers (unsubscribe_token);

-- Rows added manually before double opt-in are treated as already confirmed.
update subscribers set confirmed_at = now() where is_active = true and confirmed_at is null;

-- Signup is server-side now (the Edge Function uses the service role), so drop the public insert
-- policy and grant added in 0005. The email-format check constraint stays.
drop policy if exists "public signup" on subscribers;
revoke insert on table subscribers from anon, authenticated;
