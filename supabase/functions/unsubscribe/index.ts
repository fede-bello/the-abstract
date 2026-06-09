// GET ?token=<unsubscribe_token> — remove a subscriber from the list (link in every digest).
// Deploy with --no-verify-jwt: it's visited directly from an email, with no auth header.
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

import { htmlPage } from '../_shared/page.ts';

Deno.serve(async (req) => {
  const token = new URL(req.url).searchParams.get('token');
  if (!token) return htmlPage('Invalid link', 'This unsubscribe link is missing its token.', 400);

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
  if (error) return htmlPage('Something went wrong', 'Please try the link again later.', 500);
  if (!data) return htmlPage('Invalid link', 'This unsubscribe link is not valid.', 404);

  return htmlPage('Unsubscribed', "You won't receive the digest anymore. Re-subscribe anytime from the site.");
});
