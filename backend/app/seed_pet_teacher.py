"""Pet Teacher Mode content bank.

Each case is a real, well-known mistake learners make with a specific
grammar point already in the curriculum (see GRAMMAR in seed_learning.py).
The animal "makes" the wrong_sentence mistake; the learner must supply the
correct_sentence and an explanation touching on one of explanation_keywords.

Format: (hsk_level, grammar_topic_title_or_None, wrong_sentence,
         correct_sentence, mistake_summary, explanation_keywords, hint, order_index)
"""

PET_TEACHER_CASES = [
    (1, "是 — to be", "我是很高兴。", "我很高兴。",
     "是 is not needed before an adjective — the adjective itself acts as the verb.",
     ["adjective", "形容词", "不需要是", "no 是 before adjective", "adjective is the verb"],
     "Adjectives in Chinese don't need a linking verb like English 'to be'.", 1),
    (1, "吗 — yes/no question", "你叫什么吗？", "你叫什么？",
     "吗 can't be combined with a question word like 什么 — pick one, not both.",
     ["question word", "疑问词", "不能同时", "吗和什么", "either or not both"],
     "什么 already makes it a question — 吗 would ask a question twice.", 2),
    (1, "不 — negation", "我不有钱。", "我没有钱。",
     "有 is negated with 没(有), never with 不.",
     ["没有", "not 不", "negate you", "have negation", "没 not 不"],
     "不 negates most verbs, but 有 is the one exception.", 3),
    (1, "的 — possession", "书我的在这里。", "我的书在这里。",
     "的 links a possessor and the noun as one unit — 我的书 — it can't be split apart.",
     ["word order", "语序", "我的书", "possessor before noun", "keep together"],
     "Read it as one chunk: [我的书] 在这里, not scattered across the sentence.", 4),
    (1, "个 — measure word", "我有三苹果。", "我有三个苹果。",
     "A number needs a measure word (个) before the noun — you can't put a number directly on a noun.",
     ["measure word", "量词", "个", "number plus noun", "need a measure word"],
     "三 + 个 + 苹果, not 三 + 苹果.", 5),
    (1, "有 — to have / there is", "我有忙。", "我很忙。",
     "有 means 'to have / there is' for nouns, not for adjectives like busy — use 很 + adjective instead.",
     ["有 is for nouns", "adjective doesn't need 有", "很忙", "not have busy", "很 plus adjective"],
     "Busy (忙) is an adjective, so it takes 很, not 有.", 6),
    (2, "了 — completed action", "我每天吃了早饭。", "我每天吃早饭。",
     "了 marks one completed, specific action — it doesn't belong with a habitual word like 每天 (every day).",
     ["habitual", "每天", "completed action", "not with every day", "habit no 了"],
     "每天 describes a routine, not a single finished event.", 7),
    (2, "都 — all", "他们是都学生。", "他们都是学生。",
     "都 (all/both) goes before the verb, not after it.",
     ["word order", "都在动词前", "before verb", "都是", "都 before verb"],
     "都 + 是, never 是 + 都.", 8),
    (2, "因为……所以…… — because/therefore", "所以下雨，因为我不去。", "因为下雨，所以我不去。",
     "因为 (the cause) comes first, 所以 (the result) comes second — the order can't be reversed.",
     ["因为在前", "所以在后", "cause then result", "order", "reason first"],
     "Cause before effect: 因为 A，所以 B.", 9),
]
