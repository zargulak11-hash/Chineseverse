"""Removes the fictional demo accounts scripts/seed_demo_users.py used to
create (both files are being deleted together — the Admin Users page must
show only real registered users now, and there is no more demo-seed path
left to reintroduce them).

Targeted, not a broad cleanup: matches ONLY the exact fixed demo usernames
below, and additionally requires the email to end with the demo domain as
a second, independent check -- a row must satisfy BOTH before it is ever
touched. Never matches on "old" or "unused", never touches the owner/admin
account, never touches a real user. Safe to run again: if none of the
demo usernames exist any more, this is a no-op.

Run with: python scripts/remove_demo_users.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import models
from app.crud import delete_user_cascade_safe
from app.database import SessionLocal

DEMO_USERNAMES = {
    "demo_alice",
    "demo_bob",
    "demo_sara",
    "demo_amir",
    "demo_lina",
    "demo_daniel",
}
DEMO_EMAIL_DOMAIN = "@chineseverse.local"


def remove_demo_users(db):
    removed = []
    candidates = db.query(models.User).filter(models.User.username.in_(DEMO_USERNAMES)).all()
    for user in candidates:
        if not user.email.endswith(DEMO_EMAIL_DOMAIN):
            # Doesn't match on both markers -- a real user could in theory
            # collide with a demo username; never touch it if the email
            # doesn't also confirm it's the demo account.
            continue
        removed.append((user.id, user.username, user.email))
        delete_user_cascade_safe(db, user)
    return removed


if __name__ == "__main__":
    db = SessionLocal()
    try:
        removed = remove_demo_users(db)
    finally:
        db.close()
    print(f"Removed {len(removed)} demo user(s):")
    for row in removed:
        print(f"  {row}")
