"""add user_achievements.notified_at: show each unlock once

Revision ID: b5e2d8a4c193
Revises: a4c7e2d9f1b3
Create Date: 2026-10-03 12:00:00.000000

Achievements unlocked silently: nothing told the learner when a real
learning step earned one. The app now shows a light "Achievement
unlocked!" note, and this column records that it was shown, on the server,
so the note appears once per unlock across refreshes, devices and
re-logins.

Rows unlocked before this change are backfilled as already notified (with
their unlocked_at): those learners never got a note, but announcing old
unlocks all at once after the deploy would be noise, not feedback. No row
is added or removed.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'b5e2d8a4c193'
down_revision: Union[str, Sequence[str], None] = 'a4c7e2d9f1b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("user_achievements") as batch:
        batch.add_column(sa.Column("notified_at", sa.DateTime(), nullable=True))
    op.execute("UPDATE user_achievements SET notified_at = COALESCE(unlocked_at, CURRENT_TIMESTAMP)")


def downgrade() -> None:
    with op.batch_alter_table("user_achievements") as batch:
        batch.drop_column("notified_at")
