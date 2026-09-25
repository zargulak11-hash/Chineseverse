"""Creates a small set of fictional demo user accounts so the Admin Users
page (/admin/users) isn't empty during development/demos.

Manual, one-off script -- NOT wired into app.seed.seed_all (which runs on
every app startup for every environment, including production). Demo
accounts are dev/test furniture, not something a production deploy or CI
run should ever get automatically.

Run with: python scripts/seed_demo_users.py
Idempotent: matches each demo user by its fixed username AND email; if
either already exists, that user is skipped entirely (never overwritten,
never duplicated). Safe to run any number of times, on top of any amount
of real user data -- it only ever inserts rows for the fixed demo
identities below, never touches anyone else's account, and never sets
is_admin (the column's default is False; nothing here overrides it).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import models
from app.database import SessionLocal
from app.security import hash_password

# Obviously-fictional identities on a project-local demo domain -- never a
# real email provider, never real personal information.
DEMO_USERS = [
    ("demo_alice", "demo.alice@chineseverse.local"),
    ("demo_bob", "demo.bob@chineseverse.local"),
    ("demo_sara", "demo.sara@chineseverse.local"),
    ("demo_amir", "demo.amir@chineseverse.local"),
    ("demo_lina", "demo.lina@chineseverse.local"),
    ("demo_daniel", "demo.daniel@chineseverse.local"),
]

# Not meant to be a real, usable login -- these accounts exist only to
# populate the admin list. Hashed the same way a real registration would be.
DEMO_PASSWORD = "DemoAccount!2026"


def seed_demo_users(db):
    created, skipped = [], []
    for username, email in DEMO_USERS:
        exists = (
            db.query(models.User)
            .filter((models.User.username == username) | (models.User.email == email))
            .first()
        )
        if exists is not None:
            skipped.append(username)
            continue

        user = models.User(
            username=username,
            email=email,
            password_hash=hash_password(DEMO_PASSWORD),
            # is_admin left unset -> column default (False). Never set here.
        )
        db.add(user)
        db.flush()
        db.add(models.UserProfile(user_id=user.id, bio="Demo account for admin testing/demonstration."))
        db.add(models.UserStreak(user_id=user.id))
        created.append(username)

    db.commit()
    return created, skipped


if __name__ == "__main__":
    db = SessionLocal()
    try:
        created, skipped = seed_demo_users(db)
    finally:
        db.close()
    print(f"Created {len(created)} demo user(s): {created}")
    print(f"Skipped {len(skipped)} already-existing demo user(s): {skipped}")
