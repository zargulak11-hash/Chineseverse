"""Outgoing email over SMTP (standard library only).

The project had no email infrastructure; this is the smallest piece that
works with any SMTP provider (Gmail/Workspace app password, Mailgun, SES
SMTP, Yandex, ...). All settings come from the environment (config.py
SMTP_*), nothing is hardcoded. Callers must treat failures as non-fatal:
an email is a copy of something already stored, never the source of truth.

Tests replace `send_email` (or `_transport`) instead of talking to a real
server.
"""

from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr, make_msgid

from app.config import settings


class EmailNotConfigured(Exception):
    """SMTP_HOST / SMTP_FROM not set: email is disabled on this server."""


class EmailSendError(Exception):
    """The provider refused or could not be reached. The message carries
    only the exception class, never credentials or the server's reply."""


def email_enabled() -> bool:
    return bool(settings.smtp_host and (settings.smtp_from or settings.smtp_username))


def _sender() -> str:
    return settings.smtp_from or formataddr(("ChineseVerse", settings.smtp_username or ""))


def _transport(msg: EmailMessage) -> None:
    timeout = settings.smtp_timeout_seconds
    security = (settings.smtp_security or "starttls").lower()
    if security == "ssl":
        server = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=timeout,
                                  context=ssl.create_default_context())
    else:
        server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=timeout)
    with server:
        if security == "starttls":
            server.starttls(context=ssl.create_default_context())
        if settings.smtp_username and settings.smtp_password:
            server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(msg)


def send_email(to: str, subject: str, text: str, html: str | None = None) -> None:
    if not email_enabled():
        raise EmailNotConfigured("SMTP is not configured")
    msg = EmailMessage()
    msg["From"] = _sender()
    msg["To"] = to
    msg["Subject"] = subject
    msg["Message-ID"] = make_msgid(domain="chineseverse")
    msg.set_content(text)
    if html:
        msg.add_alternative(html, subtype="html")
    try:
        _transport(msg)
    except (smtplib.SMTPException, OSError) as exc:
        # Deliberately drop str(exc): SMTP replies can echo the login name
        # or other account details; the class name is enough to diagnose.
        raise EmailSendError(type(exc).__name__) from None
