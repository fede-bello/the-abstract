// Send mail over SMTP, reusing the same Gmail credentials as the weekly digest pipeline.
// Configured via function secrets: SMTP_USERNAME, SMTP_PASSWORD, and optionally SMTP_HOST /
// SMTP_PORT (default Gmail on 465/TLS). Low volume — one mail per signup or unsubscribe link.
import { SMTPClient } from 'https://deno.land/x/denomailer@1.6.0/mod.ts';

export async function sendEmail(to: string, subject: string, html: string): Promise<void> {
  const username = Deno.env.get('SMTP_USERNAME');
  const password = Deno.env.get('SMTP_PASSWORD');
  if (!username || !password) {
    throw new Error('SMTP_USERNAME and SMTP_PASSWORD must be set as function secrets');
  }
  const hostname = Deno.env.get('SMTP_HOST') ?? 'smtp.gmail.com';
  const port = Number(Deno.env.get('SMTP_PORT') ?? '465');

  const client = new SMTPClient({
    connection: {
      hostname,
      port,
      // Port 465 is implicit TLS; 587 upgrades via STARTTLS (tls: false lets denomailer do that).
      tls: port === 465,
      auth: { username, password },
    },
  });
  try {
    await client.send({ from: username, to, subject, content: 'text/html', html });
  } finally {
    await client.close();
  }
}
