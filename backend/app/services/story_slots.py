"""Real-word slots for generated Chinese stories (Detective Mode, Sound World).

A generated case or soundscape is a hand-written sentence frame (zh and
pinyin side by side, e.g. "{when}，{who}在{place}。" / "{when}, {who} zài
{place}.") filled with REAL curriculum rows -- places, objects, foods,
people -- plus numbers and clock times written out in Chinese. Every word
a learner is asked about is therefore a VocabularyWord row: answering it
goes through apply_srs, mistakes and review like any other practice item.

Which rows fill the slots follows the learner: only words up to their
reach (HSK level + a small stretch), preferring words they are currently
learning, then a few new ones -- so the same frame reads differently for a
beginner and for an advanced learner.
"""

from __future__ import annotations

import random

from sqlalchemy.orm import Session

from app import models
from app.services.localization import load_translations, tr

# Candidate words per slot category. Only rows that exist in the database
# are ever used (filtered at runtime), so a missing word just isn't picked.
CATEGORIES: dict[str, tuple[str, ...]] = {
    "place": ("图书馆", "教室", "食堂", "商店", "医院", "银行", "超市", "公园", "宿舍", "办公室", "洗手间",
              "饭馆", "车站", "机场", "学校", "书店", "操场", "电影院", "体育馆", "博物馆", "停车场", "实验室",
              "厨房", "客厅", "房间"),
    "object": ("书", "手机", "钥匙", "钱包", "电脑", "杯子", "本子", "笔", "护照", "帽子", "眼镜", "手表",
               "词典", "照片", "礼物", "报纸", "地图", "票", "蛋糕", "衣服", "鞋", "围巾", "手套"),
    "food": ("苹果", "西瓜", "面条", "米饭", "饺子", "包子", "鸡蛋", "牛奶", "茶", "咖啡", "水果", "面包",
             "鱼", "香蕉", "葡萄", "豆腐", "汤", "果汁", "饼干", "糖", "蔬菜", "西红柿", "土豆"),
    "person": ("老师", "医生", "学生", "司机", "服务员", "经理", "警察", "记者", "律师", "护士", "邻居",
               "同学", "朋友", "老板", "校长"),
    "position": ("左边", "右边", "前边", "后边", "旁边", "楼上", "楼下", "里边", "外边", "对面", "中间"),
    "clothes": ("衣服", "裤子", "裙子", "鞋", "帽子", "手套", "围巾"),
    "color": ("红色", "黑色", "白色", "蓝色"),
    # Narrower lists where the scene needs things that make sense there.
    "breakable": ("手机", "电脑", "杯子", "手表", "眼镜", "笔"),
    "station_place": ("洗手间", "饭馆", "商店", "超市", "停车场", "书店", "银行", "门口"),
    "school_place": ("图书馆", "教室", "食堂", "操场", "办公室", "实验室", "体育馆", "宿舍", "洗手间"),
    "street_place": ("银行", "超市", "医院", "公园", "饭馆", "书店", "电影院", "商店", "车站", "博物馆", "学校"),
    "travel_object": ("护照", "手机", "电脑", "钱包", "票", "眼镜", "手表", "照片", "地图", "词典"),
}
# Measure words read 两 (not 二) before them.
_LIANG_UNITS = ("个", "张", "杯", "碗", "斤", "本", "位", "次", "份", "件", "双", "路")

_DIGITS = "零一二三四五六七八九"
_DIGITS_PY = ("líng", "yī", "èr", "sān", "sì", "wǔ", "liù", "qī", "bā", "jiǔ")


def num_zh(n: int) -> str:
    if n < 10:
        return _DIGITS[n]
    if n < 20:
        return "十" + (_DIGITS[n % 10] if n % 10 else "")
    if n < 100:
        return _DIGITS[n // 10] + "十" + (_DIGITS[n % 10] if n % 10 else "")
    if n < 1000:
        rest = n % 100
        tail = "" if rest == 0 else ("零" + _DIGITS[rest] if rest < 10 else (("一" if rest < 20 else "") + num_zh(rest)))
        return _DIGITS[n // 100] + "百" + tail
    return str(n)


def num_py(n: int) -> str:
    if n < 10:
        return _DIGITS_PY[n]
    if n < 20:
        return "shí" + (_DIGITS_PY[n % 10] if n % 10 else "")
    if n < 100:
        return _DIGITS_PY[n // 10] + "shí" + (_DIGITS_PY[n % 10] if n % 10 else "")
    if n < 1000:
        rest = n % 100
        tail = "" if rest == 0 else ("líng" + _DIGITS_PY[rest] if rest < 10 else (("yī" if rest < 20 else "") + num_py(rest)))
        return _DIGITS_PY[n // 100] + "bǎi" + tail
    return str(n)


def clock(h: int, m: int = 0) -> dict:
    """A clock time as {zh, py, label}: 下午三点半 / xiàwǔ sān diǎn bàn / 15:30."""
    prefix_zh, prefix_py, hh = "", "", h
    if 12 < h < 18:
        prefix_zh, prefix_py, hh = "下午", "xiàwǔ ", h - 12
    elif h >= 18:
        prefix_zh, prefix_py, hh = "晚上", "wǎnshang ", h - 12
    hour_zh = "两" if hh == 2 else num_zh(hh)
    hour_py = "liǎng" if hh == 2 else num_py(hh)
    if m == 0:
        tail_zh, tail_py = "", ""
    elif m == 30:
        tail_zh, tail_py = "半", " bàn"
    else:
        tail_zh, tail_py = num_zh(m) + "分", " " + num_py(m) + " fēn"
    return {"zh": f"{prefix_zh}{hour_zh}点{tail_zh}", "py": f"{prefix_py}{hour_py} diǎn{tail_py}",
            "label": f"{h}:{m:02d}"}


def number(n: int, unit_zh: str = "", unit_py: str = "") -> dict:
    zh = ("两" if n == 2 and unit_zh in _LIANG_UNITS else num_zh(n)) + unit_zh
    py = ("liǎng" if n == 2 and unit_zh in _LIANG_UNITS else num_py(n))
    return {"zh": zh, "py": f"{py} {unit_py}".strip(), "label": str(n)}


class Slots:
    """Picks real words for one generated story, for one learner."""

    def __init__(self, db: Session, user: models.User, level: int, rng: random.Random, stretch: int = 1):
        self.db, self.user, self.rng = db, user, rng
        self.reach = level + stretch
        self.used: set[int] = set()
        self._levels = {lvl.id: lvl.level for lvl in db.query(models.HSKLevel).all()}
        self._cache: dict[str, list[models.VocabularyWord]] = {}

    def rows(self, category: str) -> list[models.VocabularyWord]:
        if category not in self._cache:
            words = CATEGORIES[category]
            found = self.db.query(models.VocabularyWord).filter(models.VocabularyWord.simplified.in_(words)).all()
            best: dict[str, models.VocabularyWord] = {}
            for r in sorted(found, key=lambda r: (self._levels.get(r.hsk_level_id, 99), r.id)):
                best.setdefault(r.simplified, r)
            self._cache[category] = [best[w] for w in words if w in best]
        return self._cache[category]

    def level_of(self, row: models.VocabularyWord) -> int:
        return self._levels.get(row.hsk_level_id, 1)

    def pick(self, category: str, n: int, *, new_words: int = 1) -> list[models.VocabularyWord]:
        """n distinct words within reach: mostly ones the learner has met
        (learning first -- the words worth reinforcing), plus up to
        `new_words` they haven't, so every story also teaches."""
        pool = [r for r in self.rows(category) if self.level_of(r) <= self.reach and r.id not in self.used]
        if len(pool) < n:  # very low reach: allow the nearest levels above it
            extra = sorted((r for r in self.rows(category) if r not in pool and r.id not in self.used),
                           key=self.level_of)
            pool += extra[: n - len(pool)]
        recs = {r.word_id: r for r in self.db.query(models.UserVocabulary).filter(
            models.UserVocabulary.user_id == self.user.id,
            models.UserVocabulary.word_id.in_([r.id for r in pool] or [0]))}
        self.rng.shuffle(pool)
        known = [r for r in pool if r.id in recs and recs[r.id].status != "mastered"]
        mastered = [r for r in pool if r.id in recs and recs[r.id].status == "mastered"]
        fresh = [r for r in pool if r.id not in recs]
        out = fresh[:new_words] + known + mastered + fresh[new_words:]
        out = out[:n]
        self.rng.shuffle(out)
        self.used.update(r.id for r in out)
        return out


def word_slot(row: models.VocabularyWord) -> dict:
    return {"zh": row.simplified, "py": row.pinyin, "word_id": row.id}


def fill(frame: tuple[str, str], **slots: dict) -> dict:
    """Render a (zh, py) frame with slot dicts ({zh, py})."""
    zh, py = frame
    return {"zh": zh.format(**{k: v["zh"] for k, v in slots.items()}),
            "py": py.format(**{k: v["py"] for k, v in slots.items()})}


def _first_gloss(label: str) -> str:
    label = (label or "").split(";")[0].strip()
    return label.split(",")[0].strip() if len(label) > 28 else label


def meanings(db: Session, word_ids: list[int], locale: str, *, uniform: bool = False) -> dict[int, str]:
    """Short localized meaning per word (first gloss). zh UI reads the
    English gloss: the zh "meaning" of a word is the word itself.

    uniform=True is for a question's OPTIONS: one language for all of them.
    If any option has no translation in the learner's language, every
    option uses the English gloss -- a lone Russian option among English
    ones would give the answer away (same rule as practice._option_labels)."""
    rows = db.query(models.VocabularyWord).filter(models.VocabularyWord.id.in_(word_ids or [0])).all()
    trs = load_translations(db, "vocab_word", [str(r.id) for r in rows], locale)
    out, translated = {}, set()
    for r in rows:
        label = tr(trs, r.id, "meanings", r.meanings) or r.meanings or ""
        if label.strip() == r.simplified:
            label = r.meanings or ""
        if label != (r.meanings or ""):
            translated.add(r.id)
        out[r.id] = _first_gloss(label)
    if uniform and locale in ("ru", "tg") and len(translated) < len(rows):
        out = {r.id: _first_gloss(r.meanings or "") for r in rows}
    return out


def gloss(db: Session, text: str, locale: str) -> list[dict]:
    """Word-by-word reading aid for a generated line: each curriculum word
    with its pinyin and localized meaning (the "explain the Chinese" part
    of a mistake). Nothing is invented: unknown pieces carry no meaning."""
    from app.services import sentence as sent

    tokens = sent.segment(db, text)
    ids = [t["word"].id for t in tokens if t["word"] is not None]
    m = meanings(db, ids, locale)
    out = []
    for t in tokens:
        if t["kind"] == "other":
            continue
        w = t["word"]
        out.append({"text": t["text"], "pinyin": w.pinyin if w else "", "meaning": m.get(w.id, "") if w else ""})
    return out
