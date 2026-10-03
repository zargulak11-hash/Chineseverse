"""rename "DNA Duel" in the first-duel mission and achievement texts

Revision ID: a4c7e2d9f1b3
Revises: f3b8d1c6a274
Create Date: 2026-10-03 12:00:00.000000

The Learning DNA is now presented to learners as the Learning Compass, so
"DNA Duel" no longer names anything in the app (they are just Duels). The
seed and the curriculum snapshot carry the new text, but both are
insert-only, so databases that already have these rows keep the old one --
this updates them.

Each row is changed only while it still holds exactly the old seeded text:
anything an admin has edited since is left alone. Nothing about progress is
touched.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'a4c7e2d9f1b3'
down_revision: Union[str, Sequence[str], None] = 'f3b8d1c6a274'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

OLD_EN = "Win your first DNA Duel."
NEW_EN = "Win your first Duel."
# locale -> (old, new) for the ru/tg/zh translations of that same text.
LOCALIZED = {
    "ru": ("Выиграйте свою первую ДНК-дуэль.", "Выиграйте свою первую дуэль."),
    "tg": ("Аввалин дуэли ДНК-и худро бибаред.", "Аввалин дуэли худро бибаред."),
    "zh": ("赢得你的第一场DNA对决。", "赢得你的第一场对决。"),
}


def _apply(forward: bool) -> None:
    bind = op.get_bind()
    old_en, new_en = (OLD_EN, NEW_EN) if forward else (NEW_EN, OLD_EN)
    bind.execute(sa.text("UPDATE missions SET objective = :new WHERE slug = 'first-duel' AND objective = :old"),
                 {"new": new_en, "old": old_en})
    bind.execute(sa.text("UPDATE achievements SET description = :new WHERE code = 'duel_win' AND description = :old"),
                 {"new": new_en, "old": old_en})
    for locale, (old, new) in LOCALIZED.items():
        if not forward:
            old, new = new, old
        bind.execute(sa.text(
            "UPDATE content_translations SET text = :new "
            "WHERE locale = :locale AND text = :old AND ("
            " (content_type = 'mission' AND field = 'objective' AND content_key IN"
            "   (SELECT CAST(id AS VARCHAR(40)) FROM missions WHERE slug = 'first-duel'))"
            " OR (content_type = 'achievement' AND field = 'description' AND content_key IN"
            "   (SELECT CAST(id AS VARCHAR(40)) FROM achievements WHERE code = 'duel_win')))"),
            {"new": new, "old": old, "locale": locale})


def upgrade() -> None:
    _apply(True)


def downgrade() -> None:
    _apply(False)
