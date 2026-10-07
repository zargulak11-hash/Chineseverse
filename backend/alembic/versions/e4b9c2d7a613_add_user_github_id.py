"""add users.github_id for GitHub sign-in

Revision ID: e4b9c2d7a613
Revises: b6d4e8f2a915
Create Date: 2026-10-07 18:00:00.000000

"Continue with GitHub" (routers/auth.py /api/auth/github/*) needs the same
stable link Google has in users.google_sub: GitHub's numeric account id
never changes, while the login name and the email on the account can. The
column is nullable and starts empty for every existing row -- an existing
account is linked the first time its owner signs in with a GitHub account
whose verified email matches, exactly as Google linking works. No data is
touched.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'e4b9c2d7a613'
down_revision: Union[str, Sequence[str], None] = 'b6d4e8f2a915'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("github_id", sa.String(length=64), nullable=True))
        batch.create_index("ix_users_github_id", ["github_id"], unique=True)


def downgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.drop_index("ix_users_github_id")
        batch.drop_column("github_id")
