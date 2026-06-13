// A small, self-contained, on-brand HTML page for the confirm/unsubscribe link landings (these
// are opened directly in the browser from an email, so they return a styled page, not JSON).
// Colors/typography mirror the SPA's "Modern Scientific" look (warm off-white, ink, one electric
// accent, sharp edges) without depending on the app's web fonts. If SITE_URL is set as a function
// secret, a button back to the site is shown.
function escapeHtml(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

export function htmlPage(title: string, message: string, status = 200): Response {
  const siteUrl = Deno.env.get('SITE_URL');
  const cta = siteUrl
    ? `<a class="cta" href="${escapeHtml(siteUrl)}">Read the latest digest &rarr;</a>`
    : '';
  const body = `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>${escapeHtml(title)} · the abstract</title>
<style>
  :root { color-scheme: light dark; }
  * { box-sizing: border-box; }
  body { font-family: system-ui, -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif;
         background: #faf9f5; color: #0a0a0a;
         display: grid; place-items: center; min-height: 100vh; margin: 0; padding: 1.5rem; }
  main { max-width: 30rem; width: 100%; text-align: left;
         border-top: 4px solid #0034ff; background: #fff; padding: 2.5rem 2rem;
         box-shadow: 0 1px 0 rgba(10,10,10,0.04); }
  .brand { font-family: ui-monospace, 'Space Mono', monospace; font-size: 0.75rem;
           letter-spacing: 0.14em; text-transform: uppercase; color: #54534e; margin: 0 0 1.5rem; }
  .brand b { color: #0034ff; font-weight: 700; }
  h1 { font-size: 1.6rem; line-height: 1.15; letter-spacing: -0.02em; margin: 0 0 0.75rem; }
  p.msg { color: #54534e; line-height: 1.6; font-size: 1rem; margin: 0; }
  .cta { display: inline-block; margin-top: 1.75rem; background: #0034ff; color: #fff;
         text-decoration: none; font-weight: 700; padding: 0.7rem 1.1rem; font-size: 0.95rem; }
  .cta:hover { opacity: 0.85; }
  @media (prefers-color-scheme: dark) {
    body { background: #0e0e0c; color: #f3f2ec; }
    main { background: #181815; border-top-color: #5b7bff; }
    .brand { color: #a3a299; } .brand b { color: #5b7bff; }
    p.msg { color: #a3a299; }
    .cta { background: #5b7bff; color: #0b0e1f; }
  }
</style>
</head>
<body>
  <main>
    <p class="brand"><b>the abstract</b> — weekly arXiv ML digest</p>
    <h1>${escapeHtml(title)}</h1>
    <p class="msg">${escapeHtml(message)}</p>
    ${cta}
  </main>
</body>
</html>`;
  return new Response(body, { status, headers: { 'content-type': 'text/html; charset=utf-8' } });
}
