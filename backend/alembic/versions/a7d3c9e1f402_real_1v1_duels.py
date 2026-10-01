"""real 1-vs-1 duels: challenge/accept lifecycle, per-player clocks, graded answers

Revision ID: a7d3c9e1f402
Revises: c1e6f3a8d5b2
Create Date: 2026-10-01 19:00:00.000000

Duels used to start immediately (no acceptance), ran an unenforced
client-side timer and sent the answers to the browser. This adds what a
real, fair duel between two users needs:

- duels: hsk_level, time_limit_seconds, expires_at, play_deadline,
  responded_at, decided_by
- duel_participants: started_at, finished_at, finish_reason, time_used_ms
  (each player's own clock)
- duel_answers: one row per graded answer, unique per (duel, user, index)
- notifications.duel_id: a challenge/result notification links to its duel

Legacy statuses are mapped: finished -> completed, aborted -> cancelled.
Legacy duels that never finished ("active"/"open") were built by the old
question engine, which the new endpoints no longer serve, so they become
"expired" (their stored scores are kept).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'a7d3c9e1f402'
down_revision: Union[str, Sequence[str], None] = 'c1e6f3a8d5b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("duels") as batch:
        batch.add_column(sa.Column("hsk_level", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("time_limit_seconds", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("expires_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("play_deadline", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("responded_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("decided_by", sa.String(length=20), nullable=True))
        batch.create_index("ix_duels_status", ["status"])

    with op.batch_alter_table("duel_participants") as batch:
        batch.add_column(sa.Column("started_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("finished_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("finish_reason", sa.String(length=20), nullable=True))
        batch.add_column(sa.Column("time_used_ms", sa.Integer(), nullable=True))

    op.create_table(
        "duel_answers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("duel_id", sa.Integer(), sa.ForeignKey("duels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("question_index", sa.Integer(), nullable=False),
        sa.Column("choice_id", sa.Integer(), nullable=False),
        sa.Column("correct", sa.Boolean(), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("response_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("answered_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("duel_id", "user_id", "question_index", name="uq_duel_answer"),
    )
    op.create_index("ix_duel_answers_id", "duel_answers", ["id"])
    op.create_index("ix_duel_answers_duel_id", "duel_answers", ["duel_id"])
    op.create_index("ix_duel_answers_user_id", "duel_answers", ["user_id"])

    with op.batch_alter_table("notifications") as batch:
        batch.add_column(sa.Column("duel_id", sa.Integer(), nullable=True))
        batch.create_index("ix_notifications_duel_id", ["duel_id"])
        batch.create_foreign_key(
            "fk_notifications_duel_id", "duels", ["duel_id"], ["id"], ondelete="CASCADE"
        )

    op.execute("UPDATE duels SET status = 'completed' WHERE status = 'finished'")
    op.execute("UPDATE duels SET status = 'cancelled' WHERE status = 'aborted'")
    op.execute("UPDATE duels SET status = 'expired' WHERE status IN ('active', 'open') OR status IS NULL")


def downgrade() -> None:
    op.execute("UPDATE duels SET status = 'finished' WHERE status = 'completed'")
    op.execute("UPDATE duels SET status = 'aborted' WHERE status IN ('cancelled', 'declined', 'expired', 'pending')")
    with op.batch_alter_table("notifications") as batch:
        batch.drop_constraint("fk_notifications_duel_id", type_="foreignkey")
        batch.drop_index("ix_notifications_duel_id")
        batch.drop_column("duel_id")
    op.drop_index("ix_duel_answers_user_id", table_name="duel_answers")
    op.drop_index("ix_duel_answers_duel_id", table_name="duel_answers")
    op.drop_index("ix_duel_answers_id", table_name="duel_answers")
    op.drop_table("duel_answers")
    with op.batch_alter_table("duel_participants") as batch:
        batch.drop_column("time_used_ms")
        batch.drop_column("finish_reason")
        batch.drop_column("finished_at")
        batch.drop_column("started_at")
    with op.batch_alter_table("duels") as batch:
        batch.drop_index("ix_duels_status")
        batch.drop_column("decided_by")
        batch.drop_column("responded_at")
        batch.drop_column("play_deadline")
        batch.drop_column("expires_at")
        batch.drop_column("time_limit_seconds")
        batch.drop_column("hsk_level")
