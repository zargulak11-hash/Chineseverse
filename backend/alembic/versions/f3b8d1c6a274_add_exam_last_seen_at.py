"""add hsk_exam_attempts.last_seen_at: server-side presence for exams

Revision ID: f3b8d1c6a274
Revises: e7c1a3f9d052
Create Date: 2026-10-02 22:00:00.000000

Leaving an exam (closing, reloading, navigating away, switching away) was
detected only by the exam page's own report, so a learner who blocked that
report could leave the exam context and keep answering through the API.
The page now sends a heartbeat while it is visible and focused; this column
holds the last one, and any contact after too long a silence ends the
attempt with score 0 (services/hsk_exam.py).

Nullable column only: attempts already in the table are unaffected (a
finished attempt never reads it; an old in-progress one falls back to
started_at).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'f3b8d1c6a274'
down_revision: Union[str, Sequence[str], None] = 'e7c1a3f9d052'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("hsk_exam_attempts") as batch:
        batch.add_column(sa.Column("last_seen_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("hsk_exam_attempts") as batch:
        batch.drop_column("last_seen_at")
