"""add times_recalled to user_vocabulary and user_hanzi

Revision ID: c3e7a1f5d208
Revises: b6d4f8a2c915
Create Date: 2026-10-13 12:00:00.000000

Every practice question was multiple choice, so a word became "mastered"
after enough correct picks out of four options -- recognition, never
recall. Rounds now ask a known word or character from memory (typed, see
services/recall.py), and `times_recalled` counts those correct recalls:
"mastered" needs at least one (services/srs.py). Additive with a 0 default;
no existing status or mastery is changed, so nobody loses a mastered word.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'c3e7a1f5d208'
down_revision: Union[str, Sequence[str], None] = 'b6d4f8a2c915'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for table in ("user_vocabulary", "user_hanzi"):
        with op.batch_alter_table(table) as batch:
            batch.add_column(sa.Column("times_recalled", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    for table in ("user_vocabulary", "user_hanzi"):
        with op.batch_alter_table(table) as batch:
            batch.drop_column("times_recalled")
