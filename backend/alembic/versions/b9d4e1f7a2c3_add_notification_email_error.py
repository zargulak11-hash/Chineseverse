"""add notifications.email_error

Revision ID: b9d4e1f7a2c3
Revises: e5a1c7d3f820
Create Date: 2026-10-01 16:00:00.000000

A follow email that failed left its reason only in the container logs, so
"the email never arrived" could not be diagnosed from the app. The last
failure (exception class + SMTP reply code/text, credentials and addresses
masked) is now stored on the row and shown to admins. Additive; nullable.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'b9d4e1f7a2c3'
down_revision: Union[str, Sequence[str], None] = 'e5a1c7d3f820'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("notifications") as batch:
        batch.add_column(sa.Column("email_error", sa.String(length=200), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("notifications") as batch:
        batch.drop_column("email_error")
