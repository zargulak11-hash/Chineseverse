"""add vocabulary_words.example_translation

Revision ID: c8a2f4e6b913
Revises: b5e1d7a3c962
Create Date: 2026-11-08 18:00:00.000000

A word's example sentence had no translation, so a learner who could not
yet read it learned nothing from it. Examples taken from the stories
library and the detective case files (scripts/seed_vocab_story_examples.py)
come with the translation their authors wrote: English is stored here,
Russian and Tajik as content translations (field "example_translation"),
like every other localized vocabulary field. Nullable, nothing backfilled
here -- the curriculum snapshot import fills it with the example.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c8a2f4e6b913"
down_revision: Union[str, Sequence[str], None] = "b5e1d7a3c962"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("vocabulary_words") as batch:
        batch.add_column(sa.Column("example_translation", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("vocabulary_words") as batch:
        batch.drop_column("example_translation")
