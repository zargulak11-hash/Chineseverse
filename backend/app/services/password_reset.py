"""Setting a password without knowing the old one: the emailed "forgot
password" link, and the shared rules for any newly chosen password.

There was no way back into an account whose password was forgotten, and an
account created with Google or GitHub had a random password nobody ever
knew -- so it could not sign in anywhere only passwords work (the Android
app). Two ways now prove the account is yours instead of the old password:
a fresh Google sign-in (routers/auth.py, POST /api/auth/google/password),
or control of the account's email address (this module).

The email link, step by step:

- request_reset() answers the same for every address: whether an account
  exists is never revealed, and the email itself goes out in the
  background, so the response time doesn't tell either.
- The token is 32 random bytes; only its SHA-256 is stored, so a leaked
  database can't reset anyone's password. It lives 30 minutes, works once,
  and asking again (or resetting) spends every older unused link.
- The link carries it in the URL fragment (/reset-password#token=...),
  which browsers never send to a server: it can't land in nginx's access
  log or a Referer header. Nothing here logs it.
- Requests are capped per account (3 an hour, counted in the database) and
  per public address (10 an hour, in-process like the login throttle), so
  the form can't be used to flood someone's inbox.
- A reset sets password_changed_at, which ends every session opened before
  it (deps.get_current_user), clears the account's login lockout, and
  signs the learner in with a fresh token.
"""

from __future__ import annotations

import hashlib
import html
import logging
import secrets
import threading
import time
from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models
from app.config import settings
from app.security import hash_password
from app.services import email as mailer
from app.services import login_throttle

log = logging.getLogger(__name__)

TOKEN_TTL = timedelta(minutes=30)
ACCOUNT_LIMIT_PER_HOUR = 3
IP_LIMIT_PER_HOUR = 10

# The same rule as registration (schemas.RegisterRequest.password) and
# Settings -> Change password (routers/me.py).
PASSWORD_MIN, PASSWORD_MAX = 6, 128

UNAVAILABLE = "Password reset by email isn't available right now"
INVALID_LINK = "This reset link is invalid or was already used"
EXPIRED_LINK = "This reset link has expired"


class ResetError(Exception):
    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status = status
        self.detail = detail


def new_password_problem(new: str, confirm: str) -> str | None:
    """The `detail` for a new password that can't be used, else None. The
    same sentences as Settings -> Change password, already translated by
    the frontend (apiErrors.js)."""
    if len(new) < PASSWORD_MIN:
        return "The new password must be at least 6 characters"
    if len(new) > PASSWORD_MAX:
        return "The new password must be at most 128 characters"
    if new != confirm:
        return "The new passwords don't match"
    return None


def set_password(db: Session, user: models.User, new: str) -> None:
    """Store a newly chosen password and end every older session. Does not
    commit. Whole seconds, like a token's `iat`
    (security.token_predates_password_change)."""
    user.password_hash = hash_password(new)
    user.password_changed_at = datetime.utcnow().replace(microsecond=0)
    login_throttle.record_success(user.username, None)


def available() -> bool:
    """Whether this server can send the email at all (SMTP configured)."""
    return mailer.email_enabled()


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


_ip_guard = threading.Lock()
_ip_hits: dict[str, list[float]] = {}
_now = time.monotonic  # replaced in tests


def _ip_allowed(ip: str | None) -> bool:
    # Only public addresses: a private one is our own proxy or a shared NAT
    # (see login_throttle), and limiting it would limit everyone behind it.
    if not login_throttle._is_global(ip):
        return True
    now = _now()
    with _ip_guard:
        hits = [t for t in _ip_hits.get(ip, []) if now - t < 3600]
        if len(hits) >= IP_LIMIT_PER_HOUR:
            _ip_hits[ip] = hits
            return False
        hits.append(now)
        _ip_hits[ip] = hits
        if len(_ip_hits) > 50_000:  # a flood of addresses must not grow memory forever
            _ip_hits.clear()
        return True


def reset_limits() -> None:
    """Tests: forget the per-address counters."""
    with _ip_guard:
        _ip_hits.clear()


def _find_account(db: Session, email: str) -> models.User | None:
    # Same matching as sign-in by email (routers/auth._find_by_email):
    # exact first, then the oldest case-insensitive match.
    exact = db.query(models.User).filter(models.User.email == email).first()
    if exact is not None:
        return exact
    return (
        db.query(models.User)
        .filter(func.lower(models.User.email) == email.lower())
        .order_by(models.User.id)
        .first()
    )


def request_reset(db: Session, email: str, ip: str | None, locale: str) -> tuple[str, str, str, str] | None:
    """Create a reset link for the account with this email, if there is one
    and it may have one now. Returns (address, username, token, locale) --
    send_reset_email's arguments, to be run AFTER the response -- or None.
    The caller answers the same either way."""
    if not _ip_allowed(ip):
        return None
    user = _find_account(db, email.strip())
    if user is None or not user.is_active or not user.email:
        return None
    now = datetime.utcnow()
    recent = (
        db.query(func.count(models.PasswordResetToken.id))
        .filter(
            models.PasswordResetToken.user_id == user.id,
            models.PasswordResetToken.created_at >= now - timedelta(hours=1),
        )
        .scalar()
    )
    if recent >= ACCOUNT_LIMIT_PER_HOUR:
        return None
    # Only the newest link works.
    _spend_open_tokens(db, user.id, now)
    token = secrets.token_urlsafe(32)
    db.add(models.PasswordResetToken(
        user_id=user.id, token_hash=_hash(token), created_at=now, expires_at=now + TOKEN_TTL,
    ))
    db.commit()
    lang = locale if locale in _EMAIL else (user.locale if user.locale in _EMAIL else "en")
    # Always the registered address from the database, never the typed one.
    return user.email, user.username, token, lang


def _spend_open_tokens(db: Session, user_id: int, now: datetime) -> None:
    db.query(models.PasswordResetToken).filter(
        models.PasswordResetToken.user_id == user_id,
        models.PasswordResetToken.used_at.is_(None),
    ).update({models.PasswordResetToken.used_at: now}, synchronize_session=False)


def spend_open_links(db: Session, user: models.User) -> None:
    """Make every reset link already sent for this account unusable (an
    admin moved it to another address). A link went to the address the
    account had THEN; left open, it could reset the account and mark the
    new, never-proven address as verified (reset_password). Does not
    commit."""
    _spend_open_tokens(db, user.id, datetime.utcnow())


def _usable(db: Session, token: str) -> models.PasswordResetToken:
    row = None
    if token and len(token) <= 128:
        row = (
            db.query(models.PasswordResetToken)
            .filter(models.PasswordResetToken.token_hash == _hash(token))
            .first()
        )
    if row is None or row.used_at is not None or row.user is None or not row.user.is_active:
        raise ResetError(400, INVALID_LINK)
    if row.expires_at <= datetime.utcnow():
        raise ResetError(400, EXPIRED_LINK)
    return row


def check_token(db: Session, token: str) -> None:
    """Raises ResetError for a link that can't be used, so the page can say
    so before the learner types a new password."""
    _usable(db, token)


def reset_password(db: Session, token: str, new: str, confirm: str) -> models.User:
    row = _usable(db, token)
    problem = new_password_problem(new, confirm)
    if problem:
        raise ResetError(422, problem)
    user = row.user
    now = datetime.utcnow()
    # Spend this link and any other open one (sets used_at on this row too).
    _spend_open_tokens(db, user.id, now)
    set_password(db, user, new)
    # The link went to the account's own address, so whoever opened it
    # controls that address: Google/GitHub sign-in may now join this account
    # by email (routers/auth._link_by_email). For an address someone else
    # registered, this same reset is what took the account back -- their
    # password and sessions just ended.
    if user.email_verified_at is None:
        user.email_verified_at = now
    db.commit()
    db.refresh(user)
    return user


_EMAIL = {
    "en": {
        "subject": "Reset your ChineseVerse password",
        "line": "Someone asked to reset the password of the ChineseVerse account {name}. To choose a new password, open this link within 30 minutes:",
        "cta": "Choose a new password",
        "footer": "If it wasn't you, ignore this email: your password stays the same. Never share this link.",
    },
    "ru": {
        "subject": "Сброс пароля ChineseVerse",
        "line": "Кто-то запросил сброс пароля аккаунта ChineseVerse {name}. Чтобы задать новый пароль, откройте ссылку в течение 30 минут:",
        "cta": "Задать новый пароль",
        "footer": "Если это были не вы, просто проигнорируйте письмо: пароль не изменится. Никому не пересылайте эту ссылку.",
    },
    "tg": {
        "subject": "Барқарор кардани пароли ChineseVerse",
        "line": "Касе барқарор кардани пароли ҳисоби ChineseVerse {name}-ро дархост кард. Барои интихоби пароли нав ин пайвандро дар давоми 30 дақиқа кушоед:",
        "cta": "Пароли нав интихоб кунед",
        "footer": "Агар ин шумо набудед, ин мактубро нодида гиред: пароли шумо тағйир намеёбад. Ин пайвандро ба касе надиҳед.",
    },
    "zh": {
        "subject": "重置你的 ChineseVerse 密码",
        "line": "有人申请重置 ChineseVerse 账户 {name} 的密码。请在 30 分钟内打开下面的链接设置新密码：",
        "cta": "设置新密码",
        "footer": "如果不是你本人操作，请忽略这封邮件，你的密码不会改变。请勿把此链接分享给任何人。",
    },
}


def reset_link(token: str) -> str:
    return f"{settings.public_app_url.rstrip('/')}/reset-password#token={token}"


def render_reset_email(username: str, token: str, lang: str) -> tuple[str, str, str]:
    tpl = _EMAIL.get(lang, _EMAIL["en"])
    url = reset_link(token)
    line = tpl["line"].format(name=username)
    text = f"{line}\n\n{url}\n\n— ChineseVerse\n{tpl['footer']}\n"
    body = (
        '<div style="font-family:Arial,Helvetica,sans-serif;font-size:15px;color:#251d10;max-width:520px">'
        f"<p>{html.escape(tpl['line']).format(name='<b>' + html.escape(username) + '</b>')}</p>"
        f'<p><a href="{html.escape(url)}" style="display:inline-block;padding:10px 16px;background:#c9974a;'
        f'color:#1c1409;border-radius:8px;text-decoration:none;font-weight:bold">{html.escape(tpl["cta"])}</a></p>'
        f'<p style="color:#6b5f42;font-size:12px">— ChineseVerse<br>{html.escape(tpl["footer"])}</p>'
        "</div>"
    )
    return tpl["subject"], text, body


def send_reset_email(address: str, username: str, token: str, lang: str) -> None:
    """Run after the response. A failure is logged without the token or
    the address; the learner can ask again."""
    subject, text, body = render_reset_email(username, token, lang)
    try:
        mailer.send_email(address, subject, text, body)
    except (mailer.EmailSendError, mailer.EmailNotConfigured) as exc:
        log.warning("password reset email failed (%s)", exc)
