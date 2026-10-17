"""add password_reset_tokens

Revision ID: c3e5a7b9d102
Revises: b8d0f2a4c615
Create Date: 2026-10-17 12:00:00.000000

There was no way back into an account whose password was forgotten, and a
Google- or GitHub-created account had a random password nobody knew, so it
could never sign in where only passwords work (the Android app). "Forgot
password" now emails a single-use, 30-minute link; this table holds only
the SHA-256 of each link's token (services/password_reset.py), never the
token itself.

A new, empty table: no existing row is touched. Rows go with their user
(ondelete CASCADE, and User.password_reset_tokens for the ORM).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'c3e5a7b9d102'
down_revision: Union[str, Sequence[str], None] = 'b8d0f2a4c615'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("token_hash", name="uq_password_reset_tokens_token_hash"),
    )
    op.create_index("ix_password_reset_tokens_id", "password_reset_tokens", ["id"])
    op.create_index("ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_password_reset_tokens_user_id", table_name="password_reset_tokens")
    op.drop_index("ix_password_reset_tokens_id", table_name="password_reset_tokens")
    op.drop_table("password_reset_tokens")
