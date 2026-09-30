"""Persistent in-app notifications and their email copies.

Flow for a follow (routers/social.py):

    follow row + Notification row  -> ONE commit (both or neither)
    response returned               -> BackgroundTasks runs deliver_email()
    deliver_email                   -> own DB session, atomically claims the
                                       row, mails the recipient's registered
                                       address in their last-used language,
                                       records sent / failed / skipped

The notification row is the source of truth: it exists whether or not the
recipient is online, and whether or not the email ever goes out. Email is
best-effort with retries (a few in-process attempts, then a sweep on the
next startup), and can never undo the follow or the notification.
"""

from __future__ import annotations

import html
import logging
import threading
import time
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app import models
from app.config import settings
from app.database import SessionLocal
from app.services import email as mailer

log = logging.getLogger("app.notifications")

FOLLOW = "follow"
TYPES = (FOLLOW,)
UI_LOCALES = ("en", "ru", "tg", "zh")

# Following, unfollowing and following again must not become a way to spam
# someone's inbox: one "followed you" per follower per day at most.
RENOTIFY_AFTER = timedelta(hours=24)

# Delivery attempts inside one background run (seconds to wait before each
# retry), and the lifetime cap across runs / restarts.
RETRY_DELAYS = (2, 10)
MAX_EMAIL_ATTEMPTS = 6
SWEEP_MAX_AGE = timedelta(days=3)


# --------------------------------------------------------------------------- creating

def create_follow_notification(db: Session, actor: models.User, recipient: models.User) -> models.Notification | None:
    """Adds (does not commit) a FOLLOW notification, unless this actor
    already notified this recipient within RENOTIFY_AFTER. The caller
    commits it together with the follow row."""
    if actor.id == recipient.id:
        return None
    recent = (
        db.query(models.Notification.id)
        .filter(
            models.Notification.recipient_id == recipient.id,
            models.Notification.actor_id == actor.id,
            models.Notification.type == FOLLOW,
            models.Notification.created_at >= datetime.utcnow() - RENOTIFY_AFTER,
        )
        .first()
    )
    if recent is not None:
        return None
    n = models.Notification(recipient_id=recipient.id, actor_id=actor.id, type=FOLLOW)
    db.add(n)
    return n


# --------------------------------------------------------------------------- reading

def serialize(n: models.Notification) -> dict:
    """What the recipient sees. The actor is resolved live (current
    username/avatar), and the text is built client-side in the reader's
    language from `type` + `actor`. Email bookkeeping is never exposed."""
    actor = n.actor
    return {
        "id": n.id,
        "type": n.type,
        "actor": (
            {
                "id": actor.id,
                "username": actor.username,
                "avatar_url": actor.profile.avatar_url if actor.profile else None,
            }
            if actor is not None
            else None
        ),
        "read": n.read_at is not None,
        "read_at": n.read_at,
        "created_at": n.created_at,
        "link": f"/u/{actor.id}" if actor is not None and n.type == FOLLOW else None,
    }


def unread_count(db: Session, user: models.User) -> int:
    return (
        db.query(models.Notification)
        .filter(models.Notification.recipient_id == user.id, models.Notification.read_at.is_(None))
        .count()
    )


def remember_locale(db: Session, user: models.User, raw: str | None) -> None:
    """Store the UI language the learner is using now, so emails sent while
    they are away use it. Only an explicit, known header value counts."""
    loc = (raw or "").strip().lower()
    if loc in UI_LOCALES and user.locale != loc:
        user.locale = loc
        db.commit()


# --------------------------------------------------------------------------- email

_EMAIL = {
    "en": {
        "subject": "You have a new follower on ChineseVerse",
        "line": "{name} followed you on ChineseVerse.",
        "cta": "View their profile",
        "footer": "You are receiving this because someone followed your ChineseVerse account.",
    },
    "ru": {
        "subject": "У вас новый подписчик в ChineseVerse",
        "line": "{name} теперь подписан(а) на вас в ChineseVerse.",
        "cta": "Открыть профиль",
        "footer": "Вы получили это письмо, потому что на ваш аккаунт ChineseVerse подписались.",
    },
    "tg": {
        "subject": "Дар ChineseVerse шумо пайрави нав доред",
        "line": "{name} шуморо дар ChineseVerse пайравӣ кард.",
        "cta": "Дидани профил",
        "footer": "Шумо ин мактубро гирифтед, зеро касе аккаунти ChineseVerse-и шуморо пайравӣ кард.",
    },
    "zh": {
        "subject": "你在 ChineseVerse 有了新的关注者",
        "line": "{name} 在 ChineseVerse 上关注了你。",
        "cta": "查看对方主页",
        "footer": "你收到这封邮件，是因为有人关注了你的 ChineseVerse 账号。",
    },
}


def render_email(n: models.Notification) -> tuple[str, str, str]:
    """(subject, text, html) for the recipient, in their last-used language."""
    loc = n.recipient.locale if n.recipient.locale in _EMAIL else "en"
    tpl = _EMAIL[loc]
    name = n.actor.username if n.actor is not None else "ChineseVerse"
    url = f"{settings.public_app_url.rstrip('/')}/u/{n.actor_id}" if n.actor_id else settings.public_app_url
    line = tpl["line"].format(name=name)
    text = f"{line}\n\n{tpl['cta']}: {url}\n\n— ChineseVerse\n{tpl['footer']}\n"
    body = (
        '<div style="font-family:Arial,Helvetica,sans-serif;font-size:15px;color:#251d10;max-width:520px">'
        f"<p>{html.escape(tpl['line']).format(name='<b>' + html.escape(name) + '</b>')}</p>"
        f'<p><a href="{html.escape(url)}" style="display:inline-block;padding:10px 16px;background:#c9974a;'
        f'color:#1c1409;border-radius:8px;text-decoration:none;font-weight:bold">{html.escape(tpl["cta"])}</a></p>'
        f'<p style="color:#6b5f42;font-size:12px">— ChineseVerse<br>{html.escape(tpl["footer"])}</p>'
        "</div>"
    )
    return tpl["subject"], text, body


def _claim(db: Session, notification_id: int) -> bool:
    """Atomically mark the row as being sent; False if it was already sent
    or is being sent by someone else -- so a retry or a second worker can
    never mail the same notification twice."""
    claimed = (
        db.query(models.Notification)
        .filter(
            models.Notification.id == notification_id,
            models.Notification.email_status.in_(("pending", "failed")),
            models.Notification.email_attempts < MAX_EMAIL_ATTEMPTS,
        )
        .update({models.Notification.email_status: "sending"}, synchronize_session=False)
    )
    db.commit()
    return claimed == 1


def deliver_email(notification_id: int) -> str:
    """Background task: send the email copy of one committed notification.
    Returns the final email_status. Never raises."""
    try:
        with SessionLocal() as db:
            if not _claim(db, notification_id):
                return "skipped_duplicate"
            n = db.get(models.Notification, notification_id)
            if n is None or n.recipient is None:
                return "gone"
            if not mailer.email_enabled():
                n.email_status = "skipped"  # email disabled on this server
                db.commit()
                return n.email_status
            if not n.recipient.email:
                n.email_status = "no_address"
                db.commit()
                return n.email_status
            subject, text, body = render_email(n)
            delays = (0,) + tuple(RETRY_DELAYS)
            for delay in delays:
                if n.email_attempts >= MAX_EMAIL_ATTEMPTS:
                    break
                if delay:
                    time.sleep(delay)
                n.email_attempts += 1
                try:
                    # Always the recipient's registered address from the DB.
                    mailer.send_email(n.recipient.email, subject, text, body)
                except mailer.EmailSendError as exc:
                    log.warning("notification %s email attempt %s failed (%s)", n.id, n.email_attempts, exc)
                    db.commit()
                    continue
                n.email_status = "sent"
                n.emailed_at = datetime.utcnow()
                db.commit()
                log.info("notification %s emailed", n.id)
                return n.email_status
            n.email_status = "failed"
            db.commit()
            return n.email_status
    except Exception as exc:  # never let a background email crash anything
        log.error("notification %s email delivery crashed (%s)", notification_id, type(exc).__name__)
        return "error"


def retry_undelivered() -> int:
    """Re-attempt recent emails that were never delivered (provider outage,
    or the process stopped before the background task ran). Run once at
    startup, off the request path."""
    if not mailer.email_enabled():
        return 0
    with SessionLocal() as db:
        cutoff = datetime.utcnow() - SWEEP_MAX_AGE
        rows = (
            db.query(models.Notification.id)
            .filter(
                models.Notification.email_status.in_(("pending", "failed", "sending")),
                models.Notification.email_attempts < MAX_EMAIL_ATTEMPTS,
                models.Notification.created_at >= cutoff,
            )
            .all()
        )
        ids = [r.id for r in rows]
        # Anything left "sending" by a stopped process is retryable now.
        if ids:
            db.query(models.Notification).filter(
                models.Notification.id.in_(ids), models.Notification.email_status == "sending"
            ).update({models.Notification.email_status: "failed"}, synchronize_session=False)
            db.commit()
    for nid in ids:
        deliver_email(nid)
    return len(ids)


def start_retry_sweep() -> None:
    if mailer.email_enabled():
        threading.Thread(target=retry_undelivered, name="notification-email-sweep", daemon=True).start()
