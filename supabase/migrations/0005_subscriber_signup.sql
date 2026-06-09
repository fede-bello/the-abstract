-- Public newsletter signup: let the web app (anon key) add a subscriber by email.
--
-- Emails stay private: 0002 enabled RLS with no SELECT policy, and this only adds INSERT, so
-- anon can add itself to the list but can never read it back. The pipeline still reads the list
-- via the table-owner role, which bypasses RLS. The WITH CHECK pins anon inserts to an email-only
-- signup (active, all topics) — anyone wanting topic filters is added manually for now.
--
-- Trade-off (accepted): with no double opt-in, anyone can submit any address. The format check +
-- unique email are the only guards; add a confirmation step / captcha later if abused.

alter table subscribers
    add constraint subscribers_email_format
    check (email ~* '^[^@[:space:]]+@[^@[:space:]]+\.[^@[:space:]]+$');

grant insert on table subscribers to anon, authenticated;

create policy "public signup" on subscribers
    for insert to anon, authenticated
    with check (is_active = true and interests = '{}'::text[]);
