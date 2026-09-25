"""Removes leftover QA/test accounts accumulated across this project's
development (registered by automated test scripts exercising HSK, duels,
onboarding, voice, etc. -- NOT the earlier demo_*/@chineseverse.local
seed, which scripts/remove_demo_users.py already handles and confirmed
at zero remaining).

Criterion is deliberately an ALLOWLIST-style domain match, not a
"delete everyone except admin" rule: every test script in this project's
history has registered its throwaway accounts on @example.com or @x.com
(confirmed: every single non-owner, non-bot row in the current database
falls into exactly these two domains). A future real user registering
with a real personal email address is never matched by this criterion,
even years from now -- unlike a blanket "not the owner" filter, which
this script deliberately does NOT use.

Two accounts are always protected regardless of their email:
  - the project owner/admin (matched by is_admin=True, never by name,
    so this stays correct even if the owner's account changes)
  - __buddy_ai__ (buddy.ai@linguaverse.internal): NOT a test artifact --
    it's a real, functional system account app/routers/duels.py
    auto-creates and relies on as the AI opponent bot for solo Duels.
    Deleting it would either break existing Duel rows referencing it or
    just get silently recreated on the next duel, so there is nothing
    to gain and real risk (FK handling on any existing Duel.winner_id /
    DuelParticipant rows) in touching it.

Prints the full match list before deleting anything (nothing is deleted
without you being able to see exactly what matched first -- run with
--dry-run to only print and change nothing).

Run with: python scripts/remove_qa_test_accounts.py [--dry-run]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import models
from app.crud import delete_user_cascade_safe
from app.database import SessionLocal

TEST_EMAIL_DOMAINS = ("@example.com", "@x.com")
PROTECTED_USERNAMES = {"__buddy_ai__"}


def find_qa_test_accounts(db):
    candidates = (
        db.query(models.User)
        .filter(models.User.is_admin.is_(False))
        .filter(models.User.username.notin_(PROTECTED_USERNAMES))
        .all()
    )
    return [u for u in candidates if u.email.endswith(TEST_EMAIL_DOMAINS)]


def remove_qa_test_accounts(db, dry_run=False):
    matches = find_qa_test_accounts(db)
    print(f"Matched {len(matches)} QA/test account(s):")
    for u in matches:
        print(f"  id={u.id} username={u.username!r} email={u.email!r} created_at={u.created_at}")

    if dry_run:
        print("--dry-run: nothing deleted.")
        return matches

    removed = []
    for u in matches:
        removed.append((u.id, u.username, u.email))
        delete_user_cascade_safe(db, u)
    return removed


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    db = SessionLocal()
    try:
        result = remove_qa_test_accounts(db, dry_run=dry_run)
    finally:
        db.close()
    if not dry_run:
        print(f"\nDeleted {len(result)} QA/test account(s).")
