"""add hanzi_trace_attempts: server-issued, single-use Hanzi tracing attempts

Revision ID: e7c1a3f9d052
Revises: d4a9e2c7b318
Create Date: 2026-10-02 20:00:00.000000

POST /api/hanzi/{id}/write used to accept {"total_mistakes": 0} and add
writing mastery for it -- the server never saw what was drawn, so any
request (repeated at will) mastered any character's handwriting. A trace is
now an attempt the server issues when the quiz starts; the report that ends
it carries the drawn stroke points, which the server re-matches against the
character's stroke data before anything counts, and it spends the attempt.

New table only: no existing writing progress is touched.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'e7c1a3f9d052'
down_revision: Union[str, Sequence[str], None] = 'd4a9e2c7b318'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "hanzi_trace_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("hanzi_id", sa.Integer(), sa.ForeignKey("hanzi.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="open"),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("total_mistakes", sa.Integer(), nullable=True),
    )
    op.create_index("ix_hanzi_trace_attempts_id", "hanzi_trace_attempts", ["id"])
    op.create_index("ix_hanzi_trace_attempts_user_id", "hanzi_trace_attempts", ["user_id"])
    op.create_index("ix_hanzi_trace_attempts_hanzi_id", "hanzi_trace_attempts", ["hanzi_id"])


def downgrade() -> None:
    op.drop_index("ix_hanzi_trace_attempts_hanzi_id", table_name="hanzi_trace_attempts")
    op.drop_index("ix_hanzi_trace_attempts_user_id", table_name="hanzi_trace_attempts")
    op.drop_index("ix_hanzi_trace_attempts_id", table_name="hanzi_trace_attempts")
    op.drop_table("hanzi_trace_attempts")
