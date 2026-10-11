"""grammar patterns without English words in them

Revision ID: a7d3e9f1c246
Revises: e5a9c2d7b104
Create Date: 2026-10-10 14:00:00.000000

Seven core grammar patterns spelled their slots in English ("不 +
verb/adjective"), so a Russian, Tajik or Chinese learner read English inside
the formula. A pattern is not translated -- it is the Chinese being taught --
so it now uses the notation the other patterns already use in every
language: V, Adj, A/B, and Chinese terms (量词) as in 主语 + 把 + 宾语.

Only a row that still has exactly the old text is changed, so a pattern an
admin rewrote is left alone. Downgrade restores the old text the same way.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'a7d3e9f1c246'
down_revision: Union[str, Sequence[str], None] = 'e5a9c2d7b104'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PATTERNS = [
    ("不 — negation", "不 + verb/adjective", "不 + V/Adj"),
    ("会/能 — ability, possibility", "会/能 + verb", "会/能 + V"),
    ("几/多少 — asking quantity", "几 + measure word (small numbers) / 多少 (any size)", "几 + 量词 (≤10) / 多少"),
    ("比 — comparison", "A 比 B + adjective", "A 比 B + Adj"),
    ("得 (děi) — must", "得 + verb", "得 + V"),
    ("太……了 — excessively", "太 + adjective + 了", "太 + Adj + 了"),
    ("越来越 — increasingly", "越来越 + adjective/verb", "越来越 + Adj/V"),
]


def _swap(old_index: int, new_index: int) -> None:
    stmt = sa.text("UPDATE grammar_topics SET pattern = :new WHERE title = :title AND pattern = :old")
    for row in PATTERNS:
        op.execute(stmt.bindparams(title=row[0], old=row[old_index], new=row[new_index]))


def upgrade() -> None:
    _swap(1, 2)


def downgrade() -> None:
    _swap(2, 1)
