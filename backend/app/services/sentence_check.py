"""Checking a learner's Chinese sentence -- correctness first, then why.

This exists because of a real grading bug. In Pet Teacher the companion says
我是很高兴。 and the learner fixes it to 我很高兴。 -- and was told to try
again. The correction was compared as one exact string (only spaces were
ignored), so 我很高兴 without 。, 我很高兴. or the equally good 我非常高兴。
all counted as wrong; and when the separately graded explanation was judged
thin, the page painted the whole answer red and showed "Correct sentence:
我很高兴。" -- the learner's own sentence -- as if it were the fix.

Grading a sentence therefore goes through one place, in this order:

  1. normalize   spaces, full/half-width punctuation and a missing or
                 different final mark never make a sentence wrong
  2. compare     the expected sentence and its accepted alternatives; a
                 degree adverb swapped for another (很/非常/真/特别/挺) is
                 an acceptable alternative, not an error
  3. detect      a small set of rules for well-known learner errors (是
                 before an adjective predicate, 不有, a number with no
                 measure word, ...). Each rule is conservative: it fires
                 only on the clear form of the mistake, and the sentences
                 that are RIGHT (我很高兴。 她很漂亮。 天气很好。) are in
                 tests/sentence_check_test.py so a rule can't creep onto them
  4. judge       anything else is a free-form answer that only a model can
                 judge fairly; ai_client.judge_sentence does it, given the
                 whole context, and the rules above still outrank it

Mandarin adjectives are predicates on their own -- 我很高兴。 needs no 是 --
so nothing here may ever require 是 before an adjective. 是 IS needed to
link two nouns (我是学生。), and rule `missing_shi` covers that case.

Verdicts (what the learner is told):
  correct      the expected sentence, possibly with other punctuation
  acceptable   a different but correct sentence (an alternative)
  close        one small slip away from the answer (a typo-sized change)
  incorrect    a grammar or vocabulary error, or a different sentence
  unchecked    free-form text with no expected answer and no known error
               (only a model can judge it)

Every result also carries `category` (exact, punctuation, alternative,
typo, unnatural, grammar, vocabulary, unchanged, different) and the `issues`
the rules found; issue codes are explained to the learner by the frontend
(i18n key grammarCheck.issue.<code>), so they read in the learner's language.
"""

from __future__ import annotations

import re
import unicodedata

_CJK = re.compile(r"[㐀-鿿]")

# Final/inner punctuation the learner may type either way. Commas and
# enumeration commas are folded together; sentence-final marks are dropped
# for comparison (a missing 。 is not a grammar error).
_PUNCT_MAP = str.maketrans({
    ",": "，", "、": "，", ";": "；", ":": "：", "?": "？", "!": "！", ".": "。",
    "．": "。", "｡": "。", "“": "", "”": "", "\"": "", "'": "", "‘": "", "’": "",
    "「": "", "」": "", "《": "", "》": "",
})
_FINAL = "。！？…~～"

# Degree adverbs that are interchangeable in front of an adjective predicate
# for grading purposes: 我很高兴。 and 我非常高兴。 are both right answers.
# (太……了 is excluded: it changes the meaning to "too", and 最 is a superlative.)
DEGREE = ("非常", "特别", "十分", "很", "真", "挺", "好")
_DEGREE_RE = re.compile("|".join(DEGREE))

# Closed lists for the rules below. The curriculum has no part-of-speech
# column, so each rule names the words it knows; a word not listed is simply
# not judged (the rules miss errors rather than invent them).
ADJECTIVES = (
    "高兴 开心 快乐 累 忙 好 坏 大 小 多 少 冷 热 贵 便宜 快 慢 远 近 高 矮 胖 瘦 新 旧 "
    "对 错 难 容易 干净 好看 好吃 好听 可爱 聪明 舒服 饿 渴 长 短 早 晚 漂亮 美 安静 "
    "认真 重要 有意思 年轻 老 帅 酷 白 黑 红 绿 蓝 黄 暖和 凉快 方便 健康 简单 努力 "
    "紧张 生气 难过 伤心 高 低 轻 重 厚 薄 亮 暗 甜 苦 辣 咸 酸 香 臭 忙碌 幸福 害怕"
).split()
# People/roles a learner says "I am ..." about. Nationality nouns (中国人)
# and dates/ages are left out on purpose: 他中国人。 / 今天星期五。 are real
# noun-predicate sentences (syllabus 主谓句3：名词谓语句).
ROLE_NOUNS = (
    "学生 老师 医生 护士 司机 工人 经理 律师 记者 警察 演员 歌手 厨师 服务员 大学生 "
    "中学生 小学生 留学生 作家 画家 农民 职员 工程师 运动员"
).split()
# Relationship nouns (朋友, 同学, 老板) are left out of ROLE_NOUNS: 我朋友 is
# also the noun phrase "my friend", so 我朋友，他很好 must not be flagged.
# 人, 字, 门 are left out: 一人一份, 一字一句 are set phrases and 门 is itself
# a measure word (一门课). So are containers and furniture that serve as
# borrowed measure words -- 一碗汤, 一桌子书, 一屋子人, 一盘子菜 (syllabus
# topic 借用量词) -- so 碗, 桌子, 房间, 盘子 are not listed either.
COUNT_NOUNS = (
    "苹果 书 朋友 学生 老师 孩子 杯子 椅子 本子 鸡蛋 包子 面包 电脑 "
    "手机 汽车 东西 问题 猫 狗 鸟 鱼 衣服 鞋 帽子 电影 窗户 学校 医院 商店 银行"
).split()
NUMERALS = "一二两三四五六七八九十几"
SUBJECTS = ("我们", "你们", "他们", "她们", "它们", "我", "你", "您", "他", "她", "它")
# Verbs that embed a question: 你知道他是谁吗？ is a correct yes/no question.
_EMBEDDING = ("知道", "记得", "明白", "清楚", "告诉", "问", "想知道", "觉得", "认识", "猜")

_ADJ = "|".join(sorted(ADJECTIVES, key=len, reverse=True))
_ROLE = "|".join(sorted(ROLE_NOUNS, key=len, reverse=True))
_NOUN = "|".join(sorted(set(COUNT_NOUNS), key=len, reverse=True))
_SUBJ = "|".join(SUBJECTS)
_DEG = "很|非常|特别|十分|挺|比较|真|有点儿|有点|太"

# Words ending in 是 that are not the copula (还是 "or", 但是 "but", ...).
_NOT_COPULA = "还但可就总于要只倒像算正凡老硬"

# (code, severity, pattern, unless). Patterns run on each clause separately,
# with the clause's final punctuation removed.
RULES: list[tuple[str, str, re.Pattern, re.Pattern | None]] = [
    # 我是很高兴 / 她是漂亮 -- a pronoun, 是, (degree adverb) and an
    # adjective ending the clause: the classic learner error, so an error.
    # 是 + adjective + 的 (他是很高兴的) and 是不是 don't match ($ / 不).
    ("shi_adj", "error",
     re.compile(rf"(?:{_SUBJ})是(?:{_DEG})?(?:{_ADJ})(?:了|啊|呀)?$"), None),
    # The same shape after a noun is only a warning: native Chinese uses an
    # emphatic 是 there (我同意，那电影是很有意思。 -- "it IS interesting"),
    # and the scan of the syllabus and story sentences found exactly these.
    # The concessive A是A (好看是好看，就是有点儿贵), 实在是/确实是, 什么是
    # and 而是 are not this at all and are excluded.
    ("shi_adj", "warning",
     re.compile(rf"(?<![{_NOT_COPULA}也都不实确在么而])是(?:{_DEG})?(?:{_ADJ})(?:了|啊|呀)?$"),
     re.compile(rf"({_ADJ})是\1|^(?:{_SUBJ})是")),
    # 不有 -> 没有 (有 is the one verb negated only with 没).
    ("bu_you", "error", re.compile(r"不有"), None),
    # 我有忙 -- 有 in front of an adjective; adjectives take 很, not 有.
    # 有点(儿)忙 is a different, correct word.
    # 有A有B (有老有少, 有男有女) is a fixed "some ... some ..." pattern.
    ("you_adj", "error",
     re.compile(rf"(?<!没)有(?!点|些|意思)(?:{_ADJ})$"), re.compile(r"有.{1,2}有")),
    # 我很学生 -- a degree adverb cannot modify a noun predicate.
    ("hen_noun", "error", re.compile(rf"(?:{_DEG})(?:{_ROLE})$"), None),
    # 我学生 -- two nouns need 是 between them.
    ("missing_shi", "error", re.compile(rf"^(?:{_SUBJ})(?:{_ROLE})$"), None),
    # 三苹果 -- a number needs a measure word before the noun. 一些 / 第一 /
    # 十一 (a bigger number) are excluded by requiring the numeral to be
    # followed directly by the noun.
    ("missing_measure", "error",
     # The look-behind also skips words that merely contain a numeral:
     # 星期一/周一 (星期一书店开门吗？), 统一, 唯一, 同一, 专一.
     re.compile(rf"(?<![第十百千万期周统唯同专])[{NUMERALS}](?:{_NOUN})"), re.compile(r"一些|一点")),
    # 他们是都学生 -- 都 goes before the verb.
    ("dou_order", "error", re.compile(r"是都"), None),
    # 你叫什么吗 -- a question word and 吗 ask twice. Embedded questions
    # (你知道他是谁吗？) are fine, so they are excluded.
    # Only the question word right before 吗 (or 为什么/怎么 anywhere): 你有
    # 什么问题吗？ uses 什么 as "any" and is a correct question.
    ("ma_question_word", "warning",
     re.compile(r"(?:什么|谁|哪儿|哪里|哪个|几|多少)吗$|(?:为什么|怎么).*吗$"),
     re.compile("|".join(_EMBEDDING))),
    # 我每天吃了早饭 -- 了 marks one completed event, not a routine.
    # A warning only: sentence-final 了 can mark a new habit (他现在每天都跑步了).
    # 除了 ("except") and a result 了 (排满了, 累极了) are not this 了.
    ("le_habitual", "warning", re.compile(r"每天.+了"), re.compile(r"了$|太.+了|除了|为了|[满极死]了")),
]

ISSUE_TOPIC = {
    # Grammar topic titles (curriculum natural keys) each issue is about, so
    # the result can link to the full grammar page.
    "shi_adj": "主谓句2：形容词谓语句",
    "you_adj": "主谓句2：形容词谓语句",
    "hen_noun": "是 — to be",
    "missing_shi": "是 — to be",
    "bu_you": "不 — negation",
    "missing_measure": "个 — measure word",
    "dou_order": "都 — all",
    "ma_question_word": "吗 — yes/no question",
    "le_habitual": "了 — completed action",
}


def normalize(text: str) -> str:
    """The sentence as compared: NFKC (full-width letters/digits), no spaces,
    one punctuation style, final marks dropped."""
    text = unicodedata.normalize("NFKC", text or "")
    # NFKC turns full-width ，？！ into ASCII; the map turns them back.
    text = re.sub(r"\s+", "", text).translate(_PUNCT_MAP).lower()
    return text.rstrip(_FINAL + "，")


def _degree_neutral(text: str) -> str:
    return _DEGREE_RE.sub("很", text)


def _clauses(text: str) -> list[str]:
    return [c for c in re.split(r"[，；：。！？…]", normalize(text)) if c]


def detect(text: str) -> list[dict]:
    """Known learner errors in `text`, as {code, severity, topic} -- in
    order of appearance, each code once."""
    found: dict[str, dict] = {}
    for clause in _clauses(text):
        for code, severity, pattern, unless in RULES:
            # A code reported as an error is never downgraded by its own
            # warning-level twin (shi_adj has both).
            if code in found and (found[code]["severity"] == "error" or severity == "warning"):
                continue
            if pattern.search(clause) and not (unless and unless.search(clause)):
                found[code] = {"code": code, "severity": severity, "topic": ISSUE_TOPIC.get(code)}
    return list(found.values())


def _distance(a: str, b: str) -> int:
    """Levenshtein distance, for "one character away" -- strings here are a
    sentence long, so the quadratic table is fine."""
    if a == b:
        return 0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def check(answer: str, expected: str | None = None, *, accepted: tuple[str, ...] | list[str] = (),
          wrong: str | None = None) -> dict:
    """Deterministic verdict on `answer`.

    `expected` and `accepted` are the right answers; `wrong` is the sentence
    the exercise started from (an answer equal to it is "unchanged"). The
    result's `final` says whether this verdict is settled; when it is False
    the sentence is a free-form answer the rules can neither accept nor
    reject, and a model (ai_client.judge_sentence) may judge it."""
    norm = normalize(answer)
    issues = detect(answer)
    errors = [i for i in issues if i["severity"] == "error"]
    targets = [t for t in [expected, *accepted] if t]

    def out(verdict: str, category: str, final: bool = True) -> dict:
        return {"verdict": verdict, "category": category, "issues": issues, "final": final, "source": "rules"}

    if not norm or not _CJK.search(norm):
        return out("incorrect", "different")
    if not targets:
        # Nothing to compare with: the rules can find a known error, but
        # finding none does not prove the sentence right -- only a model can
        # say that, so the verdict stays open.
        return out("incorrect", "grammar") if errors else out("unchecked", "unchecked", final=False)
    for t in targets:
        if norm == normalize(t):
            raw_same = re.sub(r"\s+", "", unicodedata.normalize("NFKC", answer)) == \
                re.sub(r"\s+", "", unicodedata.normalize("NFKC", t))
            return out("correct", "exact" if raw_same else "punctuation")
    if wrong and norm == normalize(wrong):
        return out("incorrect", "unchanged")
    if errors:
        return out("incorrect", "grammar")
    for t in targets:
        if _degree_neutral(norm) == _degree_neutral(normalize(t)):
            return out("correct", "alternative")
    for t in targets:
        nt = normalize(t)
        if len(nt) >= 3 and _distance(norm, nt) == 1:
            # One character off: a slip, not a different sentence. Not yet
            # final -- a model may recognise it as a valid alternative
            # (他很忙 for 她很忙 is a typo; 我很忙 for 我很累 is not).
            return out("close", "typo", final=False)
    return out("incorrect", "different", final=False)
