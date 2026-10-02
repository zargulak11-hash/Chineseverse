"""fix vocabulary rows imported with the wrong reading (gloss / pinyin)

Revision ID: c8e4a1f6b2d9
Revises: b3f7d2a9c614
Create Date: 2026-10-02 15:00:00.000000

The vocabulary was imported from drkameleon/complete-hsk-vocabulary
(CC-CEDICT data), whose entries list several readings ("forms") per word.
The importer always took the first one, so 516 rows show a reading the HSK
word is not learned for -- and practice built its questions from them:

- 339 surname / "variant of" / "see" readings: 白 "surname Bai" (Bái),
  后 "surname Hou", 个 "used in 自个儿", 鸟 "variant of 屌; penis"
- 83 proper-noun readings: 大学 "the Great Learning (Confucian classic)",
  西 "Spain", 加 "Canada", 现代 "Hyundai", 联想 "Lenovo"
- 71 rare readings of common characters: 打 "dozen" (dá) for dǎ, 跑 "(of
  an animal) to paw the ground" (páo) for pǎo, 离 "mythical beast" (chī)
  for lí, 页 "head" (xié) for yè, 要 yāo for yào, 吧 "bar" (bā) for the
  particle ba
- 23 malformed pinyin: "lu:è" -> lüè, "nu:è" -> nüè, "Aò" -> Ào, and the
  numeric neutral tone left on 10 erhua words ("lí pǔr5" -> lí pǔr). Two of
  those erhua words, which the source dictionary does not list, also had a
  wrong gloss: 离谱儿 "Scientific" and 贪玩儿 "Greedy" now carry CC-CEDICT's
  sense of 离谱 / 贪玩 (outrageous; ridiculous / to be too fond of play)

Plus one seed example that did not contain its word (二: "两个人。"),
replaced with the official HSK 1 syllabus line for 二 (EXAMPLE_FIXES).

c8e4a1f6b2d9_vocab_gloss_fixes.json holds every replacement, each taken
from the same source entry: the reading (pinyin + its first three senses)
that the HSK word actually is, chosen by its level and part of speech
where a word has several (后 hòu "back; behind", not "empress"; 干 at HSK 1
gàn "to do"); for a few core words the HSK sense is moved to the front of
that reading's own sense list (干 "to do", 克 "gram", 别 "don't ...!").
No meaning is written that the source does not contain. The 9 words whose
source entry has no real sense at all (e.g. 干吗 "see 干嘛") are left as
they are. Entries apply in file order (a later entry may continue from an
earlier one's result).

Guarded: a row changes only while its pinyin AND meanings are still exactly
the values the entry expects, so an admin's correction is never
overwritten, and a database that already has the fixed rows (a fresh one,
seeded from the re-exported snapshot) is untouched. Row ids, translations
and every learner's progress on these words stay as they are.
"""
import json
import os
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'c8e4a1f6b2d9'
down_revision: Union[str, Sequence[str], None] = 'b3f7d2a9c614'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

FIXES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "c8e4a1f6b2d9_vocab_gloss_fixes.json")


def load_fixes() -> list[list]:
    """[level, simplified, old pinyin, old meanings, new pinyin, new meanings]"""
    with open(FIXES_PATH, encoding="utf-8") as f:
        return json.load(f)


def apply(conn) -> int:
    level_id = dict(conn.execute(sa.text("SELECT level, id FROM hsk_levels")).fetchall())
    changed = 0
    for level, word, old_pinyin, old_meanings, new_pinyin, new_meanings in load_fixes():
        if level not in level_id:
            continue
        changed += conn.execute(
            sa.text(
                "UPDATE vocabulary_words SET pinyin = :np, meanings = :nm "
                "WHERE hsk_level_id = :l AND simplified = :w AND pinyin = :op AND meanings = :om"
            ),
            {"np": new_pinyin, "nm": new_meanings, "l": level_id[level], "w": word,
             "op": old_pinyin, "om": old_meanings},
        ).rowcount or 0
    return changed


# Seed examples that do not contain their own word. 二's was "两个人。" -- a
# sentence about 两, which is exactly what a learner must not take 二 for.
# Replaced with the official HSK 1 syllabus line for 二 (grammar point
# 一、二/两、三...), which shows 二 in numbers and 两 beside it.
EXAMPLE_FIXES = [
    (1, "二", "两个人。", "十二 二十 二百 两百", "shí'èr èrshí èrbǎi liǎngbǎi"),
]


def apply_examples(conn) -> int:
    level_id = dict(conn.execute(sa.text("SELECT level, id FROM hsk_levels")).fetchall())
    changed = 0
    for level, word, old, new, new_pinyin in EXAMPLE_FIXES:
        if level in level_id:
            changed += conn.execute(
                sa.text("UPDATE vocabulary_words SET example = :e, example_pinyin = :p "
                        "WHERE hsk_level_id = :l AND simplified = :w AND example = :old"),
                {"e": new, "p": new_pinyin, "l": level_id[level], "w": word, "old": old},
            ).rowcount or 0
    return changed


def upgrade() -> None:
    conn = op.get_bind()
    apply(conn)
    apply_examples(conn)


def downgrade() -> None:
    # Deliberately a no-op: putting "surname Bai", "dozen" for 打 or "penis"
    # for 鸟 back in front of learners is never wanted.
    pass
