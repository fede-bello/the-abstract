// The confirm/unsubscribe links are opened in a browser from an email, but Edge Functions can't
// serve a rendered HTML page from the *.supabase.co domain — the gateway forces `text/plain` plus
// a sandbox CSP (an anti-phishing measure), so any HTML shows up as raw source. Instead, each
// handler does its DB work and redirects here to the SPA's /subscription route, which renders a
// proper on-brand status page. Falls back to plain text if SITE_URL isn't configured.
export type SubscriptionStatus =
  | 'confirmed'
  | 'already-confirmed'
  | 'unsubscribed'
  | 'invalid'
  | 'error';

export function statusRedirect(status: SubscriptionStatus): Response {
  const siteUrl = Deno.env.get('SITE_URL');
  if (siteUrl) {
    const base = siteUrl.replace(/\/+$/, '');
    return Response.redirect(`${base}/subscription?status=${status}`, 303);
  }
  // No site configured: a plain-text body renders fine even under the forced text/plain.
  return new Response(`Subscription: ${status}.`, {
    status: 200,
    headers: { 'content-type': 'text/plain; charset=utf-8' },
  });
}
