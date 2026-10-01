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

import re
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


def _clean(value: str | None) -> str | None:
    """.env values pasted with surrounding quotes or stray spaces (older
    docker compose passes quotes through literally) would otherwise become
    part of the host / login / password and fail authentication."""
    if value is None:
        return None
    v = value.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        v = v[1:-1].strip()
    return v or None


def _host() -> str | None:
    return _clean(settings.smtp_host)


def _username() -> str | None:
    return _clean(settings.smtp_username)


def _password() -> str | None:
    pw = _clean(settings.smtp_password)
    # Google shows app passwords as "abcd efgh ijkl mnop"; the spaces are
    # only for display and are not part of the password.
    if pw and (_host() or "").lower().endswith(("gmail.com", "googlemail.com")):
        pw = pw.replace(" ", "")
    return pw


def _from() -> str | None:
    return _clean(settings.smtp_from)


def effective_security() -> str:
    """ssl | starttls | none. Port 465 is implicit TLS by definition: talking
    STARTTLS to it just hangs until the timeout, so it always means ssl.
    Unknown values (e.g. "tls", "true") fall back to starttls rather than
    to an unencrypted session the provider would refuse to AUTH over."""
    raw = (_clean(settings.smtp_security) or "starttls").lower()
    if settings.smtp_port == 465 or raw in ("ssl", "smtps", "implicit"):
        return "ssl"
    if raw in ("none", "plain", "off"):
        return "none"
    return "starttls"


# The variables a server needs for notification email. The first four have
# no usable default; the rest fall back to config.py defaults.
REQUIRED_VARS = ("SMTP_HOST", "SMTP_USERNAME", "SMTP_PASSWORD", "SMTP_FROM")
DEFAULTED_VARS = ("SMTP_PORT", "SMTP_SECURITY", "SMTP_TIMEOUT_SECONDS", "PUBLIC_APP_URL")


def config_report() -> dict:
    """Which SMTP variables THIS process actually received -- from the
    container environment (docker compose env_file) or a .env next to the
    app -- as names and booleans only, never values. "default" means the
    variable is absent and config.py's default is in use."""
    import os

    try:
        from dotenv import dotenv_values

        file_vals = dotenv_values(".env")
    except Exception:  # no .env in the image is normal under compose
        file_vals = {}

    def present(name: str) -> bool:
        return bool((os.environ.get(name) or file_vals.get(name) or "").strip())

    values = {
        "SMTP_HOST": _host(), "SMTP_USERNAME": _username(),
        "SMTP_PASSWORD": _password(), "SMTP_FROM": _from(),
    }
    report = {name: ("configured" if values[name] else "missing") for name in REQUIRED_VARS}
    for name in DEFAULTED_VARS:
        report[name] = "configured" if present(name) else "default"
    return report


def missing_vars() -> list[str]:
    return [name for name, state in config_report().items() if state == "missing"]


def email_enabled() -> bool:
    return bool(_host() and (_from() or _username()))


def _sender() -> str:
    return _from() or formataddr(("ChineseVerse", _username() or ""))


def _transport(msg: EmailMessage) -> None:
    timeout = settings.smtp_timeout_seconds
    security = effective_security()
    if security == "ssl":
        server = smtplib.SMTP_SSL(_host(), settings.smtp_port, timeout=timeout,
                                  context=ssl.create_default_context())
    else:
        server = smtplib.SMTP(_host(), settings.smtp_port, timeout=timeout)
    with server:
        if security == "starttls":
            server.starttls(context=ssl.create_default_context())
        if _username() and _password():
            server.login(_username(), _password())
        server.send_message(msg)


_ADDRESS = re.compile(r"[^\s<>()\[\]\"',;:]+@[^\s<>()\[\]\"',;:]+")


def describe_error(exc: BaseException) -> str:
    """A diagnosable but credential-free description of a send failure:
    the exception class, plus the SMTP reply code and text when the
    provider sent one (e.g. Gmail's "535 5.7.8 Username and Password not
    accepted"). Anything that could echo account details -- the login, the
    password, the sender, any email address -- is masked first."""
    out = type(exc).__name__
    if isinstance(exc, smtplib.SMTPResponseException):
        text = exc.smtp_error
        if isinstance(text, bytes):
            text = text.decode("utf-8", "replace")
        text = " ".join(str(text).split())
        for secret in (_password(), settings.smtp_password, _username(), _from()):
            if secret:
                text = text.replace(secret, "***")
        text = _ADDRESS.sub("<address>", text)
        out = f"{out} {exc.smtp_code} {text}"
    elif isinstance(exc, (TimeoutError, ConnectionError, ssl.SSLError, OSError)) and getattr(exc, "errno", None):
        out = f"{out} errno {exc.errno}"
    return out[:200]


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
        # Never str(exc): SMTP replies can echo the login name or other
        # account details. describe_error() keeps the code + masked text.
        raise EmailSendError(describe_error(exc)) from None
