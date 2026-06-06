"""Unit tests for the SMTP email client (aiosmtplib mocked at the send boundary)."""

import aiosmtplib
import pytest
from pydantic import SecretStr

from arxiv_digest.clients import email as email_client
from arxiv_digest.clients.email import EmailError, send_email
from arxiv_digest.config import settings


async def test_send_email_builds_html_message_and_passes_smtp_config(monkeypatch):
    captured = {}

    async def fake_send(message, **kwargs):
        captured["message"] = message
        captured["kwargs"] = kwargs

    monkeypatch.setattr(email_client.aiosmtplib, "send", fake_send)
    monkeypatch.setattr(settings, "email_from", "Digest <digest@x.com>")

    await send_email(to="me@x.com", subject="This Week", html="<p>hi</p>")

    message = captured["message"]
    assert message["To"] == "me@x.com"
    assert message["Subject"] == "This Week"
    assert message["From"] == "Digest <digest@x.com>"
    assert any(part.get_content_type() == "text/html" for part in message.get_payload())
    assert captured["kwargs"]["hostname"] == settings.smtp_host
    assert captured["kwargs"]["port"] == settings.smtp_port


async def test_send_email_from_falls_back_to_smtp_username(monkeypatch):
    captured = {}

    async def fake_send(message, **kwargs):
        captured["message"] = message

    monkeypatch.setattr(email_client.aiosmtplib, "send", fake_send)
    monkeypatch.setattr(settings, "email_from", "")
    monkeypatch.setattr(settings, "smtp_username", SecretStr("login@x.com"))

    await send_email(to="me@x.com", subject="s", html="<p>h</p>")

    assert captured["message"]["From"] == "login@x.com"


async def test_send_email_wraps_smtp_failure(monkeypatch):
    async def failing_send(message, **kwargs):
        msg = "connection refused"
        raise aiosmtplib.SMTPException(msg)

    monkeypatch.setattr(email_client.aiosmtplib, "send", failing_send)

    with pytest.raises(EmailError, match=r"failed to send digest to me@x.com"):
        await send_email(to="me@x.com", subject="s", html="<p>h</p>")
