// POST { email } — start a double opt-in signup.
//
// Upserts a pending (is_active=false) subscriber and emails a confirmation link. Idempotent:
// re-submitting a pending email re-sends the link; an already-confirmed email is reported back
// without sending. Uses the service role (bypasses RLS) since `subscribers` is private.
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

import { corsHeaders } from '../_shared/cors.ts';
import { sendEmail } from '../_shared/email.ts';

const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

function json(body: Record<string, unknown>, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...corsHeaders, 'content-type': 'application/json' },
  });
}

function confirmationEmail(confirmUrl: string): string {
  return `<div style="max-width:520px;margin:0 auto;font-family:Helvetica,Arial,sans-serif;color:#111;">
    <h1 style="font-size:20px;">Confirm your subscription</h1>
    <p style="color:#333;line-height:1.6;">Click below to start receiving the weekly arXiv ML digest.
    If you didn't request this, just ignore this email — you won't be added.</p>
    <p style="margin:24px 0;"><a href="${confirmUrl}"
      style="background:#0034ff;color:#fff;text-decoration:none;padding:12px 20px;border-radius:4px;
      display:inline-block;font-weight:bold;">Confirm subscription</a></p>
    <p style="font-size:12px;color:#999;">Or paste this link: ${confirmUrl}</p>
  </div>`;
}

Deno.serve(async (req) => {
  if (req.method === 'OPTIONS') return new Response('ok', { headers: corsHeaders });
  if (req.method !== 'POST') return json({ error: 'method not allowed' }, 405);

  let email: unknown;
  try {
    email = (await req.json())?.email;
  } catch {
    return json({ error: 'invalid JSON body' }, 400);
  }
  if (typeof email !== 'string' || !EMAIL_RE.test(email)) {
    return json({ error: 'invalid email' }, 400);
  }
  const normalized = email.trim().toLowerCase();

  const supabase = createClient(
    Deno.env.get('SUPABASE_URL')!,
    Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!,
  );

  // Already on the list?
  const { data: existing, error: lookupError } = await supabase
    .from('subscribers')
    .select('confirm_token, confirmed_at')
    .eq('email', normalized)
    .maybeSingle();
  if (lookupError) return json({ error: 'lookup failed' }, 500);

  let confirmToken = existing?.confirm_token as string | undefined;
  if (existing?.confirmed_at) {
    return json({ status: 'already-subscribed' });
  }
  if (!existing) {
    // New pending subscriber; `is_active` stays false until confirmed.
    const { data: inserted, error: insertError } = await supabase
      .from('subscribers')
      .insert({ email: normalized, is_active: false })
      .select('confirm_token')
      .single();
    if (insertError) return json({ error: 'signup failed' }, 500);
    confirmToken = inserted.confirm_token as string;
  }

  const confirmUrl = `${Deno.env.get('SUPABASE_URL')}/functions/v1/confirm?token=${confirmToken}`;
  try {
    await sendEmail(normalized, 'Confirm your arXiv ML digest subscription', confirmationEmail(confirmUrl));
  } catch (_err) {
    return json({ error: 'could not send confirmation email' }, 502);
  }
  return json({ status: 'confirmation-sent' });
});
