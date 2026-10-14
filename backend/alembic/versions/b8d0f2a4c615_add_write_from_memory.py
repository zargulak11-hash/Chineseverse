"""add hanzi_trace_attempts.mode and user_hanzi.times_written_memory

Revision ID: b8d0f2a4c615
Revises: a6c8e0b2d419
Create Date: 2026-10-14 21:00:00.000000

Writing practice was always tracing over the character's grey outline --
copying, never recalling -- and tracing alone could make a character's
writing "mastered". A tracing attempt now has a mode chosen when the server
opens it ("trace", the old behaviour and the default, or "memory": no
outline, only pinyin and meaning shown), and user_hanzi counts the clean
writes from memory, which "mastered" writing now needs. Additive with
defaults; no existing row changes, nobody's mastered character is demoted.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'b8d0f2a4c615'
down_revision: Union[str, Sequence[str], None] = 'a6c8e0b2d419'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("hanzi_trace_attempts") as batch:
        batch.add_column(sa.Column("mode", sa.String(length=10), nullable=False, server_default="trace"))
    with op.batch_alter_table("user_hanzi") as batch:
        batch.add_column(sa.Column("times_written_memory", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    with op.batch_alter_table("user_hanzi") as batch:
        batch.drop_column("times_written_memory")
    with op.batch_alter_table("hanzi_trace_attempts") as batch:
        batch.drop_column("mode")
