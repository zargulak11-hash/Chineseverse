"""add practice_sessions for server-graded practice and review

Revision ID: c4e8a2f6b9d1
Revises: b7e4c2a9d1f3
Create Date: 2026-09-30 12:00:00.000000

Each session stores the questions the server generated (item + option ids,
never trusted back from the client) and the graded answers, so correctness,
score and lesson completion are decided server-side.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'c4e8a2f6b9d1'
down_revision: Union[str, Sequence[str], None] = 'b7e4c2a9d1f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "practice_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("hsk_level", sa.Integer(), nullable=True),
        sa.Column("lesson_id", sa.Integer(), sa.ForeignKey("lessons.id", ondelete="SET NULL"), nullable=True),
        sa.Column("questions", sa.JSON(), nullable=False),
        sa.Column("answers", sa.JSON(), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_practice_sessions_id", "practice_sessions", ["id"])
    op.create_index("ix_practice_sessions_user_id", "practice_sessions", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_practice_sessions_user_id", table_name="practice_sessions")
    op.drop_index("ix_practice_sessions_id", table_name="practice_sessions")
    op.drop_table("practice_sessions")
