"""Sound World pronunciation lessons: tones, initials, finals, tone pairs,
tone changes, minimal pairs and short dialogues.

Each lesson is an explanation (in the learner's language), examples to
listen to, and a graded listening round played through the practice engine
(source "pronunciation", env = the lesson key). Every sound is the
browser's own Mandarin voice reading real Chinese text -- there are no
audio files and no fake recordings; a device without a Chinese voice shows
the pinyin instead (the same fallback as Sound World).

Question types (item_type "sound", rendered like Sound World):
  sound_tone      hear a character, pick its pinyin among the same syllable in four tones
  sound_pinyin    hear a word, pick its pinyin among confusable spellings
  sound_pair      hear one of a minimal pair, pick which word it was
  sound_tonepair  hear a two-syllable word, pick its tone pattern
  sound_dialogue  hear a two-line exchange, answer a question about it
A correct word answer moves that word's mastery like any listening item
(when the word is in the curriculum); nothing is scored by chance.
"""

from __future__ import annotations

import random

from sqlalchemy.orm import Session

from app import models

ROUND = 8          # questions per round
PASS = 80.0        # a lesson counts as passed at 80% or better
RATE = {"drill": 0.75, "dialogue": 0.85}
VOICES = {"teacher": ("老师", 1.0), "a": ("同学甲", 1.15), "b": ("同学乙", 0.88)}


class PronunciationError(Exception):
    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status = status
        self.detail = detail


def L(en, ru, tg, zh):
    return {"en": en, "ru": ru, "tg": tg, "zh": zh}


# Four tones: each set is one syllable in tones 1-4, written with real characters.
TONE_SETS = [
    [("妈", "mā"), ("麻", "má"), ("马", "mǎ"), ("骂", "mà")],
    [("八", "bā"), ("拔", "bá"), ("把", "bǎ"), ("爸", "bà")],
    [("衣", "yī"), ("姨", "yí"), ("椅", "yǐ"), ("意", "yì")],
    [("汤", "tāng"), ("糖", "táng"), ("躺", "tǎng"), ("烫", "tàng")],
    [("通", "tōng"), ("同", "tóng"), ("桶", "tǒng"), ("痛", "tòng")],
    [("方", "fāng"), ("房", "fáng"), ("访", "fǎng"), ("放", "fàng")],
    [("七", "qī"), ("骑", "qí"), ("起", "qǐ"), ("气", "qì")],
    [("书", "shū"), ("熟", "shú"), ("鼠", "shǔ"), ("树", "shù")],
    [("汪", "wāng"), ("王", "wáng"), ("网", "wǎng"), ("忘", "wàng")],
]

# Neutral tone: the right spelling, then spellings that give the second
# syllable a full tone (what learners tend to say).
NEUTRAL = [
    ("妈妈", "māma", ["māmā", "mámá", "māmà"]),
    ("爸爸", "bàba", ["bàbà", "bābā", "bàbā"]),
    ("朋友", "péngyou", ["péngyǒu", "pèngyou", "péngyōu"]),
    ("东西", "dōngxi", ["dōngxī", "dǒngxi", "dōngxì"]),
    ("谢谢", "xièxie", ["xièxiè", "xiēxie", "xièxiē"]),
    ("喜欢", "xǐhuan", ["xǐhuān", "xīhuan", "xǐhuàn"]),
    ("什么", "shénme", ["shénmè", "shěnme", "shénmē"]),
    ("漂亮", "piàoliang", ["piàoliàng", "piāoliang", "piàoliáng"]),
    ("孩子", "háizi", ["háizǐ", "hǎizi", "háizì"]),
]

# Initials that learners confuse: one word heard, the others are near misses.
INITIALS = [
    [("知", "zhī"), ("资", "zī"), ("鸡", "jī")],
    [("吃", "chī"), ("次", "cì"), ("七", "qī")],
    [("是", "shì"), ("四", "sì"), ("西", "xī")],
    [("爸", "bà"), ("怕", "pà"), ("大", "dà")],
    [("肚", "dù"), ("兔", "tù"), ("路", "lù")],
    [("哥", "gē"), ("科", "kē"), ("喝", "hē")],
    [("热", "rè"), ("乐", "lè"), ("这", "zhè")],
    [("男", "nán"), ("蓝", "lán"), ("难", "nàn")],
    [("鸡", "jī"), ("七", "qī"), ("西", "xī")],
]

# Finals: -n / -ng, u / ü, and similar vowels.
FINALS = [
    [("山", "shān"), ("伤", "shāng"), ("身", "shēn")],
    [("盆", "pén"), ("朋", "péng"), ("旁", "páng")],
    [("金", "jīn"), ("经", "jīng"), ("今", "jīn")],
    [("路", "lù"), ("绿", "lǜ"), ("六", "liù")],
    [("半", "bàn"), ("棒", "bàng"), ("笨", "bèn")],
    [("新", "xīn"), ("星", "xīng"), ("心", "xīn")],
    [("女", "nǚ"), ("怒", "nù"), ("你", "nǐ")],
    [("船", "chuán"), ("床", "chuáng"), ("穿", "chuān")],
]

# Tone pairs: two-syllable words and their written tone pattern.
TONE_PAIRS = [
    ("飞机", "fēijī", "1+1"), ("中国", "zhōngguó", "1+2"), ("铅笔", "qiānbǐ", "1+3"), ("生日", "shēngrì", "1+4"),
    ("同学", "tóngxué", "2+2"), ("牛奶", "niúnǎi", "2+3"), ("学校", "xuéxiào", "2+4"), ("明天", "míngtiān", "2+1"),
    ("老师", "lǎoshī", "3+1"), ("考试", "kǎoshì", "3+4"), ("小时", "xiǎoshí", "3+2"),
    ("汽车", "qìchē", "4+1"), ("问题", "wèntí", "4+2"), ("电脑", "diànnǎo", "4+3"), ("再见", "zàijiàn", "4+4"),
]
PATTERNS = [f"{a}+{b}" for a in range(1, 5) for b in range(1, 5)]

# Tone changes (sandhi): how it is SAID, then how it is written and other slips.
SANDHI = [
    ("你好", "ní hǎo", ["nǐ hǎo", "nǐ hào", "nì hǎo"]),
    ("很好", "hén hǎo", ["hěn hǎo", "hèn hǎo", "hēn hǎo"]),
    ("可以", "kéyǐ", ["kěyǐ", "kěyí", "kēyǐ"]),
    ("不是", "bú shì", ["bù shì", "bū shì", "bǔ shì"]),
    ("不对", "bú duì", ["bù duì", "bǔ duì", "bú duí"]),
    ("一个", "yí ge", ["yī ge", "yì ge", "yǐ ge"]),
    ("一起", "yìqǐ", ["yīqǐ", "yíqǐ", "yìqí"]),
    ("一天", "yì tiān", ["yī tiān", "yí tiān", "yǐ tiān"]),
]

# Minimal pairs: words that differ by one sound or one tone.
PAIRS = [
    [("买", "mǎi"), ("卖", "mài")], [("汤", "tāng"), ("糖", "táng")], [("四", "sì"), ("十", "shí")],
    [("睡觉", "shuìjiào"), ("水饺", "shuǐjiǎo")], [("大", "dà"), ("打", "dǎ")], [("想", "xiǎng"), ("像", "xiàng")],
    [("球", "qiú"), ("秋", "qiū")], [("问", "wèn"), ("文", "wén")], [("书", "shū"), ("树", "shù")],
    [("老师", "lǎoshī"), ("老是", "lǎoshì")],
]

# Short dialogues: (line A, line B, question, options, answer, question translation).
DIALOGUES = [
    (("你几点下课？", "nǐ jǐ diǎn xiàkè?"), ("我四点下课。", "wǒ sì diǎn xiàkè."),
     ("他几点下课？", "tā jǐ diǎn xiàkè?"), [("四点", "sì diǎn"), ("十点", "shí diǎn"), ("一点", "yī diǎn")], 0,
     ("When does he finish class?", "Во сколько он заканчивает занятия?", "Ӯ соати чанд аз дарс озод мешавад?")),
    (("这个多少钱？", "zhège duōshao qián?"), ("十五块。", "shíwǔ kuài."),
     ("这个多少钱？", "zhège duōshao qián?"), [("十五块", "shíwǔ kuài"), ("五十块", "wǔshí kuài"), ("十块", "shí kuài")], 0,
     ("How much is it?", "Сколько это стоит?", "Ин чанд пул аст?")),
    (("你想喝茶还是咖啡？", "nǐ xiǎng hē chá háishi kāfēi?"), ("茶，谢谢。", "chá, xièxie."),
     ("她想喝什么？", "tā xiǎng hē shénme?"), [("茶", "chá"), ("咖啡", "kāfēi"), ("水", "shuǐ")], 0,
     ("What would she like to drink?", "Что она хочет выпить?", "Ӯ чӣ нӯшидан мехоҳад?")),
    (("明天下雨吗？", "míngtiān xià yǔ ma?"), ("不下雨，是晴天。", "bú xià yǔ, shì qíngtiān."),
     ("明天天气怎么样？", "míngtiān tiānqì zěnmeyàng?"), [("晴天", "qíngtiān"), ("下雨", "xià yǔ"), ("下雪", "xià xuě")], 0,
     ("What will the weather be like tomorrow?", "Какая завтра погода?", "Пагоҳ ҳаво чӣ гуна мешавад?")),
    (("你的房间在几楼？", "nǐ de fángjiān zài jǐ lóu?"), ("在七楼。", "zài qī lóu."),
     ("房间在几楼？", "fángjiān zài jǐ lóu?"), [("七楼", "qī lóu"), ("一楼", "yī lóu"), ("十七楼", "shíqī lóu")], 0,
     ("Which floor is the room on?", "На каком этаже комната?", "Ҳуҷра дар ошёнаи чандум аст?")),
    (("我们坐地铁去吧。", "wǒmen zuò dìtiě qù ba."), ("好，地铁比出租车快。", "hǎo, dìtiě bǐ chūzūchē kuài."),
     ("他们怎么去？", "tāmen zěnme qù?"), [("坐地铁", "zuò dìtiě"), ("坐出租车", "zuò chūzūchē"), ("走路", "zǒulù")], 0,
     ("How are they going?", "Как они поедут?", "Онҳо чӣ тавр мераванд?")),
    (("你妈妈是老师吗？", "nǐ māma shì lǎoshī ma?"), ("不是，她是医生。", "bú shì, tā shì yīshēng."),
     ("妈妈做什么工作？", "māma zuò shénme gōngzuò?"), [("医生", "yīshēng"), ("老师", "lǎoshī"), ("学生", "xuésheng")], 0,
     ("What does the mother do?", "Кем работает мама?", "Модар чӣ кор мекунад?")),
    (("你喜欢吃米饭还是面条？", "nǐ xǐhuan chī mǐfàn háishi miàntiáo?"), ("我都喜欢，可是今天想吃面条。", "wǒ dōu xǐhuan, kěshì jīntiān xiǎng chī miàntiáo."),
     ("他今天想吃什么？", "tā jīntiān xiǎng chī shénme?"), [("面条", "miàntiáo"), ("米饭", "mǐfàn"), ("饺子", "jiǎozi")], 0,
     ("What does he want to eat today?", "Что он хочет съесть сегодня?", "Ӯ имрӯз чӣ хӯрдан мехоҳад?")),
]

LESSONS = [
    {"key": "tones", "icon": "〰️", "kind": "sound_tone",
     "title": L("The four tones", "Четыре тона", "Чор оҳанг", "四个声调"),
     "how": L("Mandarin has four tones: 1 high and level (mā), 2 rising (má), 3 low, dipping (mǎ), 4 falling (mà). The same syllable in another tone is another word: 妈 mother, 麻 hemp, 马 horse, 骂 to scold.",
              "В китайском четыре тона: 1 — высокий ровный (mā), 2 — восходящий (má), 3 — низкий нисходяще-восходящий (mǎ), 4 — нисходящий (mà). Тот же слог другим тоном — другое слово: 妈 мама, 麻 конопля, 马 лошадь, 骂 ругать.",
              "Дар забони чинӣ чор оҳанг ҳаст: 1 — баланд ва ҳамвор (mā), 2 — болоравӣ (má), 3 — паст ва хамида (mǎ), 4 — поёнравӣ (mà). Ҳамон ҳиҷо бо оҳанги дигар калимаи дигар аст: 妈 модар, 麻 канаб, 马 асп, 骂 дашном додан.",
              "普通话有四个声调：第一声高而平（mā），第二声上升（má），第三声先降后升（mǎ），第四声下降（mà）。同一个音节换一个声调，就是另一个词：妈、麻、马、骂。")},
    {"key": "neutral", "icon": "·", "kind": "sound_pinyin",
     "title": L("The neutral tone", "Нейтральный тон", "Оҳанги бетараф", "轻声"),
     "how": L("Many words end in a short, light syllable with no tone of its own: māma, péngyou, dōngxi. Say it quickly and softly; don't give it a full tone.",
              "Многие слова заканчиваются коротким лёгким слогом без собственного тона: māma, péngyou, dōngxi. Произносите его быстро и мягко, без полного тона.",
              "Бисёр калимаҳо бо ҳиҷои кӯтоҳ ва сабуке тамом мешаванд, ки оҳанги худ надорад: māma, péngyou, dōngxi. Онро зуд ва нарм гӯед, бе оҳанги пурра.",
              "很多词的最后一个音节又短又轻，没有自己的声调：māma、péngyou、dōngxi。说得快一点、轻一点，不要读成完整的声调。")},
    {"key": "initials", "icon": "🔤", "kind": "sound_pinyin",
     "title": L("Initials: zh ch sh, z c s, j q x", "Инициали: zh ch sh, z c s, j q x", "Ибтидоҳо: zh ch sh, z c s, j q x", "声母：zh ch sh、z c s、j q x"),
     "how": L("zh/ch/sh are said with the tongue curled back; z/c/s with the tongue behind the teeth; j/q/x with a smile, tongue flat. p, t, k come with a puff of air; b, d, g without.",
              "zh/ch/sh произносятся с загнутым назад языком; z/c/s — язык у зубов; j/q/x — с улыбкой, язык плоский. p, t, k — с придыханием; b, d, g — без него.",
              "zh/ch/sh бо забони ба қафо печида; z/c/s — забон дар паси дандонҳо; j/q/x — бо табассум, забон ҳамвор талаффуз мешаванд. p, t, k бо нафаси иловагӣ, b, d, g бе он.",
              "zh、ch、sh舌尖往后卷；z、c、s舌尖顶住牙齿后面；j、q、x嘴角像微笑，舌面放平。p、t、k要送气，b、d、g不送气。")},
    {"key": "finals", "icon": "🔡", "kind": "sound_pinyin",
     "title": L("Finals: -n / -ng, u / ü", "Финали: -n / -ng, u / ü", "Охирҳо: -n / -ng, u / ü", "韵母：-n / -ng、u / ü"),
     "how": L("-n ends at the front of the mouth (shān), -ng at the back (shāng). ü is i said with rounded lips: lǜ (green) is not lù (road).",
              "-n заканчивается во рту спереди (shān), -ng — сзади (shāng). ü — это i с округлёнными губами: lǜ (зелёный) — не lù (дорога).",
              "-n дар пеши даҳон тамом мешавад (shān), -ng дар қафо (shāng). ü — ин i бо лабони мудаввар аст: lǜ (сабз) ба lù (роҳ) баробар нест.",
              "-n在嘴的前面结束（shān），-ng在后面（shāng）。ü是把嘴唇圆起来说i：lǜ（绿）不是lù（路）。")},
    {"key": "tone_pairs", "icon": "🎼", "kind": "sound_tonepair",
     "title": L("Tone pairs", "Сочетания тонов", "Ҷуфтҳои оҳанг", "声调组合"),
     "how": L("Most words have two syllables, so tones come in pairs. Listen for the shape of the whole word: fēijī stays high, zàijiàn falls twice, xuéxiào rises then falls.",
              "Большинство слов двусложные, поэтому тоны идут парами. Слушайте рисунок всего слова: fēijī — ровно высоко, zàijiàn — два падения, xuéxiào — подъём, затем падение.",
              "Аксари калимаҳо дуҳиҷоӣ ҳастанд, бинобар ин оҳангҳо ҷуфт меоянд. Ба шакли тамоми калима гӯш диҳед: fēijī баланд мемонад, zàijiàn ду бор поён меравад, xuéxiào боло ва баъд поён.",
              "大部分词有两个音节，所以声调是成对出现的。听整个词的样子：fēijī一直很高，zàijiàn降了两次，xuéxiào先升后降。")},
    {"key": "sandhi", "icon": "🔀", "kind": "sound_pinyin",
     "title": L("Tone changes", "Изменение тонов", "Тағйири оҳангҳо", "变调"),
     "how": L("Two third tones together: the first is said as a second tone (nǐ hǎo → ní hǎo). 不 becomes bú before a fourth tone (bú shì). 一 is yí before a fourth tone and yì before the others. Pinyin keeps the written tones; your ear hears the changed ones.",
              "Два третьих тона подряд: первый произносится вторым (nǐ hǎo → ní hǎo). 不 перед четвёртым тоном звучит bú (bú shì). 一 перед четвёртым — yí, перед остальными — yì. В пиньине пишутся исходные тоны, а слышны изменённые.",
              "Ду оҳанги сеюм паси ҳам: аввалӣ бо оҳанги дуюм гуфта мешавад (nǐ hǎo → ní hǎo). 不 пеш аз оҳанги чорум bú мешавад (bú shì). 一 пеш аз оҳанги чорум yí ва пеш аз дигарҳо yì аст. Дар пинйин оҳангҳои аслӣ навишта мешаванд, гӯш тағйирёфтаро мешунавад.",
              "两个第三声在一起，第一个读成第二声（nǐ hǎo → ní hǎo）。“不”在第四声前面读bú（bú shì）。“一”在第四声前面读yí，在别的声调前面读yì。拼音写原来的声调，耳朵听到的是变了的声调。")},
    {"key": "pairs", "icon": "👂", "kind": "sound_pair",
     "title": L("Minimal pairs", "Минимальные пары", "Ҷуфтҳои ҳадди ақал", "听辨"),
     "how": L("These words differ by one sound or one tone — and mean completely different things: mǎi to buy, mài to sell; shuìjiào to sleep, shuǐjiǎo dumplings. Listen to the tone first.",
              "Эти слова различаются одним звуком или тоном — и значат совсем разное: mǎi купить, mài продать; shuìjiào спать, shuǐjiǎo пельмени. Сначала слушайте тон.",
              "Ин калимаҳо бо як овоз ё як оҳанг фарқ мекунанд ва маъноҳои тамоман дигар доранд: mǎi харидан, mài фурӯхтан; shuìjiào хобидан, shuǐjiǎo тушбера. Аввал ба оҳанг гӯш диҳед.",
              "这些词只差一个音或者一个声调，意思却完全不一样：mǎi买和mài卖，shuìjiào睡觉和shuǐjiǎo水饺。先听声调。")},
    {"key": "dialogues", "icon": "💬", "kind": "sound_dialogue",
     "title": L("Short dialogues", "Короткие диалоги", "Муколамаҳои кӯтоҳ", "短对话"),
     "how": L("Two people speak. Listen for the key word — a time, a price, a choice — then answer. You can replay each line.",
              "Говорят двое. Ищите ключевое слово — время, цену, выбор — и отвечайте. Каждую реплику можно переслушать.",
              "Ду нафар гап мезананд. Калимаи асосиро — вақт, нарх, интихоб — бишнавед ва ҷавоб диҳед. Ҳар ҷумларо боз гӯш кардан мумкин аст.",
              "两个人在说话。先听关键词——时间、价钱、选择——再回答。每一句都可以再听。")},
]
BY_KEY = {lesson["key"]: lesson for lesson in LESSONS}


def _examples(key: str) -> list[dict]:
    """What the lesson page lets the learner listen to before the round."""
    if key == "tones":
        return [{"zh": z, "py": p} for z, p in TONE_SETS[0]] + [{"zh": z, "py": p} for z, p in TONE_SETS[3]]
    if key == "neutral":
        return [{"zh": z, "py": p} for z, p, _ in NEUTRAL[:6]]
    if key == "initials":
        return [{"zh": z, "py": p} for g in INITIALS[:3] for z, p in g]
    if key == "finals":
        return [{"zh": z, "py": p} for g in FINALS[:3] for z, p in g[:2]]
    if key == "tone_pairs":
        return [{"zh": z, "py": p, "note": n} for z, p, n in TONE_PAIRS[::2]]
    if key == "sandhi":
        return [{"zh": z, "py": p} for z, p, _ in SANDHI]
    if key == "pairs":
        return [{"zh": z, "py": p} for g in PAIRS[:4] for z, p in g]
    return [{"zh": d[0][0], "py": d[0][1]} for d in DIALOGUES[:2]] + [{"zh": d[1][0], "py": d[1][1]} for d in DIALOGUES[:2]]


def _loc(d: dict, locale: str) -> str:
    return d.get(locale) or d["en"]


def _records(db: Session, user: models.User) -> dict[str, dict]:
    out: dict[str, dict] = {}
    rows = db.query(models.PracticeSession).filter(
        models.PracticeSession.user_id == user.id, models.PracticeSession.source == "pronunciation",
        models.PracticeSession.completed_at.isnot(None)).all()
    for s in rows:
        key = ((s.questions or [{}])[0].get("ctx") or {}).get("lesson")
        if key not in BY_KEY:
            continue
        r = out.setdefault(key, {"played": 0, "best": 0.0})
        r["played"] += 1
        r["best"] = max(r["best"], s.score or 0.0)
    return out


def lesson_list(db: Session, user: models.User, locale: str) -> dict:
    """The pronunciation course and this learner's real record in it. The
    next lesson is the first one not yet passed."""
    recs = _records(db, user)
    lessons = []
    for i, lesson in enumerate(LESSONS):
        r = recs.get(lesson["key"], {"played": 0, "best": 0.0})
        lessons.append({"key": lesson["key"], "n": i + 1, "icon": lesson["icon"],
                        "title": _loc(lesson["title"], locale), "title_zh": lesson["title"]["zh"],
                        "how": _loc(lesson["how"], locale), "examples": _examples(lesson["key"]),
                        "played": r["played"], "best": round(r["best"], 1), "passed": r["best"] >= PASS})
    nxt = next((x["key"] for x in lessons if not x["passed"]), None)
    return {"lessons": lessons, "next": nxt, "passed": sum(x["passed"] for x in lessons), "pass_score": PASS}


# --------------------------------------------------------------------------- the round

def _line(zh: str, py: str, voice: str = "teacher", kind: str = "drill") -> dict:
    label, pitch = VOICES[voice]
    return {"speaker": "teacher" if voice == "teacher" else "student", "speaker_zh": label,
            "zh": zh, "py": py, "pitch": pitch, "rate": RATE[kind]}


def _q(db: Session, qtype: str, lines: list[dict], options: list[dict], answer: int, focus_zh: str,
       rng: random.Random, ask: dict | None = None) -> dict:
    from app.services import internet

    order = list(range(len(options)))
    rng.shuffle(order)
    return {"type": qtype, "item_type": "sound", "answer_kind": "label", "lines": lines,
            "options": [options[i] for i in order], "item_id": order.index(answer),
            "option_ids": list(range(len(options))), "focus_id": internet._focus_of(db, focus_zh),
            "pron_ask": ask}


def build_questions(db: Session, user: models.User, key: str, rng: random.Random) -> list[dict]:
    lesson = BY_KEY.get(key or "")
    if lesson is None:
        raise PronunciationError(404, "Pronunciation lesson not found")
    qs: list[dict] = []
    if key == "tones":
        for group in rng.sample(TONE_SETS, min(ROUND, len(TONE_SETS))):
            k = rng.randrange(4)
            z, p = group[k]
            qs.append(_q(db, "sound_tone", [_line(z, p)], [{"label": py, "zh": zh} for zh, py in group], k, z, rng))
    elif key in ("neutral", "sandhi"):
        data = NEUTRAL if key == "neutral" else SANDHI
        for z, p, wrong in rng.sample(data, min(ROUND, len(data))):
            opts = [{"label": p, "zh": z}] + [{"label": w, "zh": z} for w in wrong]
            qs.append(_q(db, "sound_pinyin", [_line(z, p)], opts, 0, z, rng))
    elif key in ("initials", "finals"):
        data = INITIALS if key == "initials" else FINALS
        for group in rng.sample(data, min(ROUND, len(data))):
            uniq = list(dict.fromkeys(group))
            seen, opts = set(), []
            for zh, py in uniq:
                if py not in seen:
                    seen.add(py)
                    opts.append({"label": py, "zh": zh})
            k = rng.randrange(len(opts))
            qs.append(_q(db, "sound_pinyin", [_line(opts[k]["zh"], opts[k]["label"])], opts, k, opts[k]["zh"], rng))
    elif key == "tone_pairs":
        for z, p, pattern in rng.sample(TONE_PAIRS, min(ROUND, len(TONE_PAIRS))):
            others = rng.sample([x for x in PATTERNS if x != pattern], 3)
            opts = [{"label": pattern, "zh": z}] + [{"label": x, "zh": z} for x in others]
            qs.append(_q(db, "sound_tonepair", [_line(z, p)], opts, 0, z, rng))
    elif key == "pairs":
        for group in rng.sample(PAIRS, min(ROUND, len(PAIRS))):
            k = rng.randrange(len(group))
            z, p = group[k]
            opts = [{"label": f"{zh} {py}", "zh": zh} for zh, py in group]
            qs.append(_q(db, "sound_pair", [_line(z, p)], opts, k, z, rng))
    else:  # dialogues
        for a, b, q, options, answer, tr in rng.sample(DIALOGUES, min(ROUND, len(DIALOGUES))):
            lines = [_line(a[0], a[1], "a", "dialogue"), _line(b[0], b[1], "b", "dialogue")]
            opts = [{"label": zh, "py": py, "zh": zh} for zh, py in options]
            qs.append(_q(db, "sound_dialogue", lines, opts, answer, options[answer][0], rng,
                         ask={"zh": q[0], "py": q[1], "en": tr[0], "ru": tr[1], "tg": tr[2]}))
    qs[0]["ctx"] = {"kind": "pronunciation", "lesson": key, "icon": lesson["icon"], "titles": lesson["title"],
                    "how": lesson["how"]}
    return qs
