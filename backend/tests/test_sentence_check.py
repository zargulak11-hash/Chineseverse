"""Sentence grading is correct for correct Chinese -- the Pet Teacher bug.

The learner fixed the companion's 我是很高兴。 to 我很高兴。 and was told to
try again, with "Correct sentence: 我很高兴。" -- their own sentence -- shown
as the answer. Covers:
  * adjective-predicate sentences (我很高兴。 我很累。 她很漂亮。 天气很好。
    他很忙。) are never flagged, and nothing demands 是 before an adjective;
  * sentences where 是 IS needed (我学生。 我很学生。) are flagged;
  * the other known-error rules fire on the error and not on correct
    look-alikes (embedded questions, 有点儿, 星期一, ...);
  * punctuation, spacing and a swapped degree adverb never make a correction
    wrong; one-character slips are "close", not "incorrect";
  * Pet Teacher: a right correction is reported as right even when the
    explanation is thin (outcome fixed_needs_explanation, no "correct
    sentence" shown back), a restated sentence is not an explanation, a
    model can't overturn a correction the rules accepted, and the model is
    told the reply language and the whole case.
"""

import pytest

from app import models
from app.database import SessionLocal
from app.services import ai_client, books
from app.services import grammar_lesson as gl
from app.services import sentence_check as sc
from helpers import expect, register, unique_name


def codes(text):
    return [i["code"] for i in sc.detect(text)]


CORRECT = [
    "我很高兴。", "我很累。", "她很漂亮。", "天气很好。", "他很忙。", "我非常高兴。", "这个菜很好吃。",
    "我是学生。", "他是我的老师。", "她是美国人。", "他是很好的老师。", "我也是很高兴。", "你是不是很累？",
    "你知道他是谁吗？", "你有什么问题吗？", "星期一书店开门吗？", "他现在每天都跑步了。", "我每天吃早饭。",
    "他中国人。", "我朋友，他很好。", "我有一个苹果。", "他没有忙。", "我有点儿忙。", "这本书很有意思。",
    "他们都是学生。", "今天太冷了。", "我没有钱。", "你叫什么？",
]
WRONG = {
    "我是很高兴。": "shi_adj", "我是累。": "shi_adj", "她是很漂亮。": "shi_adj", "天气是很好。": "shi_adj",
    "我有忙。": "you_adj", "我很学生。": "hen_noun", "我学生。": "missing_shi", "他老师。": "missing_shi",
    "我不有钱。": "bu_you", "我有三苹果。": "missing_measure", "他们是都学生。": "dou_order",
    "你叫什么吗？": "ma_question_word", "我每天吃了早饭。": "le_habitual",
}
EXPECTED, SCANNED = "我很高兴。", "我是很高兴。"


@pytest.mark.parametrize("sentence", CORRECT)
def test_correct_chinese_is_never_flagged(sentence):
    assert codes(sentence) == [], (sentence, codes(sentence))


@pytest.mark.parametrize("sentence, code", list(WRONG.items()))
def test_a_real_learner_error_is_caught_by_the_right_rule(sentence, code):
    assert code in codes(sentence), (sentence, codes(sentence))


@pytest.mark.parametrize("sentence", ["我很高兴。", "我很累。", "她很漂亮。", "天气很好。", "他很忙。"])
def test_without_an_expected_answer_a_clean_sentence_stays_unchecked(sentence):
    # Never assumed wrong, never assumed right; nothing says an adjective needs 是.
    r = sc.check(sentence)
    assert r["verdict"] == "unchecked" and r["issues"] == [], (sentence, r)


@pytest.mark.parametrize("answer, verdict, category", [
    ("我很高兴。", "correct", "exact"), ("我很高兴", "correct", "punctuation"),
    ("我很高兴.", "correct", "punctuation"), ("我很高兴！", "correct", "punctuation"),
    ("我 很 高兴 。", "correct", "exact"), ("我很高兴。 ", "correct", "exact"),
    ("我非常高兴。", "correct", "alternative"), ("我真高兴！", "correct", "alternative"),
    ("我是很高兴。", "incorrect", "unchanged"), ("我是很高兴", "incorrect", "unchanged"),
    ("我是非常高兴。", "incorrect", "grammar"), ("我很高心。", "close", "typo"),
    ("", "incorrect", "different"), ("hello", "incorrect", "different"),
])
def test_checking_a_correction_against_the_expected_sentence(answer, verdict, category):
    r = sc.check(answer, EXPECTED, wrong=SCANNED)
    assert (r["verdict"], r["category"]) == (verdict, category), (answer, r)


def test_an_unknown_alternative_is_left_open_for_a_model_to_judge():
    r = sc.check("我很开心。", EXPECTED, wrong=SCANNED)
    assert r["verdict"] == "incorrect" and r["final"] is False, r


def test_no_error_rule_fires_on_any_syllabus_or_story_sentence(client):
    """Every syllabus example and every story sentence is correct Chinese, so
    no ERROR-level rule may fire on any of them -- this is how the borrowed
    measure words (一碗汤, 一桌子书), the concessive 好看是好看 and 有老有少
    were found and excluded."""
    sents = []
    with SessionLocal() as db:
        for t in db.query(models.GrammarTopic).all():
            for b in gl.example_blocks(t):
                sents += [b["zh"]] if b["kind"] == "sentence" else b.get("items", [])
    for bk in books.all_books():
        sents += [s["zh"] for ch in bk["chapters"] for s in ch["sentences"]]
    bad = [(s, i["code"]) for s in sents for i in sc.detect(s) if i["severity"] == "error"]
    assert len(sents) > 2000 and not bad, bad[:10]


@pytest.fixture(scope="module")
def case_url(client):
    with SessionLocal() as db:
        case = db.query(models.PetTeacherCase).filter_by(wrong_sentence=SCANNED).one()
        return f"/api/pet-teacher/lesson/{case.id}/answer"


@pytest.fixture
def teacher(client):
    return register(client, unique_name("pt_learner"))


@pytest.fixture
def model(monkeypatch):
    def install(reply):
        seen = []

        def chat(messages, **kw):
            seen.append(messages)
            return reply

        monkeypatch.setattr(ai_client, "_active_provider", lambda: "gemini")
        monkeypatch.setattr(ai_client, "_gemini_chat", chat)
        return seen
    return install


def test_the_case_links_to_the_adjective_predicate_topic_not_shi(client):
    with SessionLocal() as db:
        case = db.query(models.PetTeacherCase).filter_by(wrong_sentence=SCANNED).one()
        topic = db.get(models.GrammarTopic, case.grammar_topic_id)
        assert topic is not None and "形容词谓语句" in topic.title, topic and topic.title


def test_the_exact_bug_a_right_correction_with_a_restated_explanation(client, teacher, case_url):
    _, h = teacher
    assert expect(client, "get", "/api/pet-teacher/lesson", 200, headers=h)["taught_count"] == 0
    r = expect(client, "post", case_url, 200, headers={**h, "X-Locale": "ru"},
               json={"correction": EXPECTED, "explanation": "我很高兴"})
    assert r["correct_fix"] is True and r["correction_verdict"] == "correct", r
    assert r["outcome"] == "fixed_needs_explanation" and r["restated"] is True, r
    assert r["show_correct_sentence"] is False and r["issues"] == [], r


@pytest.mark.parametrize("variant", ["我很高兴", "我很高兴.", "我非常高兴。", " 我很高兴！"])
def test_punctuation_and_degree_adverb_variants_are_right_corrections(client, teacher, case_url, variant):
    _, h = teacher
    r = expect(client, "post", case_url, 200, headers=h, json={"correction": variant, "explanation": "x"})
    assert r["correct_fix"] is True, (variant, r)


def test_a_real_explanation_succeeds_in_english_or_russian_and_is_taught_once(client, teacher, case_url):
    uid, h = teacher
    r = expect(client, "post", case_url, 200, headers=h,
               json={"correction": EXPECTED, "explanation": "adjective is the verb, no 是 before adjective"})
    assert r["success"] is True and r["outcome"] == "success", r
    # offline, an explanation written in Russian is understood too
    r = expect(client, "post", case_url, 200, headers={**h, "X-Locale": "ru"},
               json={"correction": EXPECTED, "explanation": "是 не нужен, потому что прилагательное само сказуемое"})
    assert r["success"] is True, r
    with SessionLocal() as db:
        case_id = int(case_url.split("/")[-2])
        assert db.query(models.UserTaughtFact).filter_by(user_id=uid, case_id=case_id).count() == 1


def test_an_unchanged_or_still_wrong_correction_names_the_issue(client, teacher, case_url):
    _, h = teacher
    r = expect(client, "post", case_url, 200, headers=h, json={"correction": SCANNED, "explanation": "x"})
    assert r["correct_fix"] is False and r["correction_category"] == "unchanged" and r["show_correct_sentence"], r
    assert "shi_adj" in r["issues"] and r["grammar_topic_id"], r
    r = expect(client, "post", case_url, 200, headers=h, json={"correction": "我高心。", "explanation": "x"})
    assert r["outcome"] in ("close", "incorrect"), r


def test_a_model_cannot_overturn_the_rules_and_sees_the_whole_case(client, teacher, case_url, model):
    # Even if it said the explanation failed AND claimed the sentence was
    # bad, the fix stays correct; the prompt carries the case and the language.
    _, h = teacher
    seen = model('{"understood": false, "feedback": "Нужно объяснить, почему 是 лишнее."}')
    r = expect(client, "post", case_url, 200, headers={**h, "X-Locale": "ru"},
               json={"correction": EXPECTED, "explanation": "просто так"})
    assert r["correct_fix"] is True and r["outcome"] == "fixed_needs_explanation", r
    assert r["feedback"].startswith("Нужно"), r
    system, user = seen[-1][0]["content"], seen[-1][1]["content"]
    assert "Russian" in system and "correction is RIGHT" in system and "need no 是" in system, system
    assert SCANNED in user and f"Learner's correction: {EXPECTED}" in user, user


def test_a_correct_alternative_judged_by_the_model_counts(client, teacher, case_url, model):
    # Offline it would be left 'different' (never silently right or wrong by guess).
    _, h = teacher
    model('{"category": "alternative", "feedback": "Тоже верно."}')
    r = expect(client, "post", case_url, 200, headers={**h, "X-Locale": "ru"},
               json={"correction": "我很开心。", "explanation": "x"})
    assert r["correct_fix"] is True and r["correction_verdict"] == "acceptable", r


def test_the_permanent_companion_reacts_to_each_real_outcome_never_shaming(client, case_url):
    _, h = register(client, unique_name("pt_reactions"))
    with SessionLocal() as db:
        bird_id = db.query(models.Animal).filter_by(slug="bird").one().id
    expect(client, "post", "/api/me/animal", 200, headers=h, json={"animal_id": bird_id})
    seq = [
        ({"correction": SCANNED, "explanation": "x"}, "teach_retry"),
        ({"correction": "我很高心。", "explanation": "x"}, "teach_close"),
        ({"correction": EXPECTED, "explanation": "我很高兴"}, "teach_why"),
        ({"correction": EXPECTED, "explanation": "adjective is the verb, no 是"}, "taught"),
        ({"correction": EXPECTED, "explanation": "adjective is the verb, no 是"}, "taught_again"),
    ]
    for body, cause in seq:
        r = expect(client, "post", case_url, 200, headers=h, json=body)["reaction"]
        assert r["cause"] == cause and r["event"] == "pet_teach", (cause, r)
        assert r["mood"] in ("celebrating", "happy", "encouraging"), r
        assert r["companion"]["slug"] == "bird", r["companion"]
