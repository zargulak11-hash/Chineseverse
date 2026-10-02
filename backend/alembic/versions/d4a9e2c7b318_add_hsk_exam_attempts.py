"""add hsk_exam_attempts: server-graded HSK level final exams

Revision ID: d4a9e2c7b318
Revises: c8e4a1f6b2d9
Create Date: 2026-10-02 18:00:00.000000

Finishing every lesson of an HSK level no longer opens the next one by
itself: the learner passes that level's final exam first
(services/hsk_exam.py, services/lesson_path.py). Each attempt is a row the
server owns -- questions, answers, clock, status, score -- and a partial
unique index allows only one in_progress attempt per user, so a second tab
cannot hold a second live attempt.

Nothing existing changes: no lesson progress is touched, and learners who
already completed lessons above a level count as past that level's exam.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'd4a9e2c7b318'
down_revision: Union[str, Sequence[str], None] = 'c8e4a1f6b2d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "hsk_exam_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="in_progress"),
        sa.Column("questions", sa.JSON(), nullable=False),
        sa.Column("answers", sa.JSON(), nullable=False),
        sa.Column("total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("correct", sa.Integer(), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("violations", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_hsk_exam_attempts_id", "hsk_exam_attempts", ["id"])
    op.create_index("ix_hsk_exam_attempts_user_id", "hsk_exam_attempts", ["user_id"])
    op.create_index("ix_hsk_exam_attempts_level", "hsk_exam_attempts", ["level"])
    op.create_index(
        "uq_exam_one_active_per_user", "hsk_exam_attempts", ["user_id"], unique=True,
        postgresql_where=sa.text("status = 'in_progress'"), sqlite_where=sa.text("status = 'in_progress'"),
    )


def downgrade() -> None:
    op.drop_index("uq_exam_one_active_per_user", table_name="hsk_exam_attempts")
    op.drop_index("ix_hsk_exam_attempts_level", table_name="hsk_exam_attempts")
    op.drop_index("ix_hsk_exam_attempts_user_id", table_name="hsk_exam_attempts")
    op.drop_index("ix_hsk_exam_attempts_id", table_name="hsk_exam_attempts")
    op.drop_table("hsk_exam_attempts")
