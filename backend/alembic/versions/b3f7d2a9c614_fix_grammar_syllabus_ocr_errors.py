"""fix OCR errors in the imported HSK 3.0 grammar syllabus

Revision ID: b3f7d2a9c614
Revises: a7d3c9e1f402
Create Date: 2026-10-02 14:00:00.000000

The grammar syllabus was imported from an OCR'd copy of the official HSK
3.0 standard (backend/data_sources/grammar_raw/, a PDF scan), and a few
characters came out wrong:

- "名重词" for 名量词 (HSK 5: 名量词：册、朵、幅、届、颗、匹、扇)
- "尽管⋯⋯，名声/可是⋯⋯" for 尽管⋯⋯，但是/可是⋯⋯ (HSK 5; its own examples
  use 但是)
- "无论⋯⋯，者15/也⋯⋯" for 无论⋯⋯，都/也⋯⋯ (HSK 4; its examples use 都)
- in examples: "舟" for 出 (没有出过什么错 / 容易出错), "自已" for 自己 and
  "这己是" for 这已是 (人人皆知的事实)

Two official points were also lost: the scan printed their closing bracket
as "］" instead of "】" ("【四29］一+量词+比+一+量词", "【六47］连⋯⋯也/都⋯⋯，
⋯⋯更⋯⋯"), so the importer folded each one, with its two example
sentences, into the examples of the point before it (一般来说 /
不是⋯⋯，还/还是⋯⋯). They are restored as their own topics, with exactly
those examples, and removed from the neighbour's.

A grammar title is not just a label: lessons find their grammar by the
title appearing in their text (services/practice.lesson_items), Review
finds a grammar mistake by LearningMistake.reference == title, and the
curriculum snapshot keys grammar rows and translations by (level, title).
So the corrected text is applied everywhere the corrupted text appears --
grammar title/pattern/examples, lesson summary/content, lesson
translations and grammar mistake references -- while every row keeps its
id. User progress (user_grammar), pet teacher cases and grammar
translations all point at ids, so they stay attached. Should a corrected
title already exist on another row at the same level, the two are merged
into the older row (progress, cases and translations moved, the duplicate
removed) -- so the fix can never leave two copies of a grammar point.

Every change is an exact replacement of the corrupted text: a row an admin
has already corrected (or edited) no longer contains it and is left alone,
and running this on a database that never had the bad text (a fresh one,
before the curriculum snapshot is imported) changes nothing -- the
re-exported snapshot already carries the corrected syllabus.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'b3f7d2a9c614'
down_revision: Union[str, Sequence[str], None] = 'a7d3c9e1f402'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Corrupted -> correct. Each corrupted string is impossible in real Chinese,
# so replacing it wherever it occurs cannot touch correct text.
TEXT_FIXES = [
    ("名重词", "名量词"),
    ("，名声/可是⋯⋯", "，但是/可是⋯⋯"),
    ("，者15/也⋯⋯", "，都/也⋯⋯"),
    ("没有舟过什么错", "没有出过什么错"),
    ("太容易舟错了", "太容易出错了"),
    ("都有自已的优点", "都有自己的优点"),
    ("这己是人人皆知", "这已是人人皆知"),
]

# The two folded points: (HSK level, the point's examples as they sit,
# corrupted, at the end of the previous point, that previous point's title,
# the restored title, its examples).
SPLITS = [
    (
        4, "一般来说",
        "\n【四29］一+量词+比+一+量词\n这些球鞋一双比一双好看。\n他的演出一次比一次精彩。",
        "一+量词+比+一+量词",
        "这些球鞋一双比一双好看。\n他的演出一次比一次精彩。",
    ),
    (
        6, "不是⋯⋯，还/还是⋯⋯",
        "\n【六47］连⋯⋯也/都⋯⋯，⋯⋯更⋯⋯\n连大人也做不到，孩子更做不到。\n连老人也喜欢看，孩子们更是喜欢得不得了。",
        "连⋯⋯也/都⋯⋯，⋯⋯更⋯⋯",
        "连大人也做不到，孩子更做不到。\n连老人也喜欢看，孩子们更是喜欢得不得了。",
    ),
]


def _replace_column(conn, table: str, key: str, column: str, pairs, where: str = "") -> None:
    for old, new in pairs:
        rows = conn.execute(
            sa.text(f"SELECT {key}, {column} FROM {table} WHERE {column} LIKE :pat {where}"),
            {"pat": f"%{old}%"},
        ).fetchall()
        for row_id, value in rows:
            conn.execute(
                sa.text(f"UPDATE {table} SET {column} = :v WHERE {key} = :id"),
                {"v": value.replace(old, new), "id": row_id},
            )


def _apply(conn, fixes) -> None:
    for column in ("title", "pattern", "examples"):
        _replace_column(conn, "grammar_topics", "id", column, fixes)
    for column in ("summary", "content"):
        _replace_column(conn, "lessons", "id", column, fixes)
    _replace_column(conn, "content_translations", "id", "text", fixes, "AND content_type = 'lesson'")
    _replace_column(conn, "learning_mistakes", "id", "reference", fixes, "AND mistake_type = 'grammar'")

    level_id = dict(conn.execute(sa.text("SELECT level, id FROM hsk_levels")).fetchall())
    for level, prev_title, folded, title, examples in SPLITS:
        lid = level_id.get(level)
        if lid is None:
            continue  # a fresh database: the snapshot brings the corrected syllabus
        prev = conn.execute(
            sa.text("SELECT id, examples, category, difficulty, order_index FROM grammar_topics "
                    "WHERE hsk_level_id = :l AND title = :t"),
            {"l": lid, "t": prev_title},
        ).fetchone()
        if prev is None or folded not in (prev.examples or ""):
            continue  # already fixed, or edited by an admin
        conn.execute(
            sa.text("UPDATE grammar_topics SET examples = :e WHERE id = :id"),
            {"e": prev.examples.replace(folded, ""), "id": prev.id},
        )
        exists = conn.execute(
            sa.text("SELECT 1 FROM grammar_topics WHERE hsk_level_id = :l AND title = :t"),
            {"l": lid, "t": title},
        ).fetchone()
        if exists is None:
            conn.execute(
                sa.text("INSERT INTO grammar_topics (hsk_level_id, title, pattern, explanation, examples, "
                        "category, difficulty, order_index) VALUES (:l, :t, :t, NULL, :e, :c, :d, :o)"),
                {"l": lid, "t": title, "e": examples, "c": prev.category, "d": prev.difficulty,
                 "o": prev.order_index},
            )
        # The lesson that quotes the folded block shows the restored point as
        # its own section and lists it in its summary, like every other point.
        for lesson_id, content, summary in conn.execute(
            sa.text("SELECT id, content, summary FROM lessons WHERE hsk_level_id = :l AND content LIKE :pat"),
            {"l": lid, "pat": f"%{folded}%"},
        ).fetchall():
            section = folded.replace(folded.split("\n")[1], title, 1)
            new_summary = summary
            if summary and f"{prev_title}; " in summary and title not in summary:
                new_summary = summary.replace(f"{prev_title}; ", f"{prev_title}; {title}; ", 1)
            conn.execute(
                sa.text("UPDATE lessons SET content = :c, summary = :s WHERE id = :id"),
                {"c": content.replace(folded, "\n" + section), "s": new_summary, "id": lesson_id},
            )


def _merge_duplicates(conn, titles) -> None:
    """If a corrected title now exists twice at one level (a row with the
    corrected title was already there -- e.g. re-imported by an older
    curriculum snapshot), keep the oldest row and fold the other into it:
    learner progress, pet teacher cases and translations move to the kept
    row (the kept row's own value wins on a clash), then the duplicate goes.
    """
    for title in titles:
        groups = conn.execute(
            sa.text("SELECT hsk_level_id, MIN(id) FROM grammar_topics WHERE title = :t "
                    "GROUP BY hsk_level_id HAVING COUNT(*) > 1"),
            {"t": title},
        ).fetchall()
        for level_id, keep in groups:
            dups = [r[0] for r in conn.execute(
                sa.text("SELECT id FROM grammar_topics WHERE hsk_level_id = :l AND title = :t AND id <> :k"),
                {"l": level_id, "t": title, "k": keep},
            ).fetchall()]
            for dup in dups:
                for uid, ug_id in conn.execute(
                    sa.text("SELECT user_id, id FROM user_grammar WHERE topic_id = :d"), {"d": dup}
                ).fetchall():
                    clash = conn.execute(
                        sa.text("SELECT id FROM user_grammar WHERE user_id = :u AND topic_id = :k"),
                        {"u": uid, "k": keep},
                    ).fetchone()
                    if clash:
                        conn.execute(sa.text("DELETE FROM user_grammar WHERE id = :i"), {"i": ug_id})
                    else:
                        conn.execute(sa.text("UPDATE user_grammar SET topic_id = :k WHERE id = :i"),
                                     {"k": keep, "i": ug_id})
                conn.execute(sa.text("UPDATE pet_teacher_cases SET grammar_topic_id = :k WHERE grammar_topic_id = :d"),
                             {"k": keep, "d": dup})
                for tid, field, locale in conn.execute(
                    sa.text("SELECT id, field, locale FROM content_translations "
                            "WHERE content_type = 'grammar_topic' AND content_key = :d"), {"d": str(dup)}
                ).fetchall():
                    clash = conn.execute(
                        sa.text("SELECT 1 FROM content_translations WHERE content_type = 'grammar_topic' "
                                "AND content_key = :k AND field = :f AND locale = :lc"),
                        {"k": str(keep), "f": field, "lc": locale},
                    ).fetchone()
                    if clash:
                        conn.execute(sa.text("DELETE FROM content_translations WHERE id = :i"), {"i": tid})
                    else:
                        conn.execute(sa.text("UPDATE content_translations SET content_key = :k WHERE id = :i"),
                                     {"k": str(keep), "i": tid})
                conn.execute(sa.text("DELETE FROM grammar_topics WHERE id = :d"), {"d": dup})


CORRECTED_TITLES = [
    "无论⋯⋯，都/也⋯⋯", "尽管⋯⋯，但是/可是⋯⋯", "名量词：册、朵、幅、届、颗、匹、扇",
    "一+量词+比+一+量词", "连⋯⋯也/都⋯⋯，⋯⋯更⋯⋯",
]


def upgrade() -> None:
    conn = op.get_bind()
    _apply(conn, TEXT_FIXES)
    _merge_duplicates(conn, CORRECTED_TITLES)


def downgrade() -> None:
    # Deliberately a no-op. Reversing the replacements cannot be done safely:
    # "，都/也⋯⋯" -> "，者15/也⋯⋯" would also corrupt the correct point
    # 不管⋯⋯，都/也⋯⋯, and re-introducing scan errors is never wanted. The
    # restored topics stay too -- learners may already have progress on them.
    pass
