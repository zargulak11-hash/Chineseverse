"""English names of the HSK 3.0 grammar syllabus categories.

GrammarTopic.category holds the syllabus's own Chinese term (名词, 副词,
因果复句 ...). Russian and Tajik get it from content translations, and a
Chinese UI shows it as is -- but English is the base language, which has no
translation rows, so an English learner saw the raw Chinese term on every
grammar card while a Russian learner read "существительное". This is that
missing English column for the 75 terms the syllabus uses (the same
grammatical terms the RU/TG translations render).
"""

from __future__ import annotations

from app.services.localization import tr

CATEGORY_EN = {
    "名词": "Nouns", "动词": "Verbs", "形容词": "Adjectives", "代词": "Pronouns", "数词": "Numerals",
    "量词": "Measure words", "副词": "Adverbs", "连词": "Conjunctions", "助词": "Particles",
    "叹词": "Interjections", "拟声词": "Onomatopoeia", "前缀": "Prefixes", "后缀": "Suffixes",
    "类前缀": "Quasi-prefixes", "类后缀": "Quasi-suffixes",
    "程度副词": "Adverbs of degree", "范围、协同副词": "Adverbs of scope", "时间副词": "Adverbs of time",
    "频率、重复副词": "Adverbs of frequency", "关联副词": "Linking adverbs", "否定副词": "Negative adverbs",
    "方式副词": "Adverbs of manner", "情态副词": "Adverbs of attitude", "语气副词": "Modal adverbs",
    "结构助词": "Structural particles", "语气助词": "Modal particles",
    "引出时间、处所": "Introducing time or place", "引出时间": "Introducing time",
    "引出方向、路径": "Introducing direction or route", "引出对象": "Introducing the target",
    "引出目的、原因": "Introducing purpose or cause", "引出施事、受事": "Introducing the doer or receiver",
    "引出凭借、依据": "Introducing a basis or means", "表示排除": "Expressing exclusion",
    "主语": "Subject", "谓语": "Predicate", "宾语": "Object", "定语": "Attributive", "状语": "Adverbial",
    "补语": "Complements", "结构类型": "Phrase structures", "功能类型": "Phrase functions",
    "单句": "Simple sentences", "句类": "Sentence types", "句型": "Sentence patterns",
    "特殊句型": "Special sentence patterns", "特殊句式": "Special sentence structures", "句群": "Sentence groups",
    "复句": "Complex sentences", "多重复句": "Multi-clause sentences", "紧缩复句": "Contracted complex sentences",
    "并列复句": "Coordinate clauses", "承接复句": "Sequential clauses", "递进复句": "Progressive clauses",
    "选择复句": "Alternative clauses", "转折复句": "Contrast clauses", "假设复句": "Hypothetical clauses",
    "条件复句": "Conditional clauses", "因果复句": "Cause and effect", "目的复句": "Purpose clauses",
    "让步复句": "Concessive clauses", "解说复句": "Explanatory clauses",
    "动作的态": "Aspect", "数的表示法": "Expressing numbers", "时间表示法": "Expressing time",
    "提问的方法": "Asking questions", "强调的方法": "Emphasis", "特殊表达法": "Special expressions",
    "口语格式": "Spoken patterns", "固定格式": "Fixed patterns", "四字格": "Four-character expressions",
    "按形式分类": "Classified by form", "按意义分类": "Classified by meaning", "其他": "Other",
}


def category_label(category: str | None, translations: dict, topic_id: int, locale: str) -> str | None:
    """The category in the learner's language: a translation row for
    RU/TG, the Chinese term itself for ZH, CATEGORY_EN for English."""
    if not category:
        return category
    if locale == "en":
        return CATEGORY_EN.get(category, category)
    return tr(translations, topic_id, "category", category)
