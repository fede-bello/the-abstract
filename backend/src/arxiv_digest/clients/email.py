"""Email client: send the weekly HTML digest over SMTP.

Async SMTP via ``aiosmtplib``. Host/port/TLS come from ``config.toml`` and credentials from
the environment, so the same client targets Gmail (the default) or any other provider without
code changes. The ``From`` address defaults to ``email_from``, falling back to the SMTP username.
"""

from email.message import EmailMessage

import aiosmtplib

from arxiv_digest.config import settings

_TEXT_FALLBACK = "This is the weekly arXiv ML digest. View it in an HTML-capable email client."


class EmailError(RuntimeError):
    """Raised when sending an email over SMTP fails."""


def _from_address() -> str:
    """The configured sender, falling back to the SMTP login when ``email_from`` is blank."""
    return settings.email_from or settings.smtp_username.get_secret_value()


async def send_email(*, to: str, subject: str, html: str) -> None:
    """Send one HTML email (with a plain-text fallback) to a single recipient."""
    message = EmailMessage()
    message["From"] = _from_address()
    message["To"] = to
    message["Subject"] = subject
    message.set_content(_TEXT_FALLBACK)
    message.add_alternative(html, subtype="html")
    try:
        await aiosmtplib.send(
            message,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            start_tls=settings.smtp_starttls,
            username=settings.smtp_username.get_secret_value(),
            password=settings.smtp_password.get_secret_value(),
        )
    except aiosmtplib.SMTPException as exc:
        msg = f"failed to send digest to {to}: {exc}"
        raise EmailError(msg) from exc
