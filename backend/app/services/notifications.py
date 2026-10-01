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
best-effort with retries (a few in-process attempts, then a periodic
sweep), and can never undo the follow or the notification.

email_status: pending -> sending -> sent | failed | no_address.
"pending" also covers "SMTP not configured on this server yet": such rows
are left untouched (no attempt counted) and go out once SMTP is set up
and the backend restarts. "skipped" is a legacy value from before that
change -- it meant the same thing, so it is treated as pending.
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
# Statuses a delivery may (re)claim. "skipped" rows were written while SMTP
# was not configured and used to be dropped forever; they never had an
# attempt, so they are just as deliverable as "pending".
RETRYABLE = ("pending", "failed", "skipped")
# How far back the sweep reaches. Generous enough that follows made while
# SMTP was not configured yet still get their email once it is.
SWEEP_MAX_AGE = timedelta(days=14)
# The sweep re-runs while the app is up, so a provider outage is retried
# without waiting for the next deploy. One attempt per row per run.
SWEEP_INTERVAL_SECONDS = 15 * 60


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
            models.Notification.email_status.in_(RETRYABLE),
            models.Notification.email_attempts < MAX_EMAIL_ATTEMPTS,
        )
        .update({models.Notification.email_status: "sending"}, synchronize_session=False)
    )
    db.commit()
    return claimed == 1


def deliver_email(notification_id: int, retry_delays: tuple[int, ...] | None = None) -> str:
    """Background task: send the email copy of one committed notification.
    Returns the final email_status. Never raises.

    retry_delays: waits before the in-process retries after the first
    attempt (default RETRY_DELAYS); the sweep passes () so each run costs
    one attempt per row."""
    if not mailer.email_enabled():
        # SMTP not configured (yet). Leave the row "pending" with no attempt
        # counted -- it used to be marked "skipped" here and was then never
        # sent, even after SMTP was configured.
        return "pending"
    try:
        with SessionLocal() as db:
            if not _claim(db, notification_id):
                return "skipped_duplicate"
            n = db.get(models.Notification, notification_id)
            if n is None or n.recipient is None:
                return "gone"
            if not n.recipient.email:
                n.email_status = "no_address"
                db.commit()
                return n.email_status
            subject, text, body = render_email(n)
            delays = (0,) + tuple(RETRY_DELAYS if retry_delays is None else retry_delays)
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


def _release_stuck() -> None:
    """A row left "sending" by a process that stopped mid-delivery would
    never be claimed again. Called once at startup, BEFORE requests are
    served: while the app runs, "sending" means a delivery is in flight and
    must not be touched (that is what prevents double sends)."""
    with SessionLocal() as db:
        db.query(models.Notification).filter(models.Notification.email_status == "sending").update(
            {models.Notification.email_status: "failed"}, synchronize_session=False
        )
        db.commit()


def retry_undelivered(reset_stuck: bool = False) -> int:
    """Re-attempt recent emails that were never delivered: a provider outage,
    SMTP not configured when the follow happened, or the process stopping
    before the background task ran. One attempt per row per call.
    reset_stuck=True is the startup variant (see _release_stuck)."""
    if not mailer.email_enabled():
        return 0
    if reset_stuck:
        _release_stuck()
    with SessionLocal() as db:
        cutoff = datetime.utcnow() - SWEEP_MAX_AGE
        rows = (
            db.query(models.Notification.id)
            .filter(
                models.Notification.email_status.in_(RETRYABLE),
                models.Notification.email_attempts < MAX_EMAIL_ATTEMPTS,
                models.Notification.created_at >= cutoff,
            )
            .order_by(models.Notification.id)
            .all()
        )
        ids = [r.id for r in rows]
    for nid in ids:
        deliver_email(nid, retry_delays=())
    return len(ids)


def _sweep_forever() -> None:
    while True:
        try:
            retry_undelivered()
        except Exception as exc:  # e.g. DB briefly unreachable: try next round
            log.error("notification email sweep failed (%s)", type(exc).__name__)
        time.sleep(SWEEP_INTERVAL_SECONDS)


def start_retry_sweep() -> None:
    """Startup (from the lifespan, before serving): release rows a stopped
    process left mid-delivery, then -- in the background -- deliver what
    earlier runs could not (including follows made before SMTP was
    configured) and keep retrying failures periodically. SMTP settings are
    read at startup, so without them there is nothing to do until the
    backend is restarted with them."""
    if not mailer.email_enabled():
        return
    try:
        _release_stuck()
    except Exception as exc:  # never block startup over email bookkeeping
        log.error("could not release stuck notification emails (%s)", type(exc).__name__)
    threading.Thread(target=_sweep_forever, name="notification-email-sweep", daemon=True).start()
