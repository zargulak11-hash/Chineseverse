"""add users.google_sub for stable Google account linking

Revision ID: b7e4c2a9d1f3
Revises: a1c3f9e2d7b4
Create Date: 2026-09-30 10:00:00.000000

Google's `sub` claim is the account's permanent identifier; the email on a
Google account can change. Until now /api/auth/google matched users only by
exact-case email, so a Google identity could land on a different row than
intended (or a new one) on a database whose stored email differed only in
letter case. The column is nullable: existing rows get linked on their next
Google sign-in, and password-only accounts never need it.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'b7e4c2a9d1f3'
down_revision: Union[str, Sequence[str], None] = 'a1c3f9e2d7b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("google_sub", sa.String(length=255), nullable=True))
        batch.create_index("ix_users_google_sub", ["google_sub"], unique=True)


def downgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.drop_index("ix_users_google_sub")
        batch.drop_column("google_sub")
