"""fix the Tajik word for noodles in 牛肉面 (beef noodles)

Revision ID: e7b3c9d2f418
Revises: c3e5a7b9d102
Create Date: 2026-10-20 12:00:00.000000

The Tajik translations called 牛肉面 "решаи гӯшти гов" -- "реша" is a ROOT
in Tajik ("the root of beef"), not noodles. The Tajik word is "угро":
"угрои гӯшти гов". It sits in the Food words lesson, the noodle-ordering
scenario's title and description, one of its dialogue lines, the mission
that asks for it and the word's own meaning. The seed and the curriculum
snapshot carry the fixed text, but both are insert-only, so databases that
already have these rows keep the wrong one -- this updates them.

Each row is changed only while it still holds exactly the old seeded text:
anything an admin has edited since is left alone. Nothing about progress is
touched, nothing is deleted.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'e7b3c9d2f418'
down_revision: Union[str, Sequence[str], None] = 'c3e5a7b9d102'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

WRONG, RIGHT = "решаи гӯшти гов", "угрои гӯшти гов"
# (content_type, field, the exact seeded tg text)
ROWS = [
    ("lesson", "content",
     "米饭 mǐfàn = биринҷ, 茶 chá = чой, 水 shuǐ = об,\n牛肉面 niúròumiàn = решаи гӯшти гов, 苹果 píngguǒ = себ.\n"
     "一碗牛肉面，谢谢。 = Як коса решаи гӯшти гов, лутфан."),
    ("scenario", "title", "Фармоиши решаи гӯшти гов"),
    ("scenario", "description", "Як коса решаи гӯшти говро фармоиш диҳед ва ҳисобро пардохт кунед."),
    ("dialogue", "prompt", "Гӯй: Ман як коса решаи гӯшти гов мехоҳам."),
    ("vocab_word", "meanings", "решаи гӯшти гов"),
]
# The mission that asks for that scenario quoted its title another wrong way.
MISSION = ("'Фармоиши реша бо гӯшти гов'-ро бо овоз анҷом диҳед.",
           "'Фармоиши угрои гӯшти гов'-ро бо овоз анҷом диҳед.")


def _apply(forward: bool) -> None:
    bind = op.get_bind()
    for content_type, field, text in ROWS:
        old, new = text, text.replace(WRONG, RIGHT)
        if not forward:
            old, new = new, old
        bind.execute(sa.text(
            "UPDATE content_translations SET text = :new "
            "WHERE locale = 'tg' AND content_type = :ct AND field = :field AND text = :old"),
            {"new": new, "old": old, "ct": content_type, "field": field})
    old, new = MISSION if forward else MISSION[::-1]
    bind.execute(sa.text(
        "UPDATE content_translations SET text = :new "
        "WHERE locale = 'tg' AND content_type = 'mission' AND field = 'objective' AND text = :old"),
        {"new": new, "old": old})


def upgrade() -> None:
    _apply(True)


def downgrade() -> None:
    _apply(False)
