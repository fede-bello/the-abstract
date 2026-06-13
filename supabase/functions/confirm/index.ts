// GET ?token=<confirm_token> — confirm a pending subscription (opened from the email link).
// Deploy with --no-verify-jwt: it's visited directly from an email, with no auth header. Redirects
// to the SPA's /subscription page for the user-facing result (see _shared/redirect.ts).
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

import { statusRedirect } from '../_shared/redirect.ts';

Deno.serve(async (req) => {
  const token = new URL(req.url).searchParams.get('token');
  if (!token) return statusRedirect('invalid');

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
  if (error) return statusRedirect('error');

  // No row updated: either the token is bogus, or it was already confirmed. Confirm the latter.
  if (!data) {
    const { data: existing } = await supabase
      .from('subscribers')
      .select('email')
      .eq('confirm_token', token)
      .maybeSingle();
    if (!existing) return statusRedirect('invalid');
    return statusRedirect('already-confirmed');
  }

  return statusRedirect('confirmed');
});
