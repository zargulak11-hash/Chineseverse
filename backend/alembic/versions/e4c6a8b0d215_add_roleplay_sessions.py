"""add roleplay_sessions

Revision ID: e4c6a8b0d215
Revises: d8b2f4a6c193
Create Date: 2026-10-14 12:00:00.000000

AI roleplay (services/roleplay.py): the learner talks in their own words
with an AI partner in a real-life scenario and gets each message
corrected. Every conversation is kept -- its turns, the corrections and the
goals reached -- so the end-of-scenario summary is built from what really
happened and mistakes reach the notebook. A new table only; nothing
existing changes. Rows go with their user (User.roleplay_sessions cascade).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'e4c6a8b0d215'
down_revision: Union[str, Sequence[str], None] = 'd8b2f4a6c193'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "roleplay_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("scenario", sa.String(length=40), nullable=False),
        sa.Column("hsk_level", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("turns", sa.JSON(), nullable=False),
        sa.Column("goals_met", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("summary", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_roleplay_sessions_id", "roleplay_sessions", ["id"])
    op.create_index("ix_roleplay_sessions_user_id", "roleplay_sessions", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_roleplay_sessions_user_id", table_name="roleplay_sessions")
    op.drop_index("ix_roleplay_sessions_id", table_name="roleplay_sessions")
    op.drop_table("roleplay_sessions")
