// GET ?token=<unsubscribe_token> — remove a subscriber from the list (link in every digest).
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

  // Deactivate (idempotent — re-clicking stays unsubscribed). Keep the row so re-subscribing works.
  const { data, error } = await supabase
    .from('subscribers')
    .update({ is_active: false })
    .eq('unsubscribe_token', token)
    .select('email')
    .maybeSingle();
  if (error) return statusRedirect('error');
  if (!data) return statusRedirect('invalid');

  return statusRedirect('unsubscribed');
});
