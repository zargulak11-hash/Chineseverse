"""mark which content translations are drafts awaiting native review

Revision ID: d4f8a1c3e925
Revises: c9e4f2a7b318
Create Date: 2026-10-09 16:00:00.000000

Most vocabulary and Hanzi meanings had no Russian, Tajik or Chinese
translation, so a learner using those languages saw English glosses in
practice, the word helper and the mistake notebook. There is no Chinese-
Russian or Chinese-Tajik dictionary in the project to import from, so the
missing glosses are written as drafts. `source` says where a translation
came from: NULL for everything that existed before (authored), "draft" for
those written to close the gap. scripts/export_translation_review.py lists
the drafts for a native speaker; an admin who corrects one clears the mark.
Nothing about how a translation is served changes.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4f8a1c3e925'
down_revision: Union[str, Sequence[str], None] = 'c9e4f2a7b318'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("content_translations") as batch:
        batch.add_column(sa.Column("source", sa.String(length=20), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("content_translations") as batch:
        batch.drop_column("source")
