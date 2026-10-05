"""Follow notifications end to end: follow -> stored notification -> email
copy to the recipient's registered address, plus the delivery bookkeeping
(retries, backoff, give-up, admin retry), diagnostics and health.

The SMTP transport is replaced by an in-memory fake (no real email is ever
sent); the fake can be switched to fail to prove email failure never
undoes a follow or loses the notification.
"""

import io
import logging
import smtplib
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy.orm import Query

from app import models
from app.config import settings
from app.crud import delete_user_cascade_safe
from app.database import SessionLocal
from app.deps import get_locale
from app.services import email as mailer
from app.services import notifications as notif
from helpers import expect, register, unique_name

SECRET = "sup3r-s3cret-smtp-pa55"
EMAIL_SETTINGS = {
    "smtp_host": "smtp.test.invalid",
    "smtp_username": "mailer@test.invalid",
    "smtp_password": SECRET,
    "smtp_from": "ChineseVerse <no-reply@test.invalid>",
}


@pytest.fixture(scope="module")
def outbox(client):
    box = SimpleNamespace(sent=[], fail=False, log=io.StringIO())

    def fake_transport(msg):
        if box.fail:
            # What a real provider outage looks like, including a reply that
            # echoes account details -- which must never reach logs/responses.
            raise smtplib.SMTPAuthenticationError(535, f"auth failed for {settings.smtp_username} / {SECRET}".encode())
        box.sent.append(msg)

    handler = logging.StreamHandler(box.log)
    logging.getLogger("app").addHandler(handler)
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(mailer, "_transport", fake_transport)
        mp.setattr(notif, "RETRY_DELAYS", (0, 0))
        yield box
    logging.getLogger("app").removeHandler(handler)


@pytest.fixture(autouse=True)
def email_on(outbox, monkeypatch):
    """Every test starts with SMTP configured (fake transport), an empty
    outbox and log, and no undelivered email left over from another test
    (the sweep counts every pending row in the database)."""
    outbox.sent.clear()
    outbox.fail = False
    outbox.log.seek(0)
    outbox.log.truncate(0)
    for name, value in EMAIL_SETTINGS.items():
        monkeypatch.setattr(settings, name, value)
    with SessionLocal() as db:
        db.query(models.Notification).filter(models.Notification.email_status != "sent").update(
            {"email_status": "sent"}, synchronize_session=False)
        db.commit()


def enable_email():
    for name, value in EMAIL_SETTINGS.items():
        setattr(settings, name, value)


def person(client, prefix):
    name = unique_name(prefix)
    uid, h = register(client, name)
    return SimpleNamespace(id=uid, h=h, name=name, email=f"{name}@example.com")


def db_notifications(recipient_id):
    with SessionLocal() as db:
        return db.query(models.Notification).filter_by(recipient_id=recipient_id).order_by(models.Notification.id).all()


def body_of(msg):
    return msg.get_body(preferencelist=("plain",)).get_content()


def follow(client, follower, target, expected=201):
    return expect(client, "post", f"/api/users/{target.id}/follow", expected, headers=follower.h)


def age_last_attempt(nid, minutes):
    with SessionLocal() as db:
        row = db.get(models.Notification, nid)
        row.email_last_attempt_at = datetime.utcnow() - timedelta(minutes=minutes)
        db.commit()


def test_a_follow_notifies_the_recipient_by_app_and_by_localized_email(client, outbox):
    a, b = person(client, "zarina"), person(client, "bahrom")
    # B used the app in Russian once, then went offline.
    expect(client, "get", "/api/me", 200, headers={**b.h, "X-Locale": "ru"})
    with SessionLocal() as db:
        assert db.get(models.User, b.id).locale == "ru"

    r = follow(client, a, b)
    assert r["is_following"] is True and r["followers_count"] == 1
    with SessionLocal() as db:
        assert db.query(models.Follow).filter_by(follower_id=a.id, following_id=b.id).count() == 1
    rows = db_notifications(b.id)
    assert len(rows) == 1 and rows[0].actor_id == a.id and rows[0].type == "follow" and rows[0].read_at is None

    # email: to B's REAL registered address, in B's language, with a link to A
    assert len(outbox.sent) == 1, outbox.sent
    msg = outbox.sent[0]
    assert msg["To"] == b.email, msg["To"]
    assert msg["Subject"] == "У вас новый подписчик в ChineseVerse", msg["Subject"]
    assert a.name in body_of(msg) and f"/u/{a.id}" in body_of(msg)
    assert db_notifications(b.id)[0].email_status == "sent"

    # B reads it later (was offline)
    lst = expect(client, "get", "/api/notifications", 200, headers=b.h)
    assert len(lst) == 1
    n = lst[0]
    assert n["type"] == "follow" and n["actor"]["id"] == a.id and n["actor"]["username"] == a.name
    assert n["read"] is False and n["link"] == f"/u/{a.id}" and n["created_at"]
    assert "email" not in str(n).lower(), n  # no delivery bookkeeping / addresses exposed
    assert expect(client, "get", "/api/notifications/unread-count", 200, headers=b.h) == {"unread": 1}

    # the actor's CURRENT name is shown (resolved live, not a copied string)
    new_name = unique_name("renamed")
    expect(client, "patch", "/api/me/account", 200, headers=a.h, json={"username": new_name})
    assert expect(client, "get", "/api/notifications", 200, headers=b.h)[0]["actor"]["username"] == new_name


def test_only_the_recipient_can_list_or_read_a_notification(client):
    a, b, c = person(client, "priv_a"), person(client, "priv_b"), person(client, "priv_c")
    follow(client, a, b)
    n = expect(client, "get", "/api/notifications", 200, headers=b.h)[0]
    assert expect(client, "get", "/api/notifications", 200, headers=a.h) == []
    assert expect(client, "get", "/api/notifications", 200, headers=c.h) == []
    assert expect(client, "get", "/api/notifications/unread-count", 200, headers=a.h) == {"unread": 0}
    expect(client, "patch", f"/api/notifications/{n['id']}/read", 404, headers=a.h)
    expect(client, "patch", f"/api/notifications/{n['id']}/read", 404, headers=c.h)
    expect(client, "get", "/api/notifications", 401)
    expect(client, "get", "/api/notifications/unread-count", 401)
    expect(client, "patch", f"/api/notifications/{n['id']}/read", 401)
    assert db_notifications(b.id)[0].read_at is None
    # no route lets a client create notifications / choose recipients
    expect(client, "post", "/api/notifications", 405, headers=a.h, json={"recipient_id": b.id, "type": "follow"})


def test_marking_read_drops_the_unread_count_and_is_idempotent(client):
    a, b = person(client, "read_a"), person(client, "read_b")
    follow(client, a, b)
    n = expect(client, "get", "/api/notifications", 200, headers=b.h)[0]
    rd = expect(client, "patch", f"/api/notifications/{n['id']}/read", 200, headers=b.h)
    assert rd["read"] is True and rd["read_at"]
    assert expect(client, "get", "/api/notifications/unread-count", 200, headers=b.h) == {"unread": 0}
    again = expect(client, "patch", f"/api/notifications/{n['id']}/read", 200, headers=b.h)
    assert again["read_at"] == rd["read_at"]
    expect(client, "patch", "/api/notifications/999999/read", 404, headers=b.h)


def test_repeated_follow_requests_make_one_follow_one_notification_one_email(client, outbox):
    a, b = person(client, "dup_a"), person(client, "dup_b")
    for _ in range(4):  # double clicks / client retries
        follow(client, a, b)
    with SessionLocal() as db:
        assert db.query(models.Follow).filter_by(follower_id=a.id, following_id=b.id).count() == 1
    assert len(db_notifications(b.id)) == 1 and len(outbox.sent) == 1


def test_a_lost_follow_race_is_201_with_no_notification_or_email(client, outbox, monkeypatch):
    # The pre-check passes but the unique constraint fires -> no 500, no extra notification.
    a, c = person(client, "race_a"), person(client, "race_c")
    with SessionLocal() as db:
        db.add(models.Follow(follower_id=c.id, following_id=a.id))
        db.commit()
    orig_first = Query.first
    state = {"hit": False}

    def first_blind(self):
        # The router's existence pre-check misses once, exactly like a
        # concurrent request whose follow hasn't committed yet.
        ents = [d.get("entity") for d in self.column_descriptions]
        if not state["hit"] and models.Follow in ents:
            state["hit"] = True
            return None
        return orig_first(self)

    monkeypatch.setattr(Query, "first", first_blind)
    follow(client, c, a)
    monkeypatch.setattr(Query, "first", orig_first)
    assert state["hit"]
    assert len(db_notifications(a.id)) == 0, "the losing duplicate request must not leave a notification"
    assert outbox.sent == [], "the losing duplicate request must not send an email"


def test_unfollow_and_refollow_respect_the_24h_anti_spam_window(client, outbox):
    a, b = person(client, "spam_a"), person(client, "spam_b")
    follow(client, a, b)
    expect(client, "delete", f"/api/users/{b.id}/follow", 200, headers=a.h)
    assert len(db_notifications(b.id)) == 1  # unfollow creates no notification
    assert follow(client, a, b)["is_following"] is True
    # re-follow within 24h: follow restored, but no second notification/email
    assert len(db_notifications(b.id)) == 1 and len(outbox.sent) == 1
    with SessionLocal() as db:  # age the first notification past the window
        first = db.query(models.Notification).filter_by(recipient_id=b.id).one()
        first_id = first.id
        first.created_at = datetime.utcnow() - timedelta(hours=25)
        db.commit()
    expect(client, "patch", f"/api/notifications/{first_id}/read", 200, headers=b.h)
    expect(client, "delete", f"/api/users/{b.id}/follow", 200, headers=a.h)
    follow(client, a, b)
    assert len(db_notifications(b.id)) == 2 and len(outbox.sent) == 2
    assert expect(client, "get", "/api/notifications/unread-count", 200, headers=b.h) == {"unread": 1}
    # newest first in the list
    assert [x["read"] for x in expect(client, "get", "/api/notifications", 200, headers=b.h)] == [False, True]
    # self-follow is refused and never notifies
    expect(client, "post", f"/api/users/{a.id}/follow", 400, headers=a.h)


def test_email_failure_never_undoes_the_follow_and_is_retried_once_after_backoff(client, outbox):
    b, c = person(client, "fail_b"), person(client, "fail_c")
    outbox.fail = True
    r = follow(client, c, b)
    assert r["is_following"] is True
    with SessionLocal() as db:
        assert db.query(models.Follow).filter_by(follower_id=c.id, following_id=b.id).count() == 1
        failed = db.query(models.Notification).filter_by(recipient_id=b.id, actor_id=c.id).one()
        # NOT given up: still pending (retryable), with its attempts counted
        assert failed.email_status == "pending" and failed.email_attempts == 3, (failed.email_status, failed.email_attempts)
        assert failed.email_last_attempt_at is not None
        # the real SMTP reason is kept on the row, with credentials masked
        assert failed.email_error.startswith("SMTPAuthenticationError 535"), failed.email_error
        assert SECRET not in failed.email_error and "mailer@test.invalid" not in failed.email_error, failed.email_error
    assert any(x["actor"]["id"] == c.id for x in expect(client, "get", "/api/notifications", 200, headers=b.h))
    logs = outbox.log.getvalue()
    assert "failed" in logs and "SMTPAuthenticationError" in logs, logs
    assert SECRET not in logs and "mailer@test.invalid" not in logs and b.email not in logs, logs
    assert SECRET not in repr(r)

    # the sweep backs off: nothing is retried right after the failure
    outbox.fail = False
    assert notif.retry_undelivered() == 0 and outbox.sent == []
    age_last_attempt(failed.id, 16)
    assert notif.retry_undelivered() == 1
    assert len(outbox.sent) == 1 and outbox.sent[-1]["To"] == b.email
    with SessionLocal() as db:
        fixed = db.get(models.Notification, failed.id)
        assert fixed.email_status == "sent" and fixed.email_error is None
    assert notif.retry_undelivered() == 0  # nothing is ever mailed twice
    assert notif.deliver_email(failed.id) == "skipped_duplicate"


def test_the_sweep_gives_up_after_the_attempt_limit_and_an_admin_retry_sends_once(client, outbox):
    a, e = person(client, "cap_a"), person(client, "cap_e")
    outbox.fail = True
    follow(client, a, e)
    capped = db_notifications(e.id)[0]
    assert capped.email_status == "pending" and capped.email_attempts == 3
    for attempts in range(4, notif.MAX_EMAIL_ATTEMPTS + 1):
        assert notif.retry_undelivered() == 0  # still inside its backoff window
        age_last_attempt(capped.id, 13 * 60)
        assert notif.retry_undelivered() == 1
        with SessionLocal() as db:
            row = db.get(models.Notification, capped.id)
            want = "failed" if attempts == notif.MAX_EMAIL_ATTEMPTS else "pending"
            assert (row.email_status, row.email_attempts) == (want, attempts), (row.email_status, row.email_attempts)
    outbox.fail = False
    age_last_attempt(capped.id, 13 * 60)
    assert notif.retry_undelivered(ignore_backoff=True) == 0 and notif.deliver_email(capped.id) == "skipped_duplicate"
    assert outbox.sent == []
    # an admin's explicit retry after fixing SMTP gives a given-up email one more try -- once
    assert notif.retry_undelivered(ignore_backoff=True, include_exhausted=True) == 1
    assert len(outbox.sent) == 1 and outbox.sent[-1]["To"] == e.email
    assert notif.retry_undelivered(ignore_backoff=True, include_exhausted=True) == 0 and len(outbox.sent) == 1


def test_an_email_in_flight_is_only_reclaimed_by_the_startup_sweep(client, outbox):
    a, f = person(client, "inflight_a"), person(client, "inflight_f")
    settings.smtp_host = None
    follow(client, a, f)
    enable_email()
    with SessionLocal() as db:
        row = db.query(models.Notification).filter_by(recipient_id=f.id).one()
        row.email_status = "sending"
        db.commit()
        stuck_id = row.id
    assert notif.retry_undelivered() == 0 and outbox.sent == []
    assert notif.retry_undelivered(reset_stuck=True) == 1
    assert len(outbox.sent) == 1 and outbox.sent[-1]["To"] == f.email
    with SessionLocal() as db:
        assert db.get(models.Notification, stuck_id).email_status == "sent"


def test_without_smtp_emails_wait_and_are_sent_once_smtp_is_configured(client, outbox):
    a, d, g = person(client, "later_a"), person(client, "later_d"), person(client, "later_g")
    settings.smtp_host = None
    assert follow(client, a, d)["is_following"] is True
    rows = db_notifications(d.id)
    assert len(rows) == 1 and rows[0].email_status == "pending" and rows[0].email_attempts == 0, (rows[0].email_status, rows[0].email_attempts)
    assert expect(client, "get", "/api/notifications/unread-count", 200, headers=d.h) == {"unread": 1}
    assert notif.deliver_email(rows[0].id) == "pending" and notif.retry_undelivered() == 0
    assert outbox.sent == []

    # rows a previous version marked "skipped" for the same reason
    follow(client, a, g)
    with SessionLocal() as db:
        legacy = db.query(models.Notification).filter_by(recipient_id=g.id).one()
        legacy.email_status = "skipped"
        db.commit()

    enable_email()  # SMTP configured + backend restarted -> startup sweep
    assert notif.retry_undelivered(reset_stuck=True) == 2
    assert sorted(m["To"] for m in outbox.sent) == sorted([d.email, g.email])
    # the real follower name and the full profile URL
    assert all(a.name in body_of(m) and f"https://chineseverse.qobus.tj/u/{a.id}" in body_of(m) for m in outbox.sent)
    for uid in (d.id, g.id):
        row = db_notifications(uid)[0]
        assert row.email_status == "sent" and row.email_attempts == 1
    assert notif.retry_undelivered() == 0 and len(outbox.sent) == 2


EXPECTED_EMAIL = {
    "en": ("You have a new follower on ChineseVerse", "followed you on ChineseVerse"),
    "ru": ("У вас новый подписчик в ChineseVerse", "подписан(а) на вас"),
    "tg": ("Дар ChineseVerse шумо пайрави нав доред", "шуморо дар ChineseVerse пайравӣ кард"),
    "zh": ("你在 ChineseVerse 有了新的关注者", "在 ChineseVerse 上关注了你"),
}


@pytest.mark.parametrize("loc", sorted(EXPECTED_EMAIL))
def test_the_email_is_in_the_recipients_own_language(client, outbox, loc):
    c, rcpt = person(client, "loc_actor"), person(client, f"loc_{loc}")
    expect(client, "get", "/api/notifications/unread-count", 200, headers={**rcpt.h, "X-Locale": loc})
    follow(client, c, rcpt)
    subject, phrase = EXPECTED_EMAIL[loc]
    m = outbox.sent[-1]
    assert m["To"] == rcpt.email and m["Subject"] == subject, (loc, m["Subject"])
    assert phrase in body_of(m) and c.name in body_of(m), (loc, body_of(m))


def test_regional_locale_codes_select_the_language(client, outbox):
    # A browser-detected regional code is the same language (it used to be
    # ignored, so these learners got English emails).
    learner = person(client, "regional")
    for raw, want in (("ru-RU", "ru"), ("zh-CN", "zh"), ("tg_TJ", "tg"), ("EN-us", "en")):
        expect(client, "get", "/api/notifications/unread-count", 200, headers={**learner.h, "X-Locale": raw})
        with SessionLocal() as db:
            assert db.get(models.User, learner.id).locale == want, (raw, want)
    # an unknown header keeps the stored language
    expect(client, "get", "/api/notifications/unread-count", 200, headers={**learner.h, "X-Locale": "zh"})
    expect(client, "get", "/api/notifications/unread-count", 200, headers={**learner.h, "X-Locale": "xx"})
    with SessionLocal() as db:
        assert db.get(models.User, learner.id).locale == "zh"

    c, rr = person(client, "regional_actor"), person(client, "regional_ru")
    expect(client, "get", "/api/me", 200, headers={**rr.h, "X-Locale": "ru-RU"})
    follow(client, c, rr)
    assert outbox.sent[-1]["To"] == rr.email and outbox.sent[-1]["Subject"] == "У вас новый подписчик в ChineseVerse"
    assert [get_locale(x) for x in ("zh-CN", "ru_RU", "tg", "fr-FR", "en-US", None, "")] == ["zh", "ru", "tg", "en", "en", "en", "en"]


def test_deleting_a_user_removes_notifications_to_and_from_them(client):
    a, b, c = person(client, "del_a"), person(client, "del_b"), person(client, "del_c")
    follow(client, c, b)
    follow(client, a, c)
    with SessionLocal() as db:
        delete_user_cascade_safe(db, db.get(models.User, c.id))
    assert all(x["actor"] is None or x["actor"]["id"] != c.id
               for x in expect(client, "get", "/api/notifications", 200, headers=b.h))
    with SessionLocal() as db:
        assert db.query(models.Notification).filter(
            (models.Notification.actor_id == c.id) | (models.Notification.recipient_id == c.id)
        ).count() == 0


@pytest.fixture
def admin(client):
    a = person(client, "mailadmin")
    with SessionLocal() as db:
        db.get(models.User, a.id).is_admin = True
        db.commit()
    return a


def test_admin_email_diagnostics_show_presence_only_never_secrets(client, admin):
    b = person(client, "diag_b")
    follow(client, admin, b)
    expect(client, "get", "/api/admin/email", 401)
    expect(client, "get", "/api/admin/email", 403, headers=b.h)
    expect(client, "post", "/api/admin/email/test", 403, headers=b.h)
    expect(client, "post", "/api/admin/email/retry", 403, headers=b.h)
    diag = expect(client, "get", "/api/admin/email", 200, headers=admin.h)
    cfg = diag["config"]
    assert cfg["enabled"] is True and cfg["host"] == "smtp.test.invalid" and cfg["security"] == "starttls"
    assert cfg["username_set"] and cfg["password_set"] and cfg["from_set"]
    assert diag["renotify_after_hours"] == 24 and diag["recent"] and "email_error" in diag["recent"][0]
    dump = str(diag)
    assert SECRET not in dump and "mailer@test.invalid" not in dump and "no-reply@test.invalid" not in dump
    assert "@example.com" not in dump, "no recipient addresses in diagnostics"
    assert diag["variables"]["SMTP_PASSWORD"] == "configured" and diag["variables"]["SMTP_HOST"] == "configured"


def test_public_health_reports_email_readiness_with_names_only(client):
    a, b = person(client, "health_a"), person(client, "health_b")
    follow(client, a, b)  # an email has gone out
    h = expect(client, "get", "/api/health", 200)
    assert {k: h["email"][k] for k in ("enabled", "retry_sweep_running", "missing")} == {
        "enabled": True, "retry_sweep_running": False, "missing": []}, h
    assert h["email"]["last_sent_at"]
    # newest undelivered email's error: type + SMTP code only, never the reply text
    with SessionLocal() as db:
        row = db.query(models.Notification).order_by(models.Notification.id.desc()).first()
        row.email_status, row.email_error = "pending", "SMTPAuthenticationError 535 5.7.8 Username and Password not accepted"
        db.commit()
        newest_id = row.id
    assert expect(client, "get", "/api/health", 200)["email"]["last_error"] == "SMTPAuthenticationError 535"
    with SessionLocal() as db:
        row = db.get(models.Notification, newest_id)
        row.email_status, row.email_error = "sent", None
        db.commit()
    assert expect(client, "get", "/api/health", 200)["email"]["last_error"] is None
    settings.smtp_password, settings.smtp_from = None, None
    assert expect(client, "get", "/api/health", 200)["email"]["missing"] == ["SMTP_PASSWORD", "SMTP_FROM"]
    settings.smtp_host = None
    h = expect(client, "get", "/api/health", 200)
    assert h["email"]["enabled"] is False and "SMTP_HOST" in h["email"]["missing"]
    assert "test.invalid" not in str(h) and SECRET not in str(h)


def test_admin_test_email_goes_to_the_admin_and_reports_a_masked_error(client, outbox, admin):
    assert expect(client, "post", "/api/admin/email/test", 200, headers=admin.h) == {"ok": True, "error": None}
    assert len(outbox.sent) == 1 and outbox.sent[-1]["To"] == admin.email
    outbox.fail = True
    r = expect(client, "post", "/api/admin/email/test", 200, headers=admin.h)
    outbox.fail = False
    assert r["ok"] is False and r["error"].startswith("SMTPAuthenticationError 535") and SECRET not in r["error"], r
    assert "mailer@test.invalid" not in r["error"]
    settings.smtp_host = None
    r = expect(client, "post", "/api/admin/email/test", 200, headers=admin.h)
    assert r["ok"] is False and r["error"].startswith("EmailNotConfigured"), r
    enable_email()
    assert expect(client, "post", "/api/admin/email/retry", 200, headers=admin.h) == {"queued": True}


def test_smtp_settings_are_read_the_way_people_paste_them(monkeypatch):
    monkeypatch.setattr(settings, "smtp_port", 465)
    monkeypatch.setattr(settings, "smtp_security", "starttls")
    assert mailer.effective_security() == "ssl"  # 465 is implicit TLS
    settings.smtp_port = 587
    for raw, want in (("tls", "starttls"), ("STARTTLS", "starttls"), ("ssl", "ssl"), ("none", "none"), ('"starttls"', "starttls")):
        settings.smtp_security = raw
        assert mailer.effective_security() == want, (raw, mailer.effective_security())
    settings.smtp_host, settings.smtp_password = ' "smtp.gmail.com" ', "'abcd efgh ijkl mnop'"
    assert mailer._host() == "smtp.gmail.com" and mailer._password() == "abcdefghijklmnop"


class FakeThread:
    """Stands in for the sweep thread: the test checks the startup decision
    and its log line without leaving a real loop running in the test run."""

    def __init__(self, target, name, daemon):
        self.target, self.name, self.started = target, name, False

    def start(self):
        self.started = True

    def is_alive(self):
        return self.started


def test_startup_logs_email_readiness_and_starts_the_sweep_only_when_enabled(client, outbox, monkeypatch):
    monkeypatch.setattr(notif, "_sweep_thread", None)
    monkeypatch.setattr(notif.threading, "Thread", FakeThread)
    settings.smtp_host = None
    notif.start_retry_sweep()
    assert "notification emails are DISABLED: missing SMTP_HOST" in outbox.log.getvalue(), outbox.log.getvalue()
    assert not notif.sweep_running()
    enable_email()
    notif.start_retry_sweep()
    logs = outbox.log.getvalue()
    assert "notification emails enabled: host=smtp.test.invalid port=587 security=starttls" in logs
    assert "SMTP_PASSWORD=configured" in logs and notif.sweep_running()
    assert notif._sweep_thread.target is notif._sweep_forever
    # names and booleans only: never the password, the login or an address
    assert SECRET not in logs and "mailer@test.invalid" not in logs and "@example.com" not in logs, logs
