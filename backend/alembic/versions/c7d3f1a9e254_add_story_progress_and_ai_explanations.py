"""add story_progress and ai_explanations: Chinese Stories as a reading library

Revision ID: c7d3f1a9e254
Revises: b5e2d8a4c193
Create Date: 2026-10-04 10:00:00.000000

Chinese Stories grows from single-page stories into books with chapters.
A learner needs a bookmark ("Continue reading" returns to the chapter and
sentence they left), finished chapters and the real help they asked for
while reading -- story_progress, one row per learner and book, created by
their first reading action. Book content stays in files
(seed_content/books), keyed by slug.

ai_explanations caches AI explanations of selected Chinese text. Its key
covers only what the answer depends on (text, kind, language, level band),
never the person, so identical requests don't pay twice.

New tables only: existing rows are untouched. Story rounds already played
keep counting (services/stories.py reads them for one-chapter books).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'c7d3f1a9e254'
down_revision: Union[str, Sequence[str], None] = 'b5e2d8a4c193'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "story_progress",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("slug", sa.String(length=60), nullable=False),
        sa.Column("chapter", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("chapters_done", sa.JSON(), nullable=False),
        sa.Column("explained", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("listened", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("looked_up", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("user_id", "slug", name="uq_story_progress"),
    )
    op.create_index("ix_story_progress_id", "story_progress", ["id"])
    op.create_index("ix_story_progress_user_id", "story_progress", ["user_id"])
    op.create_index("ix_story_progress_slug", "story_progress", ["slug"])

    op.create_table(
        "ai_explanations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("locale", sa.String(length=5), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_ai_explanations_id", "ai_explanations", ["id"])
    op.create_index("ix_ai_explanations_key", "ai_explanations", ["key"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_ai_explanations_key", table_name="ai_explanations")
    op.drop_index("ix_ai_explanations_id", table_name="ai_explanations")
    op.drop_table("ai_explanations")
    op.drop_index("ix_story_progress_slug", table_name="story_progress")
    op.drop_index("ix_story_progress_user_id", table_name="story_progress")
    op.drop_index("ix_story_progress_id", table_name="story_progress")
    op.drop_table("story_progress")
