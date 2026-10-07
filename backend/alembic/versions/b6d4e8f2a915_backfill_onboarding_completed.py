"""mark onboarding complete for accounts already in use

Revision ID: b6d4e8f2a915
Revises: d8e2a5c1f736
Create Date: 2026-10-07 12:00:00.000000

user_profiles.onboarding_completed (d3f1a9b7c412) was added with
server_default 'false' for every existing row, and nothing ever enforced it:
the app was reachable with it false, and only the companion picker looked at
it (picking or changing a companion sent anyone still marked "not complete"
into the onboarding questions again). The app now routes every signed-in
learner whose onboarding is not complete to /onboarding, so without this
backfill everyone who joined before onboarding existed -- or who walked away
from it half-way and simply used the app -- would be stopped and asked the
questions as if they were new.

An account counts as onboarded when it has a finished or skipped placement
test, or real learning on record: XP, an activity event, lesson progress, a
practice session, or a word or character in its own study list. Those rows
are only written by actually using the app (see services/activity.py and
the practice/progress routers), never by registering or picking a companion,
so a genuinely new account stays in onboarding.

Data-only and one-way: it only flips false -> true (and creates the profile
row an old account is missing, which GET /api/me would otherwise create
with the "not complete" default). Nothing is deleted; downgrade leaves the
flags alone because which ones were flipped here can't be told apart from
ones completed through the app.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b6d4e8f2a915'
down_revision: Union[str, Sequence[str], None] = 'd8e2a5c1f736'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# `{uid}` is the column holding the user id in the outer statement.
_IN_USE = """(
    EXISTS (SELECT 1 FROM users u WHERE u.id = {uid} AND u.total_xp > 0)
    OR EXISTS (SELECT 1 FROM placement_attempts pa
               WHERE pa.user_id = {uid} AND pa.status IN ('finished', 'skipped'))
    OR EXISTS (SELECT 1 FROM activity_events ae WHERE ae.user_id = {uid})
    OR EXISTS (SELECT 1 FROM progress pr WHERE pr.user_id = {uid})
    OR EXISTS (SELECT 1 FROM practice_sessions ps WHERE ps.user_id = {uid})
    OR EXISTS (SELECT 1 FROM user_vocabulary uv WHERE uv.user_id = {uid})
    OR EXISTS (SELECT 1 FROM user_hanzi uh WHERE uh.user_id = {uid})
)"""


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "INSERT INTO user_profiles "
            "(user_id, native_language, daily_goal_minutes, avatar_color, onboarding_completed, created_at) "
            "SELECT users.id, 'English', 10, '#6366f1', :done, CURRENT_TIMESTAMP FROM users "
            "WHERE NOT EXISTS (SELECT 1 FROM user_profiles p WHERE p.user_id = users.id) "
            f"AND {_IN_USE.format(uid='users.id')}"
        ),
        {"done": True},
    )
    bind.execute(
        sa.text(
            "UPDATE user_profiles SET onboarding_completed = :done "
            "WHERE onboarding_completed = :not_done "
            f"AND {_IN_USE.format(uid='user_profiles.user_id')}"
        ),
        {"done": True, "not_done": False},
    )


def downgrade() -> None:
    """Downgrade schema: nothing to undo (see the module docstring)."""
