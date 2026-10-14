"""add saved_sentences

Revision ID: a6c8e0b2d419
Revises: f2a4c6e8b017
Create Date: 2026-10-14 18:00:00.000000

The story reader's line-by-line mode lets a learner save a sentence they
found hard, to hear and practise it again later (services/stories.py).
A sentence is kept by its place in the book; its text is copied from the
book's content file. A new table only; rows go with their user.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'a6c8e0b2d419'
down_revision: Union[str, Sequence[str], None] = 'f2a4c6e8b017'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "saved_sentences",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("slug", sa.String(length=60), nullable=False),
        sa.Column("chapter", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("zh", sa.String(length=300), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("user_id", "slug", "chapter", "position", name="uq_saved_sentence"),
    )
    op.create_index("ix_saved_sentences_id", "saved_sentences", ["id"])
    op.create_index("ix_saved_sentences_user_id", "saved_sentences", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_saved_sentences_user_id", table_name="saved_sentences")
    op.drop_index("ix_saved_sentences_id", table_name="saved_sentences")
    op.drop_table("saved_sentences")
