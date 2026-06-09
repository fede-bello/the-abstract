// A minimal self-contained HTML page for the confirm/unsubscribe link landings (these are
// opened directly in the browser from an email, so they return a page, not JSON).
export function htmlPage(title: string, message: string, status = 200): Response {
  const body = `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>${title}</title>
<style>
  body { font-family: Helvetica, Arial, sans-serif; background: #faf9f5; color: #111;
         display: grid; place-items: center; min-height: 100vh; margin: 0; }
  main { max-width: 30rem; padding: 2rem; text-align: center; }
  h1 { font-size: 1.4rem; margin: 0 0 0.5rem; }
  p { color: #54534e; line-height: 1.6; }
</style>
</head>
<body><main><h1>${title}</h1><p>${message}</p></main></body>
</html>`;
  return new Response(body, { status, headers: { 'content-type': 'text/html; charset=utf-8' } });
}
