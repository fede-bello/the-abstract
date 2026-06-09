// GET ?token=<confirm_token> — confirm a pending subscription (opened from the email link).
// Deploy with --no-verify-jwt: it's visited directly from an email, with no auth header.
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

import { htmlPage } from '../_shared/page.ts';

Deno.serve(async (req) => {
  const token = new URL(req.url).searchParams.get('token');
  if (!token) return htmlPage('Invalid link', 'This confirmation link is missing its token.', 400);

  const supabase = createClient(
    Deno.env.get('SUPABASE_URL')!,
    Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!,
  );

  // Activate only if still pending; an already-confirmed token returns no row but is still a success.
  const { data, error } = await supabase
    .from('subscribers')
    .update({ is_active: true, confirmed_at: new Date().toISOString() })
    .eq('confirm_token', token)
    .is('confirmed_at', null)
    .select('email')
    .maybeSingle();
  if (error) return htmlPage('Something went wrong', 'Please try the link again later.', 500);

  // No row updated: either the token is bogus, or it was already confirmed. Confirm the latter.
  if (!data) {
    const { data: existing } = await supabase
      .from('subscribers')
      .select('email')
      .eq('confirm_token', token)
      .maybeSingle();
    if (!existing) return htmlPage('Invalid link', 'This confirmation link is not valid.', 404);
    return htmlPage("You're already confirmed", 'You are on the list for the weekly digest.');
  }

  return htmlPage("You're subscribed", 'Thanks for confirming — the next digest lands Monday.');
});
