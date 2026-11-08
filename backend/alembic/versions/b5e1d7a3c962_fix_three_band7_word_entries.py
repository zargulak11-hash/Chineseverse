"""fix three HSK 7-9 words that carried a single character's entry

Revision ID: b5e1d7a3c962
Revises: d4a9c2e7f150
Create Date: 2026-11-08 12:00:00.000000

The curriculum import gave three advanced-band words the dictionary entry
of one of their characters instead of their own -- pinyin AND English
meaning:

  得意扬扬  "yáng"  "ocean; vast; foreign"            (洋, not even 扬)
  火暴      "bào"   "to explode or burst; ..."         (爆)
  无可厚非  "fēi"   "to not be; not; wrong; ..."       (非)

so the vocabulary page, practice and review taught a learner to read a
four-syllable idiom as one syllable. Their Russian, Tajik and Chinese
meanings were already right. Found by checking every word's pinyin
syllables against its characters (these were the only mismatches among
11,334 words) and every multi-character word for a meaning identical to a
single character's (the same three).

The curriculum snapshot carries the fixed entries for new databases; the
seed is insert-only, so this updates databases that already have the rows.
A row is changed only while it still holds exactly the old pinyin and
meaning: anything an admin has edited is left alone. Progress is untouched
(the word ids don't change), nothing is deleted.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "b5e1d7a3c962"
down_revision: Union[str, Sequence[str], None] = "d4a9c2e7f150"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# simplified: (wrong pinyin, wrong meanings, right pinyin, right meanings)
FIXES = {
    "得意扬扬": ("yáng", "ocean; vast; foreign",
             "dé yì yáng yáng", "immensely pleased with oneself (idiom); proud; complacent"),
    "火暴": ("bào", "to explode or burst; to quick fry or quick boil",
           "huǒ bào", "fiery (temper); popular; flourishing; lively"),
    "无可厚非": ("fēi", "to not be; not; wrong; incorrect; non-; un-; in-; de-",
             "wú kě hòu fēi", "not to be blamed (idiom); not without justification; understandable"),
}


def _apply(forward: bool) -> None:
    bind = op.get_bind()
    for word, (bad_py, bad_m, good_py, good_m) in FIXES.items():
        old, new = ((bad_py, bad_m), (good_py, good_m)) if forward else ((good_py, good_m), (bad_py, bad_m))
        bind.execute(
            sa.text(
                "UPDATE vocabulary_words SET pinyin = :new_py, meanings = :new_m "
                "WHERE simplified = :word AND pinyin = :old_py AND meanings = :old_m"
            ),
            {"word": word, "old_py": old[0], "old_m": old[1], "new_py": new[0], "new_m": new[1]},
        )


def upgrade() -> None:
    _apply(True)


def downgrade() -> None:
    _apply(False)
