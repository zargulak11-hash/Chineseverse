"""drop the Chinese "meanings" that were only the word itself

Revision ID: e5a9c2d7b104
Revises: d4f8a1c3e925
Create Date: 2026-10-09 17:00:00.000000

scripts/seed_vocab_zh_mirror.py gave 538 words a Chinese "meaning" equal to
the word (喝 -> 喝) so a Chinese UI had something to show. It explains
nothing, and as a quiz option it gave the answer away, so practice fell back
to the English gloss -- a Chinese learner answered in English. Those rows
are now replaced by real short Chinese definitions (释义) from the curriculum
snapshot, which the startup seed inserts after this migration has run.

Only a row whose text is exactly the word is removed: a real definition an
admin wrote is never touched. Downgrade restores nothing (the mirrors were
placeholders, not translations).
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'e5a9c2d7b104'
down_revision: Union[str, Sequence[str], None] = 'd4f8a1c3e925'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        DELETE FROM content_translations
        WHERE content_type = 'vocab_word' AND field = 'meanings' AND locale = 'zh'
          AND text = (SELECT v.simplified FROM vocabulary_words v
                      WHERE CAST(v.id AS VARCHAR(40)) = content_translations.content_key)
        """
    )


def downgrade() -> None:
    pass
