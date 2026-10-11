"""add users.timezone

Revision ID: b6d4f8a2c915
Revises: a7d3e9f1c246
Create Date: 2026-10-11 12:00:00.000000

The daily streak counted UTC calendar days, so a learner in Dushanbe
(UTC+5) who studied at 01:00 local time was credited for the day before,
and four consecutive local learning days could read as a broken streak.
`users.timezone` remembers the learner's IANA zone (sent by the browser in
the X-Timezone header) so learning days follow their own calendar. Null
means "not seen yet" and keeps the old UTC days. Additive; no existing row
is touched.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'b6d4f8a2c915'
down_revision: Union[str, Sequence[str], None] = 'a7d3e9f1c246'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("timezone", sa.String(length=64), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.drop_column("timezone")
