"""fix vocabulary rows that teach the wrong reading of a common word

Revision ID: c9e4f2a7b318
Revises: f6c2a8d4e197
Create Date: 2026-10-09 10:00:00.000000

The HSK 3.0 vocabulary was imported with each word's FIRST dictionary
sense. For a handful of everyday words with two readings that first sense
is the rare literary one, so learners were taught the wrong word:
便宜 (HSK 2) as biàn yí "convenient" instead of piányi "cheap", 告诉 as
"to press charges" instead of "to tell", 大夫 as "senior official (in
imperial China)" instead of "doctor", and so on. Those glosses show up as
practice options, in the mistake notebook and in the word helper.

Each row is corrected to the reading the HSK level actually teaches (the
pinyin keeps the imported rows' spaced style). A row is only touched while
its gloss still starts with the known wrong text -- one an admin already
corrected is left alone -- and the row keeps its id, so learners' review
records stay attached. Genuine two-word polyphones (看 kàn/kān, 假 jiǎ/jià,
得 de/dé ...) are separate HSK entries and are not touched. A fresh
database gets the corrected rows from the curriculum snapshot, which
carries the same fix.

Downgrade restores nothing: the old glosses were wrong.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c9e4f2a7b318'
down_revision: Union[str, Sequence[str], None] = 'f6c2a8d4e197'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (HSK level, word, the wrong gloss starts with, pinyin, gloss)
FIXES = (
    (1, "告诉", "to press charges", "gào su", "to tell; to inform; to let know"),
    (1, "地方", "region; regional", "dì fang", "place; space; part"),
    (2, "便宜", "convenient", "pián yi", "cheap; inexpensive"),
    (2, "故事", "old practice", "gù shi", "story; tale"),
    (2, "好处", "easy to get along with", "hǎo chù", "benefit; advantage; good point"),
    (2, "结果", "to bear fruit", "jié guǒ", "result; outcome; as a result"),
    (3, "大夫", "senior official", "dài fu", "doctor; physician"),
    (3, "生意", "life force", "shēng yi", "business; trade"),
    (3, "本事", "source material", "běn shi", "ability; skill"),
    (3, "工夫", "(old) laborer", "gōng fu", "time; spare time; effort"),
    (3, "千万", "ten million", "qiān wàn", "be sure to; must by all means; ten million"),
    (4, "大方", "expert; scholar", "dà fang", "generous; natural and poised; in good taste"),
    (4, "人家", "household; dwelling", "rén jia", "other people; others; (rénjiā) household, family"),
    (7, "地道", "tunnel; causeway", "dì dao", "authentic; genuine; proper; (dìdào) tunnel"),
)


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    for level, word, wrong, pinyin, meanings in FIXES:
        bind.execute(
            sa.text(
                "UPDATE vocabulary_words SET pinyin = :pinyin, meanings = :meanings "
                "WHERE simplified = :word AND meanings LIKE :wrong "
                "AND hsk_level_id IN (SELECT id FROM hsk_levels WHERE level = :level)"
            ),
            {"pinyin": pinyin, "meanings": meanings, "word": word, "wrong": wrong + "%", "level": level},
        )


def downgrade() -> None:
    """Downgrade schema: nothing to restore (see the module docstring)."""
