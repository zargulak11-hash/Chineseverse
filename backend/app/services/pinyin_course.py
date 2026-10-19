"""The pinyin foundation course: step 1 of the journey (/foundation).

A beginner who has never seen pinyin used to land on one page showing
mā/má/mǎ/mà and then a graded round of HSK 1 characters they had never
met, shown without sound and asked for their tone -- a guess, not a test
of anything taught. This course teaches the sound system in order, each
unit as a short lesson:

  explain   what the unit is about, in the learner's language
  examples  real syllables to hear (the browser's Chinese voice)
  try it    a few guided questions on the page, answered with an
            explanation, nothing graded or stored
  check     a graded mastery round through the practice engine (source
            "pronunciation", env = the unit key), passed at
            pronunciation.PASS, like the Sound World course it extends

Units, in teaching order:
  py_syllable   a syllable = initial + final + tone (read: name the parts)
  py_tones      the four tones and the light one (read the mark, hear it)
  py_initials1  b p m f / d t n l / g k h, and the puff of air of p t k
  py_initials2  j q x / zh ch sh r / z c s
  py_finals     the vowels, ü, -n and -ng
  py_spelling   y and w, ü written u, where the tone mark goes

Every syllable is a real one written with a real character; nothing is
scored by chance, and a wrong answer says exactly what differed (the
initial, the final, the tone, the spelling rule) -- see explain().
"""

from __future__ import annotations

import random

from sqlalchemy.orm import Session

from app import models
from app.services.pronunciation import PASS, ROUND, TONE_SETS, L, _line, _loc, _q

TONE_OF = {}
for _v, _marks in (("a", "āáǎà"), ("e", "ēéěè"), ("i", "īíǐì"), ("o", "ōóǒò"), ("u", "ūúǔù"), ("ü", "ǖǘǚǜ")):
    for _n, _m in enumerate(_marks, 1):
        TONE_OF[_m] = (_n, _v)
INITIALS = ("zh", "ch", "sh", "b", "p", "m", "f", "d", "t", "n", "l", "g", "k", "h", "j", "q", "x", "r", "z", "c", "s")


def tone_of(py: str) -> int:
    """The tone of ONE written syllable: 1-4 from its mark, 0 (light) without one."""
    return next((TONE_OF[ch][0] for ch in py if ch in TONE_OF), 0)


def plain(py: str) -> str:
    """The syllable without its tone mark (ü keeps its dots)."""
    return "".join(TONE_OF[ch][1] if ch in TONE_OF else ch for ch in py)


def split(py: str) -> tuple[str, str]:
    """(initial, final) of one syllable, tone removed. No initial -> ""."""
    p = plain(py.strip().lower())
    for ini in INITIALS:
        if p.startswith(ini) and len(p) > len(ini):
            return ini, p[len(ini):]
    return "", p


# --------------------------------------------------------------------------- content

# (character, pinyin, initial, final) -- the syllables the first unit takes apart.
SYLLABLES = [
    ("妈", "mā", "m", "a"), ("好", "hǎo", "h", "ao"), ("你", "nǐ", "n", "i"), ("书", "shū", "sh", "u"),
    ("爱", "ài", "", "ai"), ("茶", "chá", "ch", "a"), ("看", "kàn", "k", "an"), ("忙", "máng", "m", "ang"),
    ("冷", "lěng", "l", "eng"), ("很", "hěn", "h", "en"), ("高", "gāo", "g", "ao"), ("狗", "gǒu", "g", "ou"),
    ("饭", "fàn", "f", "an"), ("来", "lái", "l", "ai"), ("中", "zhōng", "zh", "ong"), ("安", "ān", "", "an"),
    ("饿", "è", "", "e"), ("是", "shì", "sh", "i"),
]

# Groups of real syllables that differ only in the initial (same final, same tone).
INITIALS_1 = [
    [("八", "bā"), ("趴", "pā"), ("妈", "mā"), ("发", "fā")],
    [("爸", "bà"), ("怕", "pà")],
    [("拔", "bá"), ("爬", "pá")],
    [("肚", "dù"), ("兔", "tù"), ("路", "lù")],
    [("地", "dì"), ("替", "tì"), ("力", "lì")],
    [("多", "duō"), ("拖", "tuō")],
    [("男", "nán"), ("蓝", "lán")],
    [("哥", "gē"), ("科", "kē"), ("喝", "hē")],
    [("古", "gǔ"), ("苦", "kǔ"), ("虎", "hǔ")],
]
INITIALS_2 = [
    [("鸡", "jī"), ("七", "qī"), ("西", "xī")],
    [("家", "jiā"), ("掐", "qiā"), ("虾", "xiā")],
    [("知", "zhī"), ("吃", "chī"), ("诗", "shī")],
    [("猪", "zhū"), ("出", "chū"), ("书", "shū")],
    [("字", "zì"), ("次", "cì"), ("四", "sì")],
    [("是", "shì"), ("四", "sì"), ("戏", "xì")],
    [("知", "zhī"), ("资", "zī"), ("鸡", "jī")],
    [("日", "rì"), ("力", "lì"), ("至", "zhì")],
]
# Groups that differ only in the final.
FINALS = [
    [("山", "shān"), ("伤", "shāng"), ("身", "shēn")],
    [("盆", "pén"), ("朋", "péng"), ("旁", "páng")],
    [("半", "bàn"), ("棒", "bàng"), ("笨", "bèn")],
    [("新", "xīn"), ("星", "xīng")],
    [("路", "lù"), ("绿", "lǜ")],
    [("女", "nǚ"), ("怒", "nù")],
    [("包", "bāo"), ("杯", "bēi"), ("班", "bān")],
    [("来", "lái"), ("雷", "léi")],
    [("买", "mǎi"), ("美", "měi")],
]

# Spelling: (character, the parts as a learner would build them, right
# spelling, wrong spellings, the rule it shows).
SPELLING = [
    ("举", "j + ü + 3", "jǔ", ["jǚ", "jiǔ"], "u_after_jqx"),
    ("去", "q + ü + 4", "qù", ["qǜ", "qiù"], "u_after_jqx"),
    ("学", "x + üe + 2", "xué", ["xüé", "xuó"], "u_after_jqx"),
    ("女", "n + ü + 3", "nǚ", ["nǔ", "niǔ"], "u_after_nl"),
    ("绿", "l + ü + 4", "lǜ", ["lù", "liù"], "u_after_nl"),
    ("一", "i + 1", "yī", ["ī", "iī"], "y_w"),
    ("五", "u + 3", "wǔ", ["ǔ", "yǔ"], "y_w"),
    ("雨", "ü + 3", "yǔ", ["ǚ", "wǔ"], "y_w"),
    ("我", "uo + 3", "wǒ", ["uǒ", "wuǒ"], "y_w"),
    ("好", "h + ao + 3", "hǎo", ["haǒ"], "mark_a"),
    ("北", "b + ei + 3", "běi", ["beǐ"], "mark_oe"),
    ("多", "d + uo + 1", "duō", ["dūo"], "mark_oe"),
    ("谢", "x + ie + 4", "xiè", ["xìe"], "mark_oe"),
    ("六", "l + iu + 4", "liù", ["lìu"], "mark_iu_ui"),
    ("贵", "g + ui + 4", "guì", ["gùi"], "mark_iu_ui"),
    ("水", "sh + ui + 3", "shuǐ", ["shǔi"], "mark_iu_ui"),
    ("九", "j + iu + 3", "jiǔ", ["jǐu", "jǔ"], "mark_iu_ui"),
]

TONE_NAMES = {
    1: L("Tone 1 · high and level", "1-й тон · высокий ровный", "Оҳанги 1 · баланд ва ҳамвор", "第一声 · 高而平"),
    2: L("Tone 2 · rising", "2-й тон · восходящий", "Оҳанги 2 · болоравӣ", "第二声 · 上升"),
    3: L("Tone 3 · low, dipping", "3-й тон · низкий, с провалом", "Оҳанги 3 · паст, хамида", "第三声 · 低，先降后升"),
    4: L("Tone 4 · falling", "4-й тон · нисходящий", "Оҳанги 4 · поёнравӣ", "第四声 · 下降"),
}

UNITS = [
    {"key": "py_syllable", "kind": "pinyin_part",
     "title": L("How a syllable is built", "Как устроен слог", "Ҳиҷо чӣ тавр сохта шудааст", "音节是怎么组成的"),
     "intro": L(
         "Pinyin writes Chinese sounds with Latin letters. Each character is one syllable, and a syllable has up to "
         "three parts: the initial (the consonant at the start), the final (the vowel part, sometimes ending in -n or "
         "-ng) and the tone (the pitch of the voice, marked over a vowel). Some syllables have no initial at all.",
         "Пиньинь записывает китайские звуки латинскими буквами. Каждый иероглиф — один слог, а в слоге до трёх "
         "частей: инициаль (согласный в начале), финаль (гласная часть, иногда с -n или -ng на конце) и тон (высота "
         "голоса, знак над гласной). У некоторых слогов инициали нет совсем.",
         "Пинйин овозҳои чиниро бо ҳарфҳои лотинӣ менависад. Ҳар иероглиф як ҳиҷо аст ва ҳиҷо то се қисм дорад: "
         "ибтидо (ҳамсадои аввал), охир (қисми садонок, баъзан бо -n ё -ng дар охир) ва оҳанг (баландии овоз, ки "
         "болои садонок нишон дода мешавад). Баъзе ҳиҷоҳо тамоман ибтидо надоранд.",
         "拼音用拉丁字母写汉语的读音。一个汉字就是一个音节，一个音节最多有三部分：声母（开头的辅音）、韵母（元音部分，"
         "有时以 -n 或 -ng 结尾）和声调（声音的高低，标在元音上）。有的音节没有声母。"),
     "points": [
         L("The initial comes first: m in mā, h in hǎo, sh in shū. zh, ch and sh are one initial each, written "
           "with two letters.",
           "Сначала идёт инициаль: m в mā, h в hǎo, sh в shū. zh, ch и sh — это одна инициаль, записанная двумя "
           "буквами.",
           "Аввал ибтидо меояд: m дар mā, h дар hǎo, sh дар shū. zh, ch ва sh ҳар кадом як ибтидо мебошанд, ки бо "
           "ду ҳарф навишта мешаванд.",
           "声母在前面：mā 的 m，hǎo 的 h，shū 的 sh。zh、ch、sh 各是一个声母，只是用两个字母写。"),
         L("The final is everything after it: a in mā, ao in hǎo, ang in máng. ài and ān have no initial — the "
           "syllable is only a final.",
           "Финаль — всё, что после неё: a в mā, ao в hǎo, ang в máng. В ài и ān инициали нет — слог состоит "
           "только из финали.",
           "Охир ҳамаи он чизест, ки баъд аз ибтидо меояд: a дар mā, ao дар hǎo, ang дар máng. Дар ài ва ān "
           "ибтидо нест — ҳиҷо танҳо аз охир иборат аст.",
           "后面的部分都是韵母：mā 的 a，hǎo 的 ao，máng 的 ang。ài 和 ān 没有声母，整个音节就是韵母。"),
         L("The tone is the mark over the vowel. The same letters with another tone are another word — the next "
           "unit is about tones.",
           "Тон — это знак над гласной. Те же буквы с другим тоном — другое слово; о тонах следующий урок.",
           "Оҳанг аломати болои садонок аст. Ҳамон ҳарфҳо бо оҳанги дигар калимаи дигаранд — дарси навбатӣ дар "
           "бораи оҳангҳост.",
           "声调是元音上面的符号。同样的字母换一个声调就是另一个词——下一课专门讲声调。"),
     ]},
    {"key": "py_tones", "kind": "pinyin_tone_mark",
     "title": L("The four tones", "Четыре тона", "Чор оҳанг", "四个声调"),
     "intro": L(
         "Every syllable is said on a tone, and the tone is part of the word: mā 妈 is mother, mǎ 马 is horse. "
         "The mark over the vowel tells you the tone; listen to each one and copy its shape with your voice.",
         "Каждый слог произносится с тоном, и тон — часть слова: mā 妈 — мама, mǎ 马 — лошадь. Знак над "
         "гласной показывает тон; послушайте каждый и повторите его рисунок голосом.",
         "Ҳар ҳиҷо бо оҳанг гуфта мешавад ва оҳанг қисми калима аст: mā 妈 — модар, mǎ 马 — асп. Аломати болои "
         "садонок оҳангро нишон медиҳад; ҳар якеро гӯш кунед ва шакли онро бо овозатон такрор кунед.",
         "每个音节都有声调，声调是词的一部分：mā 妈是妈妈，mǎ 马是马。元音上的符号告诉你声调；听一听，再用声音模仿它的样子。"),
     "points": [
         L("Tone 1 (ā): high and level — hold one high note.", "1-й тон (ā): высокий и ровный — держите одну "
           "высокую ноту.", "Оҳанги 1 (ā): баланд ва ҳамвор — як нотаи баландро нигоҳ доред.",
           "第一声（ā）：高而平，像唱一个高音。"),
         L("Tone 2 (á): rising — from the middle up, like asking “what?”.", "2-й тон (á): восходящий — от "
           "середины вверх, как в вопросе «что?».", "Оҳанги 2 (á): болоравӣ — аз миёна ба боло, мисли саволи "
           "«чӣ?».", "第二声（á）：从中间往上升，像问“啊？”。"),
         L("Tone 3 (ǎ): low — the voice dips down low; said alone it rises a little at the end.",
           "3-й тон (ǎ): низкий — голос опускается вниз; отдельно в конце немного поднимается.",
           "Оҳанги 3 (ǎ): паст — овоз поён меравад; вақте ки танҳо гуфта шавад, дар охир каме боло мешавад.",
           "第三声（ǎ）：低，声音先降下去；单独读的时候最后稍微升一点。"),
         L("Tone 4 (à): falling — sharply from high to low, like a firm “No!”.",
           "4-й тон (à): нисходящий — резко сверху вниз, как твёрдое «Нет!».",
           "Оҳанги 4 (à): поёнравӣ — якбора аз боло ба поён, мисли «Не!»-и қатъӣ.",
           "第四声（à）：从高到低，很快，像坚决地说“不！”。"),
         L("The light tone has no mark: short and weak, as ma in 吗 or the second ma in māma.",
           "Лёгкий тон знака не имеет: коротко и слабо, как ma в 吗 или второе ma в māma.",
           "Оҳанги сабук аломат надорад: кӯтоҳ ва суст, мисли ma дар 吗 ё ma-и дуюм дар māma.",
           "轻声没有符号：又短又轻，比如“吗”的 ma，或者 māma 的第二个 ma。"),
     ]},
    {"key": "py_initials1", "kind": "sound_pinyin",
     "title": L("Initials 1: b p m f · d t n l · g k h", "Инициали 1: b p m f · d t n l · g k h",
                "Ибтидоҳо 1: b p m f · d t n l · g k h", "声母一：b p m f · d t n l · g k h"),
     "intro": L(
         "Initials are learned in groups, by where the mouth makes them: the lips (b p m f), the tip of the tongue "
         "(d t n l) and the back of the tongue (g k h). The pairs b/p, d/t and g/k differ only in air.",
         "Инициали учат группами — по месту, где их образует рот: губы (b p m f), кончик языка (d t n l) и задняя "
         "часть языка (g k h). Пары b/p, d/t и g/k различаются только воздухом.",
         "Ибтидоҳоро гурӯҳ-гурӯҳ меомӯзанд — аз рӯи ҷое, ки даҳон онҳоро месозад: лабҳо (b p m f), нӯги забон "
         "(d t n l) ва қафои забон (g k h). Ҷуфтҳои b/p, d/t ва g/k танҳо бо нафас фарқ мекунанд.",
         "声母按发音部位分组学：双唇和唇齿（b p m f）、舌尖（d t n l）、舌根（g k h）。b/p、d/t、g/k 只差在送气。"),
     "points": [
         L("p, t, k come with a strong puff of air — hold your hand in front of your mouth and you feel it.",
           "p, t, k произносятся с сильным выдохом — поднесите ладонь ко рту, и вы его почувствуете.",
           "p, t, k бо нафаси қавӣ гуфта мешаванд — кафи дастатонро назди даҳон нигоҳ доред, онро ҳис мекунед.",
           "p、t、k 要送气：把手放在嘴前面，能感觉到一股气。"),
         L("b, d, g have no puff of air and no buzz of the voice: they sound closer to a soft p, t, k than to "
           "English b, d, g.",
           "b, d, g — без выдоха и без звона голоса: они ближе к русским п, т, к, чем к б, д, г.",
           "b, d, g бе нафас ва бе ларзиши овоз гуфта мешаванд: онҳо ба p, t, k-и нарм наздиктаранд.",
           "b、d、g 不送气，声带也不振动。"),
         L("n is said through the nose, l along the sides of the tongue: nán (男) and lán (蓝) are different words.",
           "n произносится через нос, l — по бокам языка: nán (男) и lán (蓝) — разные слова.",
           "n аз бинӣ, l аз паҳлӯҳои забон гуфта мешавад: nán (男) ва lán (蓝) калимаҳои гуногунанд.",
           "n 从鼻子出气，l 从舌头两边出气：nán（男）和 lán（蓝）是两个词。"),
         L("h is made at the back of the mouth, a little rough — like the ch in Scottish “loch”.",
           "h образуется в глубине рта, немного шершаво — как русское х.",
           "h дар қафои даҳон сохта мешавад, каме дағал — мисли х-и тоҷикӣ.",
           "h 在嘴的后部发音，有一点摩擦。"),
     ]},
    {"key": "py_initials2", "kind": "sound_pinyin",
     "title": L("Initials 2: j q x · zh ch sh r · z c s", "Инициали 2: j q x · zh ch sh r · z c s",
                "Ибтидоҳо 2: j q x · zh ch sh r · z c s", "声母二：j q x · zh ch sh r · z c s"),
     "intro": L(
         "Three groups that sound alike at first. They differ in where the tongue is; q, ch and c also carry the "
         "puff of air, like p, t, k.",
         "Три группы, которые сначала звучат похоже. Они различаются положением языка; q, ch и c, как p, t, k, "
         "произносятся с выдохом.",
         "Се гурӯҳе, ки дар аввал ба ҳам монанд садо медиҳанд. Онҳо бо ҷойи забон фарқ мекунанд; q, ch ва c низ "
         "мисли p, t, k бо нафас гуфта мешаванд.",
         "这三组一开始听起来很像，区别在舌头的位置；q、ch、c 也像 p、t、k 一样要送气。"),
     "points": [
         L("j q x: the tongue lies flat behind the lower teeth, the lips spread as in a smile. They are only ever "
           "followed by i or ü.",
           "j q x: язык лежит плоско за нижними зубами, губы растянуты, как в улыбке. После них бывают только i "
           "или ü.",
           "j q x: забон дар паси дандонҳои поён ҳамвор мехобад, лабҳо мисли табассум кашида мешаванд. Баъд аз "
           "онҳо танҳо i ё ü меояд.",
           "j q x：舌面放平，舌尖在下齿后面，嘴角像微笑。后面只跟 i 或 ü。"),
         L("zh ch sh r: the tip of the tongue curls up towards the roof of the mouth.",
           "zh ch sh r: кончик языка загибается вверх, к нёбу.",
           "zh ch sh r: нӯги забон ба боло, сӯи ком печида мешавад.",
           "zh ch sh r：舌尖往上卷，靠近上腭。"),
         L("z c s: the tip of the tongue touches the back of the upper teeth; c sounds like ts in “cats”.",
           "z c s: кончик языка у задней стороны верхних зубов; c звучит как русское ц.",
           "z c s: нӯги забон ба пушти дандонҳои боло мерасад; c мисли ц садо медиҳад.",
           "z c s：舌尖抵住上齿背；c 的音像 cats 里的 ts。"),
         L("After zh ch sh r and z c s, the letter i is not “ee”: it only stretches the buzz of the consonant "
           "(shì, sì). After j q x it is a real “ee” (xī).",
           "После zh ch sh r и z c s буква i — не «и»: она лишь продлевает звучание согласного (shì, sì). После "
           "j q x это настоящее «и» (xī).",
           "Баъд аз zh ch sh r ва z c s ҳарфи i «и» нест: он танҳо садои ҳамсадоро дароз мекунад (shì, sì). "
           "Баъд аз j q x ин «и»-и ҳақиқӣ аст (xī).",
           "zh ch sh r 和 z c s 后面的 i 不读“衣”，只是把声母的音拉长（shì、sì）；j q x 后面的 i 才是真正的“衣”（xī）。"),
     ]},
    {"key": "py_finals", "kind": "sound_pinyin",
     "title": L("Finals: vowels, -n and -ng", "Финали: гласные, -n и -ng", "Охирҳо: садонокҳо, -n ва -ng",
                "韵母：元音、-n 和 -ng"),
     "intro": L(
         "There are six simple vowels — a o e i u ü — and finals built from them: ai, ei, ao, ou, then ia, ie, ua, "
         "uo, üe, and the nasal finals ending in -n or -ng.",
         "Есть шесть простых гласных — a o e i u ü — и финали из них: ai, ei, ao, ou, затем ia, ie, ua, uo, üe и "
         "носовые финали на -n и -ng.",
         "Шаш садоноки сода ҳаст — a o e i u ü — ва охирҳое, ки аз онҳо сохта мешаванд: ai, ei, ao, ou, баъд ia, "
         "ie, ua, uo, üe ва охирҳои биниӣ бо -n ё -ng.",
         "有六个单韵母：a o e i u ü，由它们组成复韵母 ai、ei、ao、ou、ia、ie、ua、uo、üe，还有以 -n 或 -ng 结尾的鼻韵母。"),
     "points": [
         L("ü is i said with rounded lips: lǜ (绿 green) is not lù (路 road).",
           "ü — это i с округлёнными губами: lǜ (绿 зелёный) — не lù (路 дорога).",
           "ü — ин i бо лабони мудаввар аст: lǜ (绿 сабз) ба lù (路 роҳ) баробар нест.",
           "ü 是把嘴唇圆起来说 i：lǜ（绿）不是 lù（路）。"),
         L("-n ends at the front: the tongue touches behind the upper teeth (shān 山).",
           "-n заканчивается спереди: язык касается места за верхними зубами (shān 山).",
           "-n дар пеш тамом мешавад: забон ба паси дандонҳои боло мерасад (shān 山).",
           "-n 在前面结束：舌尖抵住上齿后面（shān 山）。"),
         L("-ng ends at the back, the mouth stays open, as in English “song” (shāng 伤).",
           "-ng заканчивается сзади, рот остаётся открытым, как в английском song (shāng 伤).",
           "-ng дар қафо тамом мешавад, даҳон кушода мемонад (shāng 伤).",
           "-ng 在后面结束，嘴巴张着，像英语 song 的结尾（shāng 伤）。"),
         L("ai is like “eye”, ei like “ay” in “say”, ao like “ow” in “how”, ou like “oh”.",
           "ai — как «ай», ei — как «эй», ao — как «ао» слитно, ou — как «оу».",
           "ai — мисли «ай», ei — мисли «эй», ao — мисли «ао»-и якҷоя, ou — мисли «оу».",
           "ai 像“哀”，ei 像“诶”，ao 像“熬”，ou 像“欧”。"),
     ]},
    {"key": "py_spelling", "kind": "pinyin_spell",
     "title": L("Spelling rules: y, w, ü and the tone mark", "Правила записи: y, w, ü и знак тона",
                "Қоидаҳои навишт: y, w, ü ва аломати оҳанг", "拼写规则：y、w、ü 和声调符号"),
     "intro": L(
         "A few rules decide how a syllable is written. Once you know them you can read any pinyin you meet.",
         "Несколько правил определяют, как пишется слог. Зная их, вы прочитаете любой пиньинь.",
         "Якчанд қоида муайян мекунад, ки ҳиҷо чӣ тавр навишта мешавад. Онҳоро донед — ҳар пинйинро хонда "
         "метавонед.",
         "几条规则决定一个音节怎么写。掌握了它们，遇到什么拼音都能读。"),
     "points": [
         L("With no initial, i, u and ü are written with y and w: yi, wu, yu; ia → ya, ie → ye, ua → wa, uo → wo.",
           "Без инициали i, u и ü пишутся через y и w: yi, wu, yu; ia → ya, ie → ye, ua → wa, uo → wo.",
           "Бе ибтидо i, u ва ü бо y ва w навишта мешаванд: yi, wu, yu; ia → ya, ie → ye, ua → wa, uo → wo.",
           "没有声母时，i、u、ü 写成 yi、wu、yu；ia → ya，ie → ye，ua → wa，uo → wo。"),
         L("After j, q, x and y, ü is written u without the dots: ju, qu, xue, yu. After n and l the dots stay: "
           "nǚ, lǜ.",
           "После j, q, x и y ü пишется как u без точек: ju, qu, xue, yu. После n и l точки остаются: nǚ, lǜ.",
           "Баъд аз j, q, x ва y ü бе нуқтаҳо, ҳамчун u навишта мешавад: ju, qu, xue, yu. Баъд аз n ва l нуқтаҳо "
           "мемонанд: nǚ, lǜ.",
           "j、q、x、y 后面的 ü 去掉两点写成 u：ju、qu、xue、yu。n、l 后面保留两点：nǚ、lǜ。"),
         L("The tone mark goes on a; with no a, on o or e; in iu and ui, on the second letter (liù, guì). On i, "
           "the mark replaces the dot (nǐ).",
           "Знак тона ставится над a; если a нет — над o или e; в iu и ui — над второй буквой (liù, guì). Над i "
           "знак заменяет точку (nǐ).",
           "Аломати оҳанг болои a гузошта мешавад; агар a набошад — болои o ё e; дар iu ва ui — болои ҳарфи дуюм "
           "(liù, guì). Болои i аломат ҷойи нуқтаро мегирад (nǐ).",
           "声调符号标在 a 上；没有 a 就标在 o 或 e 上；iu、ui 标在后一个字母上（liù、guì）。标在 i 上时去掉 i 的点（nǐ）。"),
     ]},
]
BY_KEY = {u["key"]: u for u in UNITS}


def _examples(key: str) -> list[dict]:
    """What the unit lets the learner hear before trying anything."""
    if key == "py_syllable":
        return [{"zh": z, "py": p, "initial": i, "final": f, "tone": tone_of(p)} for z, p, i, f in SYLLABLES[:6]]
    if key == "py_tones":
        return [{"zh": z, "py": p, "tone": tone_of(p)} for z, p in TONE_SETS[0]] + [{"zh": "吗", "py": "ma", "tone": 0}]
    if key == "py_initials1":
        return [{"zh": z, "py": p} for g in (INITIALS_1[0], INITIALS_1[3], INITIALS_1[7]) for z, p in g]
    if key == "py_initials2":
        return [{"zh": z, "py": p} for g in INITIALS_2[:3] for z, p in g] + [{"zh": z, "py": p} for z, p in INITIALS_2[4]]
    if key == "py_finals":
        return [{"zh": z, "py": p} for g in FINALS[:2] + FINALS[4:5] for z, p in g]
    return [{"zh": z, "py": right, "parts": parts} for z, parts, right, _, _ in SPELLING[::3]]


# --------------------------------------------------------------------------- questions

def _part_question(db: Session, zh: str, py: str, ini: str, fin: str, ask: str, rng: random.Random) -> dict:
    """Name one part of a written syllable (no sound first: this is reading)."""
    none = {"label": "—", "labels": L("no initial", "нет инициали", "ибтидо нест", "没有声母")}
    if ask == "final" and not ini and len(fin) == 1:
        ask = "initial"  # è is all final: the only thing to ask is that it has no initial
    if ask == "initial":
        right = {"label": ini} if ini else none
        # Near misses: the initial with the vowel glued on (ha), a two-letter
        # initial cut in half (s for sh), the final, the whole syllable.
        wrong = [ini + fin[0], ini[0] if len(ini) == 2 else None, fin] if ini else [fin[0] if len(fin) > 1 else None, plain(py)]
        options = [right] + [{"label": w} for w in dict.fromkeys(wrong) if w and w != right["label"]][:2]
    else:
        right = {"label": fin}
        wrong = [fin[1:] if len(fin) > 1 else None, ini + fin if ini else None, ini or None, fin[:-1] if len(fin) > 1 else None]
        options = [right] + [{"label": w} for w in dict.fromkeys(wrong) if w and w != fin][:2]
    for o in options:
        o["zh"] = zh
    q = _q(db, "pinyin_part", [_line(zh, py)], options, 0, zh, rng)
    q.update(silent=True, ask_text=py, part=ask, focus_id=None, parts={"initial": ini, "final": fin, "tone": tone_of(py)})
    return q


def _tone_mark_question(db: Session, zh: str, py: str, rng: random.Random) -> dict:
    """Read the mark: which tone is written on this syllable?"""
    right = tone_of(py)
    options = [{"label": str(n), "labels": TONE_NAMES[n], "zh": zh} for n in (1, 2, 3, 4)]
    q = _q(db, "pinyin_tone_mark", [_line(zh, py)], options, right - 1, zh, rng)
    q.update(silent=True, ask_text=py, focus_id=None)
    return q


def _heard_choice(db: Session, group: list[tuple[str, str]], rng: random.Random) -> dict:
    """Hear one syllable of the group, pick its spelling among the others."""
    seen, opts = set(), []
    for zh, py in group:
        if py not in seen:
            seen.add(py)
            opts.append({"label": py, "zh": zh})
    k = rng.randrange(len(opts))
    return _q(db, "sound_pinyin", [_line(opts[k]["zh"], opts[k]["label"])], opts, k, opts[k]["zh"], rng)


def _spell_question(db: Session, item: tuple, rng: random.Random) -> dict:
    zh, parts, right, wrong, rule = item
    options = [{"label": right, "zh": zh}] + [{"label": w, "zh": zh} for w in wrong]
    q = _q(db, "pinyin_spell", [_line(zh, right)], options, 0, zh, rng)
    q.update(silent=True, ask_text=parts, rule=rule, focus_id=None)
    return q


def build_questions(db: Session, user: models.User, key: str, rng: random.Random) -> list[dict]:
    unit = BY_KEY[key]
    qs: list[dict] = []
    if key == "py_syllable":
        for zh, py, ini, fin in rng.sample(SYLLABLES, ROUND):
            qs.append(_part_question(db, zh, py, ini, fin, rng.choice(("initial", "final")), rng))
    elif key == "py_tones":
        # Half read from the mark, half heard (the Sound World tone question).
        sets = rng.sample(TONE_SETS, ROUND)
        for i, group in enumerate(sets):
            k = rng.randrange(4)
            zh, py = group[k]
            if i % 2 == 0:
                qs.append(_tone_mark_question(db, zh, py, rng))
            else:
                qs.append(_q(db, "sound_tone", [_line(zh, py)], [{"label": p, "zh": z} for z, p in group], k, zh, rng))
        rng.shuffle(qs)
    elif key in ("py_initials1", "py_initials2", "py_finals"):
        data = {"py_initials1": INITIALS_1, "py_initials2": INITIALS_2, "py_finals": FINALS}[key]
        for group in rng.sample(data, min(ROUND, len(data))):
            qs.append(_heard_choice(db, group, rng))
    else:
        for item in rng.sample(SPELLING, ROUND):
            qs.append(_spell_question(db, item, rng))
    qs[0]["ctx"] = {"kind": "pronunciation", "lesson": key, "course": "pinyin", "titles": unit["title"],
                    "how": unit["intro"]}
    return qs


# --------------------------------------------------------------------------- why an answer is wrong

_ASPIRATED = [{"b", "p"}, {"d", "t"}, {"g", "k"}, {"j", "q"}, {"zh", "ch"}, {"z", "c"}]
_PLACE = [{"zh", "z", "j"}, {"ch", "c", "q"}, {"sh", "s", "x"}]


def _initial_tip(a: str, b: str) -> str:
    pair = {a, b}
    if pair in _ASPIRATED:
        return "air"
    if any(pair <= s for s in _PLACE):
        return "tongue"
    if pair == {"n", "l"}:
        return "nl"
    if pair == {"r", "l"} or pair == {"r", "zh"}:
        return "r"
    return "initial"


def _nasal(final: str) -> str:
    return "ng" if final.endswith("ng") else "n" if final.endswith("n") else ""


def _final_tip(a: str, b: str) -> str:
    if _nasal(a) and _nasal(b) and _nasal(a) != _nasal(b):
        return "nasal"
    if {a, b} == {"u", "ü"}:
        return "umlaut"
    return "final"


def explain(q: dict, choice_id: int | None) -> dict | None:
    """What a pinyin answer shows, for the learner: exactly what differs
    between the option picked and the right one. Structured (the page words
    it in the learner's language); None when there is nothing to compare."""
    qtype = q["type"]
    if qtype not in ("sound_tone", "sound_pinyin", "pinyin_part", "pinyin_tone_mark", "pinyin_spell"):
        return None
    right = q["options"][q["item_id"]]
    picked = q["options"][choice_id] if choice_id is not None and 0 <= choice_id < len(q["options"]) else None
    out = {"kind": "pinyin", "answer": right["label"], "picked": picked["label"] if picked else None,
           "correct": choice_id == q["item_id"]}
    if qtype == "pinyin_part":
        parts = q["parts"]
        return {**out, "why": "part", "syllable": q["ask_text"], "part": q["part"], **parts}
    if qtype == "pinyin_tone_mark":
        return {**out, "why": "mark", "syllable": q["ask_text"], "answer_tone": int(right["label"]),
                "picked_tone": int(picked["label"]) if picked else None}
    if qtype == "pinyin_spell":
        return {**out, "why": "rule", "rule": q["rule"], "parts": q["ask_text"]}
    if picked is None or out["correct"] or " " in right["label"] or " " in picked["label"]:
        return {**out, "why": "heard"}
    (pi, pf), (ri, rf) = split(picked["label"]), split(right["label"])
    pt, rt = tone_of(picked["label"]), tone_of(right["label"])
    if (pi, pf) == (ri, rf) and pt != rt:
        return {**out, "why": "tone", "picked_tone": pt, "answer_tone": rt}
    if pi != ri and pf == rf:
        return {**out, "why": "initial", "picked_part": pi or "—", "answer_part": ri or "—", "tip": _initial_tip(pi, ri)}
    if pf != rf and pi == ri:
        return {**out, "why": "final", "picked_part": pf, "answer_part": rf, "tip": _final_tip(pf, rf)}
    return {**out, "why": "heard"}


# --------------------------------------------------------------------------- the course page

def _guided(db: Session, key: str, locale: str) -> list[dict]:
    """Three questions to try on the page, with the answer and the
    explanation of every option -- fixed (the same for everyone), never
    graded or stored."""
    rng = random.Random(key)  # deterministic: a guided example, not a test
    if key == "py_syllable":
        qs = [_part_question(db, *SYLLABLES[1], "final", rng), _part_question(db, *SYLLABLES[3], "initial", rng),
              _part_question(db, *SYLLABLES[4], "initial", rng)]
    elif key == "py_tones":
        qs = [_tone_mark_question(db, *TONE_SETS[1][2], rng), _tone_mark_question(db, *TONE_SETS[3][1], rng),
              _q(db, "sound_tone", [_line(*TONE_SETS[0][3])], [{"label": p, "zh": z} for z, p in TONE_SETS[0]], 3,
                 TONE_SETS[0][3][0], rng)]
    elif key in ("py_initials1", "py_initials2", "py_finals"):
        data = {"py_initials1": INITIALS_1, "py_initials2": INITIALS_2, "py_finals": FINALS}[key]
        qs = [_heard_choice(db, g, rng) for g in data[:3]]
    else:
        qs = [_spell_question(db, SPELLING[i], rng) for i in (0, 5, 13)]
    out = []
    for q in qs:
        silent = q.get("silent")
        line = q["lines"][0]
        out.append({
            "type": q["type"], "ask": q.get("ask_text"), "part": q.get("part"), "zh": line["zh"], "py": line["py"],
            # Heard questions play the syllable; read ones show it and let it be heard after.
            "heard": not silent,
            "options": [{"id": i, "label": _label(o, locale)} for i, o in enumerate(q["options"])],
            "answer": q["item_id"],
            "why": [explain(q, i) for i in range(len(q["options"]))],  # by option id
        })
    return out


def _label(o: dict, locale: str) -> str:
    return _loc(o["labels"], locale) if o.get("labels") else o["label"]


def records(db: Session, user: models.User) -> dict[str, dict]:
    """This learner's completed check rounds per unit: how many, best score."""
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


def passed_all(db: Session, user: models.User) -> bool:
    recs = records(db, user)
    return all(recs.get(u["key"], {}).get("best", 0.0) >= PASS for u in UNITS)


def course(db: Session, user: models.User, locale: str) -> dict:
    """The course and the learner's real record in it. The next unit is the
    first one not yet passed; every unit stays open (a learner who knows
    some pinyin may jump ahead -- the checks say whether they really do)."""
    recs = records(db, user)
    units = []
    for i, u in enumerate(UNITS):
        r = recs.get(u["key"], {"played": 0, "best": 0.0})
        units.append({"key": u["key"], "n": i + 1, "kind": u["kind"], "title": _loc(u["title"], locale),
                      "intro": _loc(u["intro"], locale), "points": [_loc(p, locale) for p in u["points"]],
                      "examples": _examples(u["key"]), "guided": _guided(db, u["key"], locale),
                      "played": r["played"], "best": round(r["best"], 1), "passed": r["best"] >= PASS})
    nxt = next((x["key"] for x in units if not x["passed"]), None)
    return {"units": units, "next": nxt, "passed": sum(x["passed"] for x in units), "total": len(units),
            "pass_score": PASS, "tone_names": {n: _loc(v, locale) for n, v in TONE_NAMES.items()}}
