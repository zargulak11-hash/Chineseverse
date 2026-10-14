"""add tone_attempts

Revision ID: f2a4c6e8b017
Revises: e4c6a8b0d215
Create Date: 2026-10-14 15:00:00.000000

The Tone Coach (services/tone_coach.py) judges the tones a learner says
from the pitch contour their browser measured. Each attempt keeps the
expected tones and the tone heard per syllable, so the coach can show
per-tone accuracy and confusions and choose what to practise next. A new
table only; rows go with their user (User.tone_attempts cascade).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'f2a4c6e8b017'
down_revision: Union[str, Sequence[str], None] = 'e4c6a8b0d215'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tone_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("item_type", sa.String(length=10), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("text", sa.String(length=10), nullable=False),
        sa.Column("expected", sa.String(length=20), nullable=False),
        sa.Column("verdict", sa.String(length=10), nullable=False),
        sa.Column("syllables", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_tone_attempts_id", "tone_attempts", ["id"])
    op.create_index("ix_tone_attempts_user_id", "tone_attempts", ["user_id"])
    op.create_index("ix_tone_attempts_created_at", "tone_attempts", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_tone_attempts_created_at", table_name="tone_attempts")
    op.drop_index("ix_tone_attempts_user_id", table_name="tone_attempts")
    op.drop_index("ix_tone_attempts_id", table_name="tone_attempts")
    op.drop_table("tone_attempts")
