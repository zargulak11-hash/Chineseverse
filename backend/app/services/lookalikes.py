"""Characters that LOOK alike (形近字): 己 / 已, 人 / 入 / 八, 未 / 末, 晴 / 睛 / 请...

Character DNA already shows the characters that share a radical or a
component (Hanzi.decomposition), and the mix-up memory (services/mixups.py)
remembers pairs THIS learner has confused. Neither catches the classic
look-alikes: many differ by one stroke's length or position and share no
listed component (己 / 已, 未 / 末, 土 / 士), and a learner meets them
before ever confusing them. These groups are the well-known teaching sets,
each a group of characters a reader can take for one another at a glance
(the kind Pleco's and Skritter's character study puts side by side). A
group only acts where its characters are in the curriculum.

Used in two places:
  * Character DNA shows "looks like" next to a character;
  * a character question offers a look-alike among its wrong options, so
    telling them apart is practised -- and a wrong pick becomes a tracked
    mix-up like any other (mixups.py).
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app import models

GROUPS = (
    "人入八", "己已", "土士", "未末", "天夫", "日曰目", "大太犬", "王玉主", "千干于", "午牛年",
    "田由甲申", "白百自", "刀力", "今令", "问间", "买卖", "休体", "处外", "找我", "很跟",
    "住往", "历厉", "鸟乌马", "贝见", "风凤", "设没", "汽气", "怕拍", "晴睛请清情", "读续",
    "侍待持特", "级极", "认让", "话活", "题提", "坐座", "目且", "木本术", "儿几", "又叉",
    "元无", "开井", "右石", "左在", "办为", "东车", "厂广", "视现", "拔拨", "贵责",
    "货贷", "漂飘", "哪那", "它他她", "门们", "宁守", "式试", "杨扬", "蓝篮", "渴喝",
    "玩完", "吃乞",
)
_OF: dict[str, set[str]] = {}
for _g in GROUPS:
    for _c in _g:
        _OF.setdefault(_c, set()).update(x for x in _g if x != _c)


def lookalikes(char: str) -> list[str]:
    """The characters that look like `char`, in a stable order."""
    return sorted(_OF.get(char, ()))


def partner_ids(db: Session, chars: set[str]) -> dict[str, list[int]]:
    """For each character: the Hanzi ids of its look-alikes that exist in the
    curriculum (lowest level first)."""
    wanted = {o for c in chars for o in _OF.get(c, ())}
    if not wanted:
        return {}
    by_char: dict[str, int] = {}
    for h in db.query(models.Hanzi).filter(models.Hanzi.character.in_(wanted)).order_by(
            models.Hanzi.hsk_level_id, models.Hanzi.id):
        by_char.setdefault(h.character, h.id)
    return {c: [by_char[o] for o in lookalikes(c) if o in by_char] for c in chars if c in _OF}
