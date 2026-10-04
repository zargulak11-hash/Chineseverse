"""fix more OCR errors in the HSK 3.0 grammar syllabus

Revision ID: d8e2a5c1f736
Revises: c7d3f1a9e254
Create Date: 2026-10-04 12:00:00.000000

A proofread of all 602 grammar topics (mechanical checks for scan
artefacts, an AI pass, and a line-by-line read of every topic the AI quota
skipped -- each candidate checked by hand against the topic's own examples)
found seventeen more characters the scan of the official HSK 3.0 standard
got wrong. b3f7d2a9c614 fixed the first batch; this is the same treatment.

Titles (a separator or a character misread):
- 否定副词：另、不、没、没有 -> 别、... (its own example is 你别进来。)
- -儿、一家、-们、-头、-子 -> -家 (a suffix: 画家, 作家)
- 打开、看见，离开、完成 / 比较、更加，还、相当 -> 、 (list separator)
- A—+量词，B—+量词 -> A一+量词，B一+量词 (青一块，紫一块)

Examples:
- 传来中国之前 -> 他来中国之前 (传 for 他; the topic is pronoun back-reference)
- 无健康 -> 亚健康 (the 亚- prefix of the title, which otherwise had no example)
- 述不如 -> 还不如; 别管是淮 -> 别管是谁; 计你安静 -> 叫你安静
- 经营策略上一瘦大姐 -> 经营策略上——瘦大姐 (a dash read as 一)
- A跟B-样 -> A跟B一样; 宾语1+宾语？ -> 宾语1+宾语2
- a full stop or a lost comma between clauses: 留也不是.真, 别提了.我,
  比起其他人.我, 我北京人 今年二十五岁

Applied exactly like b3f7d2a9c614: each corrupted string (quoted with
enough context to be impossible in correct Chinese) is replaced wherever
it occurs -- grammar title/pattern/examples, lesson summary/content, lesson
and grammar-topic translations, grammar mistake references -- and every
row keeps its id, so learner progress, Pet Teacher cases and translations
stay attached. A row an admin already corrected no longer contains the bad
text and is left alone; a fresh database never had it (the re-exported
curriculum snapshot carries the corrected syllabus). Should a corrected
title already exist at the same level, the two rows are merged with the
same helper as before.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'd8e2a5c1f736'
down_revision: Union[str, Sequence[str], None] = 'c7d3f1a9e254'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TEXT_FIXES = [
    ("否定副词：另、不、没、没有", "否定副词：别、不、没、没有"),
    ("-儿、一家、-们", "-儿、-家、-们"),
    ("打开、看见，离开、完成", "打开、看见、离开、完成"),
    ("比较、更加，还、相当", "比较、更加、还、相当"),
    ("A—+量词，B—+量词", "A一+量词，B一+量词"),
    ("传来中国之前", "他来中国之前"),
    ("无烟 无健康 准妈妈", "无烟 亚健康 准妈妈"),
    ("与其去爬山，述不如", "与其去爬山，还不如"),
    ("别管是淮，都得挨骂", "别管是谁，都得挨骂"),
    ("计你安静你就安静", "叫你安静你就安静"),
    ("经营策略上一瘦大姐", "经营策略上——瘦大姐"),
    ("A跟B-样", "A跟B一样"),
    ("宾语1+宾语？", "宾语1+宾语2"),
    ("留也不是.真不知道", "留也不是，真不知道"),
    ("别提了.我根本", "别提了，我根本"),
    ("比起其他人.我的想法", "比起其他人，我的想法"),
    ("我北京人 今年二十五岁", "我北京人，今年二十五岁"),
]

CORRECTED_TITLES = [
    "否定副词：别、不、没、没有", "-儿、-家、-们、-头、-子", "动补式离合词：打开、看见、离开、完成",
    "程度副词：比较、更加、还、相当", "A一+量词，B一+量词",
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


def _merge_duplicates(conn, titles) -> None:
    """Same as b3f7d2a9c614: if a corrected title now exists twice at one
    level, keep the oldest row and move progress, Pet Teacher cases and
    translations onto it before removing the other."""
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


def upgrade() -> None:
    apply(op.get_bind())


def apply(conn) -> None:
    """The whole fix on one connection (tests/grammar_ocr_migration2_test.py
    runs it directly, twice)."""
    for column in ("title", "pattern", "examples"):
        _replace_column(conn, "grammar_topics", "id", column, TEXT_FIXES)
    for column in ("summary", "content"):
        _replace_column(conn, "lessons", "id", column, TEXT_FIXES)
    _replace_column(conn, "content_translations", "id", "text", TEXT_FIXES,
                    "AND content_type IN ('lesson', 'grammar_topic')")
    _replace_column(conn, "learning_mistakes", "id", "reference", TEXT_FIXES, "AND mistake_type = 'grammar'")
    _merge_duplicates(conn, CORRECTED_TITLES)


def downgrade() -> None:
    # A no-op, as in b3f7d2a9c614: re-introducing scan errors is never wanted.
    pass
