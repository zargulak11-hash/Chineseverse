"""add notifications.email_last_attempt_at

Revision ID: c1e6f3a8d5b2
Revises: b9d4e1f7a2c3
Create Date: 2026-10-01 18:00:00.000000

The retry sweep tried a failed notification email every 15 minutes, so a
provider outage or a wrong SMTP setting used up the whole attempt budget in
under an hour and the email was dropped even if SMTP was fixed later that
day. Remembering when the last attempt ran lets the sweep back off instead
(15 min ... 12 h). Additive; nullable.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'c1e6f3a8d5b2'
down_revision: Union[str, Sequence[str], None] = 'b9d4e1f7a2c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("notifications") as batch:
        batch.add_column(sa.Column("email_last_attempt_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("notifications") as batch:
        batch.drop_column("email_last_attempt_at")
