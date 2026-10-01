"""Follow notifications end to end: follow -> stored notification -> email
copy to the recipient's registered address, on a fresh database.

The SMTP transport is replaced by an in-memory fake (no real email is ever
sent); the fake can be switched to fail to prove email failure never
undoes a follow or loses the notification.
"""

import io
import logging
import os
import sys
import tempfile
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/notifications.db"
os.environ["SMTP_HOST"] = ""  # start with email disabled; enabled below with a fake transport

from fastapi.testclient import TestClient  # noqa: E402

from app import models  # noqa: E402
from app.config import settings  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.services import email as mailer  # noqa: E402
from app.services import notifications as notif  # noqa: E402

SECRET = "sup3r-s3cret-smtp-pa55"
sent: list = []
fail_mode = {"on": False}


def fake_transport(msg):
    if fail_mode["on"]:
        # What a real provider outage looks like, including a reply that
        # echoes account details -- which must never reach logs/responses.
        import smtplib
        raise smtplib.SMTPAuthenticationError(535, f"auth failed for {settings.smtp_username} / {SECRET}".encode())
    sent.append(msg)


mailer._transport = fake_transport
notif.RETRY_DELAYS = (0, 0)

log_buf = io.StringIO()
_h = logging.StreamHandler(log_buf)
logging.getLogger("app").addHandler(_h)


def enable_email():
    settings.smtp_host = "smtp.test.invalid"
    settings.smtp_username = "mailer@test.invalid"
    settings.smtp_password = SECRET
    settings.smtp_from = "ChineseVerse <no-reply@test.invalid>"


def expect(client, method, url, expected, **kwargs):
    resp = getattr(client, method)(url, **kwargs)
    assert resp.status_code == expected, f"{method.upper()} {url} -> {resp.status_code} (expected {expected}): {resp.text}"
    return resp.json() if resp.content else None


def register(client, name):
    data = expect(client, "post", "/api/auth/register", 201,
                  json={"username": name, "email": f"{name}@example.com", "password": "secret1"})
    return data["user"]["id"], {"Authorization": f"Bearer {data['access_token']}"}


def db_notifications(recipient_id):
    with SessionLocal() as db:
        return db.query(models.Notification).filter_by(recipient_id=recipient_id).order_by(models.Notification.id).all()


def body_of(msg):
    part = msg.get_body(preferencelist=("plain",))
    return part.get_content()


with TestClient(app) as client:
    a_id, a = register(client, "zarina_a")
    b_id, b = register(client, "bahrom_b")
    c_id, c = register(client, "carol_c")

    # B used the app in Russian once, then went offline (no requests at all
    # from B until much later below).
    expect(client, "get", "/api/me", 200, headers={**b, "X-Locale": "ru"})
    with SessionLocal() as db:
        assert db.get(models.User, b_id).locale == "ru"
    print("[PASS] the recipient's UI language is remembered from X-Locale")

    # ------------------------------------------------ follow -> notification (+ email)
    enable_email()
    r = expect(client, "post", f"/api/users/{b_id}/follow", 201, headers=a)
    assert r["is_following"] is True and r["followers_count"] == 1
    with SessionLocal() as db:
        assert db.query(models.Follow).filter_by(follower_id=a_id, following_id=b_id).count() == 1
    rows = db_notifications(b_id)
    assert len(rows) == 1 and rows[0].actor_id == a_id and rows[0].type == "follow" and rows[0].read_at is None
    print("[PASS] A follows B: follow row + one notification for B with A as the actor")

    # email: to B's REAL registered address, in B's language, with a link to A
    assert len(sent) == 1, sent
    msg = sent[0]
    assert msg["To"] == "bahrom_b@example.com", msg["To"]
    assert msg["Subject"] == "У вас новый подписчик в ChineseVerse", msg["Subject"]
    assert "zarina_a" in body_of(msg) and f"/u/{a_id}" in body_of(msg)
    assert db_notifications(b_id)[0].email_status == "sent"
    print("[PASS] email went to B's registered address, localized (ru), linking to A's profile")

    # ------------------------------------------------ B reads it later (was offline)
    lst = expect(client, "get", "/api/notifications", 200, headers=b)
    assert len(lst) == 1
    n = lst[0]
    assert n["type"] == "follow" and n["actor"]["id"] == a_id and n["actor"]["username"] == "zarina_a"
    assert n["read"] is False and n["link"] == f"/u/{a_id}" and n["created_at"]
    assert "email" not in str(n).lower(), n  # no delivery bookkeeping / addresses exposed
    assert expect(client, "get", "/api/notifications/unread-count", 200, headers=b) == {"unread": 1}
    print("[PASS] offline recipient finds the persisted notification + unread count when back")

    # the actor's CURRENT name is shown (resolved live, not a copied string)
    expect(client, "patch", "/api/me/account", 200, headers=a, json={"username": "zarina_new"})
    assert expect(client, "get", "/api/notifications", 200, headers=b)[0]["actor"]["username"] == "zarina_new"
    print("[PASS] actor name is resolved live from the user row")

    # ------------------------------------------------ privacy / authorization
    assert expect(client, "get", "/api/notifications", 200, headers=a) == []
    assert expect(client, "get", "/api/notifications", 200, headers=c) == []
    assert expect(client, "get", "/api/notifications/unread-count", 200, headers=a) == {"unread": 0}
    expect(client, "patch", f"/api/notifications/{n['id']}/read", 404, headers=a)
    expect(client, "patch", f"/api/notifications/{n['id']}/read", 404, headers=c)
    expect(client, "get", "/api/notifications", 401)
    expect(client, "get", "/api/notifications/unread-count", 401)
    expect(client, "patch", f"/api/notifications/{n['id']}/read", 401)
    assert db_notifications(b_id)[0].read_at is None
    # no route lets a client create notifications / choose recipients
    expect(client, "post", "/api/notifications", 405, headers=a, json={"recipient_id": b_id, "type": "follow"})
    print("[PASS] only B can list/read B's notification (A and C get nothing / 404; anon 401; no create route)")

    # ------------------------------------------------ mark read
    rd = expect(client, "patch", f"/api/notifications/{n['id']}/read", 200, headers=b)
    assert rd["read"] is True and rd["read_at"]
    assert expect(client, "get", "/api/notifications/unread-count", 200, headers=b) == {"unread": 0}
    again = expect(client, "patch", f"/api/notifications/{n['id']}/read", 200, headers=b)
    assert again["read_at"] == rd["read_at"]  # idempotent
    expect(client, "patch", "/api/notifications/999999/read", 404, headers=b)
    print("[PASS] B marks it read; unread count drops to 0; idempotent")

    # ------------------------------------------------ duplicates
    for _ in range(3):  # double clicks / client retries
        expect(client, "post", f"/api/users/{b_id}/follow", 201, headers=a)
    with SessionLocal() as db:
        assert db.query(models.Follow).filter_by(follower_id=a_id, following_id=b_id).count() == 1
    assert len(db_notifications(b_id)) == 1 and len(sent) == 1
    print("[PASS] repeated follow requests: still one follow, one notification, one email")

    # race: the pre-check passes but the unique constraint fires -> no 500, no extra notification
    with SessionLocal() as db:
        db.add(models.Follow(follower_id=c_id, following_id=a_id))
        db.commit()
    from sqlalchemy.orm import Query as _Q
    orig_first = _Q.first
    state = {"hit": False}

    def first_blind(self):
        # The router's existence pre-check misses once, exactly like a
        # concurrent request whose follow hasn't committed yet.
        ents = [d.get("entity") for d in self.column_descriptions]
        if not state["hit"] and models.Follow in ents:
            state["hit"] = True
            return None
        return orig_first(self)

    _Q.first = first_blind
    sent_before_race = len(sent)
    try:
        expect(client, "post", f"/api/users/{a_id}/follow", 201, headers=c)
    finally:
        _Q.first = orig_first
    assert state["hit"]
    assert len(db_notifications(a_id)) == 0, "the losing duplicate request must not leave a notification"
    assert len(sent) == sent_before_race, "the losing duplicate request must not send an email"
    print("[PASS] concurrent duplicate follow hits uq_follow_pair: 201, no 500, no notification, no email")

    # ------------------------------------------------ unfollow / follow again
    expect(client, "delete", f"/api/users/{b_id}/follow", 200, headers=a)
    assert len(db_notifications(b_id)) == 1
    print("[PASS] unfollow creates no notification")
    r = expect(client, "post", f"/api/users/{b_id}/follow", 201, headers=a)
    assert r["is_following"] is True
    assert len(db_notifications(b_id)) == 1 and len(sent) == 1
    print("[PASS] re-follow within 24h: follow restored, but no second notification/email (anti-spam)")
    with SessionLocal() as db:  # age the first notification past the window
        first = db.query(models.Notification).filter_by(recipient_id=b_id).one()
        first.created_at = datetime.utcnow() - timedelta(hours=25)
        db.commit()
    expect(client, "delete", f"/api/users/{b_id}/follow", 200, headers=a)
    expect(client, "post", f"/api/users/{b_id}/follow", 201, headers=a)
    assert len(db_notifications(b_id)) == 2 and len(sent) == 2
    assert expect(client, "get", "/api/notifications/unread-count", 200, headers=b) == {"unread": 1}
    print("[PASS] re-follow after the window notifies again (newest first in the list)")
    lst = expect(client, "get", "/api/notifications", 200, headers=b)
    assert [x["read"] for x in lst] == [False, True]

    # self-follow is refused and never notifies
    expect(client, "post", f"/api/users/{a_id}/follow", 400, headers=a)

    # ------------------------------------------------ email failure never undoes the follow
    fail_mode["on"] = True
    log_buf.seek(0)
    log_buf.truncate(0)
    r = expect(client, "post", f"/api/users/{b_id}/follow", 201, headers=c)
    assert r["is_following"] is True
    with SessionLocal() as db:
        assert db.query(models.Follow).filter_by(follower_id=c_id, following_id=b_id).count() == 1
        failed = db.query(models.Notification).filter_by(recipient_id=b_id, actor_id=c_id).one()
        assert failed.email_status == "failed" and failed.email_attempts == 3, (failed.email_status, failed.email_attempts)
        # the real SMTP reason is kept on the row, with credentials masked
        assert failed.email_error.startswith("SMTPAuthenticationError 535"), failed.email_error
        assert SECRET not in failed.email_error and "mailer@test.invalid" not in failed.email_error, failed.email_error
    assert any(x["actor"]["id"] == c_id for x in expect(client, "get", "/api/notifications", 200, headers=b))
    logs = log_buf.getvalue()
    assert "failed" in logs and "SMTPAuthenticationError" in logs, logs
    assert SECRET not in logs and "mailer@test.invalid" not in logs and "bahrom_b@example.com" not in logs, logs
    assert SECRET not in r.__repr__()
    print("[PASS] provider failure: follow + notification kept, 3 attempts, status failed, no secrets/addresses in logs")

    # the startup sweep retries it once the provider is back
    fail_mode["on"] = False
    before = len(sent)
    assert notif.retry_undelivered() == 1
    assert len(sent) == before + 1 and sent[-1]["To"] == "bahrom_b@example.com"
    with SessionLocal() as db:
        fixed = db.query(models.Notification).filter_by(recipient_id=b_id, actor_id=c_id).one()
        assert fixed.email_status == "sent" and fixed.email_error is None
    assert notif.retry_undelivered() == 0  # nothing is ever mailed twice
    assert notif.deliver_email(failed.id) == "skipped_duplicate"
    print("[PASS] undelivered email is retried later exactly once")

    # ------------------------------------------------ the periodic sweep: one attempt per run, capped
    fail_mode["on"] = True
    e_id, e = register(client, "emil_e")
    expect(client, "post", f"/api/users/{e_id}/follow", 201, headers=a)
    capped = db_notifications(e_id)[0]
    assert capped.email_status == "failed" and capped.email_attempts == 3
    for attempts in (4, 5, 6):
        assert notif.retry_undelivered() == 1
        with SessionLocal() as db:
            row = db.get(models.Notification, capped.id)
            assert (row.email_status, row.email_attempts) == ("failed", attempts), (row.email_status, row.email_attempts)
    fail_mode["on"] = False
    before = len(sent)
    assert notif.retry_undelivered() == 0 and notif.deliver_email(capped.id) == "skipped_duplicate"
    assert len(sent) == before
    print("[PASS] SMTP outage: each sweep makes one more attempt, stopping at the attempt limit")

    # a delivery in flight ("sending") is never touched by the running sweep;
    # only the startup sweep reclaims rows a stopped process left behind
    f_id, f = register(client, "fara_f")
    settings.smtp_host = None
    expect(client, "post", f"/api/users/{f_id}/follow", 201, headers=a)
    enable_email()
    with SessionLocal() as db:
        row = db.query(models.Notification).filter_by(recipient_id=f_id).one()
        row.email_status = "sending"
        db.commit()
        stuck_id = row.id
    before = len(sent)
    assert notif.retry_undelivered() == 0 and len(sent) == before
    assert notif.retry_undelivered(reset_stuck=True) == 1
    assert len(sent) == before + 1 and sent[-1]["To"] == "fara_f@example.com"
    with SessionLocal() as db:
        assert db.get(models.Notification, stuck_id).email_status == "sent"
    print("[PASS] in-flight email is never re-sent by the sweep; startup reclaims rows from a stopped process")

    # ------------------------------------------------ email not configured: stored, shown, and sent LATER
    settings.smtp_host = None
    d_id, d = register(client, "dina_d")
    before = len(sent)
    r = expect(client, "post", f"/api/users/{d_id}/follow", 201, headers=a)
    assert r["is_following"] is True
    rows = db_notifications(d_id)
    assert len(rows) == 1 and rows[0].email_status == "pending" and rows[0].email_attempts == 0, (rows[0].email_status, rows[0].email_attempts)
    assert expect(client, "get", "/api/notifications/unread-count", 200, headers=d) == {"unread": 1}
    assert notif.deliver_email(rows[0].id) == "pending" and notif.retry_undelivered() == 0
    assert len(sent) == before
    print("[PASS] with SMTP unconfigured the follow + notification are stored and shown; email stays pending (no attempt used)")

    # rows a previous version marked "skipped" for the same reason
    g_id, g = register(client, "gulya_g")
    expect(client, "post", f"/api/users/{g_id}/follow", 201, headers=a)
    with SessionLocal() as db:
        legacy = db.query(models.Notification).filter_by(recipient_id=g_id).one()
        legacy.email_status = "skipped"
        db.commit()

    enable_email()  # SMTP configured + backend restarted -> startup sweep
    assert notif.retry_undelivered(reset_stuck=True) == 2
    assert sorted(m["To"] for m in sent[before:]) == ["dina_d@example.com", "gulya_g@example.com"]
    # the real follower name (current username) and the full profile URL
    assert all("zarina_new" in body_of(m) and f"https://chineseverse.qobus.tj/u/{a_id}" in body_of(m) for m in sent[before:])
    for uid in (d_id, g_id):
        row = db_notifications(uid)[0]
        assert row.email_status == "sent" and row.email_attempts == 1
    assert notif.retry_undelivered() == 0 and len(sent) == before + 2
    print("[PASS] once SMTP is configured, pending (and legacy skipped) follow emails are delivered exactly once")

    # ------------------------------------------------ localized email for every UI language
    enable_email()
    expected = {
        "en": ("You have a new follower on ChineseVerse", "followed you on ChineseVerse"),
        "ru": ("У вас новый подписчик в ChineseVerse", "подписан(а) на вас"),
        "tg": ("Дар ChineseVerse шумо пайрави нав доред", "шуморо дар ChineseVerse пайравӣ кард"),
        "zh": ("你在 ChineseVerse 有了新的关注者", "在 ChineseVerse 上关注了你"),
    }
    for loc, (subject, phrase) in expected.items():
        uid, hdr = register(client, f"loc_{loc}")
        expect(client, "get", "/api/notifications/unread-count", 200, headers={**hdr, "X-Locale": loc})
        expect(client, "post", f"/api/users/{uid}/follow", 201, headers=c)
        m = sent[-1]
        assert m["To"] == f"loc_{loc}@example.com" and m["Subject"] == subject, (loc, m["Subject"])
        assert phrase in body_of(m) and "carol_c" in body_of(m), (loc, body_of(m))
    # unknown header keeps the stored language
    expect(client, "get", "/api/notifications/unread-count", 200, headers={**hdr, "X-Locale": "xx"})
    with SessionLocal() as db:
        assert db.query(models.User).filter_by(username="loc_zh").one().locale == "zh"
    print("[PASS] email subject/body localized for en/ru/tg/zh from the recipient's own language")

    # ------------------------------------------------ deleting a user cleans up
    from app.crud import delete_user_cascade_safe
    with SessionLocal() as db:
        delete_user_cascade_safe(db, db.get(models.User, c_id))
    assert all(x["actor"] is None or x["actor"]["id"] != c_id for x in expect(client, "get", "/api/notifications", 200, headers=b))
    with SessionLocal() as db:
        assert db.query(models.Notification).filter(
            (models.Notification.actor_id == c_id) | (models.Notification.recipient_id == c_id)
        ).count() == 0
    print("[PASS] deleting a user removes notifications to/from them (no broken FKs)")

    # ------------------------------------------------ admin email diagnostics
    with SessionLocal() as db:
        db.get(models.User, a_id).is_admin = True
        db.commit()
    expect(client, "get", "/api/admin/email", 401)
    expect(client, "get", "/api/admin/email", 403, headers=b)
    expect(client, "post", "/api/admin/email/test", 403, headers=b)
    expect(client, "post", "/api/admin/email/retry", 403, headers=b)
    diag = expect(client, "get", "/api/admin/email", 200, headers=a)
    cfg = diag["config"]
    assert cfg["enabled"] is True and cfg["host"] == "smtp.test.invalid" and cfg["security"] == "starttls"
    assert cfg["username_set"] and cfg["password_set"] and cfg["from_set"]
    assert diag["renotify_after_hours"] == 24 and diag["recent"] and "email_error" in diag["recent"][0]
    dump = str(diag)
    assert SECRET not in dump and "mailer@test.invalid" not in dump and "no-reply@test.invalid" not in dump
    assert "@example.com" not in dump, "no recipient addresses in diagnostics"
    print("[PASS] admin email diagnostics: admin-only, config presence only, no secrets or addresses")

    before = len(sent)
    assert expect(client, "post", "/api/admin/email/test", 200, headers=a) == {"ok": True, "error": None}
    assert len(sent) == before + 1 and sent[-1]["To"] == "zarina_a@example.com"
    fail_mode["on"] = True
    r = expect(client, "post", "/api/admin/email/test", 200, headers=a)
    fail_mode["on"] = False
    assert r["ok"] is False and r["error"].startswith("SMTPAuthenticationError 535") and SECRET not in r["error"], r
    assert "mailer@test.invalid" not in r["error"]
    settings.smtp_host = None
    r = expect(client, "post", "/api/admin/email/test", 200, headers=a)
    assert r["ok"] is False and r["error"].startswith("EmailNotConfigured"), r
    enable_email()
    assert expect(client, "post", "/api/admin/email/retry", 200, headers=a) == {"queued": True}
    print("[PASS] admin test email goes to the admin's own address and reports the masked SMTP error")

    # ------------------------------------------------ SMTP settings as people actually paste them
    saved = (settings.smtp_port, settings.smtp_security, settings.smtp_host, settings.smtp_password)
    settings.smtp_port, settings.smtp_security = 465, "starttls"
    assert mailer.effective_security() == "ssl"  # 465 is implicit TLS
    settings.smtp_port = 587
    for raw, want in (("tls", "starttls"), ("STARTTLS", "starttls"), ("ssl", "ssl"), ("none", "none"), ('"starttls"', "starttls")):
        settings.smtp_security = raw
        assert mailer.effective_security() == want, (raw, mailer.effective_security())
    settings.smtp_host, settings.smtp_password = ' "smtp.gmail.com" ', "'abcd efgh ijkl mnop'"
    assert mailer._host() == "smtp.gmail.com" and mailer._password() == "abcdefghijklmnop"
    settings.smtp_port, settings.smtp_security, settings.smtp_host, settings.smtp_password = saved
    print("[PASS] SMTP settings: quotes/spaces stripped, Gmail app-password spaces removed, 465 => ssl")

    # nothing logged since the provider-failure section ever carries the SMTP
    # password, the SMTP login or a recipient address
    logs = log_buf.getvalue()
    assert SECRET not in logs and "mailer@test.invalid" not in logs and "@example.com" not in logs, logs
    print("[PASS] no SMTP secrets or email addresses in the logs")

print("ALL NOTIFICATION TESTS PASSED")
