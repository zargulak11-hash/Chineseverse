"""add FSRS stability/difficulty to user_vocabulary, user_hanzi, user_grammar

Revision ID: d8b2f4a6c193
Revises: c3e7a1f5d208
Create Date: 2026-10-14 10:00:00.000000

Reviews were scheduled by a fixed doubling (1, 2, 4 ... 30 days), the same
for an easy word and one forgotten five times. services/srs.py now
schedules with FSRS-4.5, which keeps a per-item memory state: stability
(days until recall probability falls to 90%) and difficulty (1-10).
Additive and nullable: no existing row is touched; a record's first review
after this seeds both from the schedule it already had (srs._seed).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'd8b2f4a6c193'
down_revision: Union[str, Sequence[str], None] = 'c3e7a1f5d208'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = ("user_vocabulary", "user_hanzi", "user_grammar")


def upgrade() -> None:
    for table in TABLES:
        with op.batch_alter_table(table) as batch:
            batch.add_column(sa.Column("stability", sa.Float(), nullable=True))
            batch.add_column(sa.Column("difficulty", sa.Float(), nullable=True))


def downgrade() -> None:
    for table in TABLES:
        with op.batch_alter_table(table) as batch:
            batch.drop_column("difficulty")
            batch.drop_column("stability")
