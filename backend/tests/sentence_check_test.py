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

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/sentence_check.db"
os.environ["AI_PROVIDER"] = "offline"

from fastapi.testclient import TestClient  # noqa: E402

from app import models  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.services import ai_client  # noqa: E402
from app.services import sentence_check as sc  # noqa: E402


def expect(client, method, url, expected, **kwargs):
    resp = getattr(client, method)(url, **kwargs)
    assert resp.status_code == expected, f"{method.upper()} {url} -> {resp.status_code} (expected {expected}): {resp.text}"
    return resp.json() if resp.content else None


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


def test_rules():
    for s in CORRECT:
        assert codes(s) == [], (s, codes(s))
    print(f"[PASS] {len(CORRECT)} correct sentences (adjective predicates, 是 + noun, embedded questions, ...) are not flagged")
    for s, code in WRONG.items():
        assert code in codes(s), (s, codes(s))
    print(f"[PASS] {len(WRONG)} real learner errors are each caught by the right rule (incl. 是 missing before a noun)")
    # Nothing anywhere says an adjective needs 是.
    for s in ("我很高兴。", "我很累。", "她很漂亮。", "天气很好。", "他很忙。"):
        r = sc.check(s)
        assert r["verdict"] == "unchecked" and r["issues"] == [], (s, r)
    print("[PASS] with no expected answer, a clean sentence stays 'unchecked' -- never assumed wrong, never assumed right")


def test_check():
    exp, wrong = "我很高兴。", "我是很高兴。"
    for a, verdict, category in [
        ("我很高兴。", "correct", "exact"), ("我很高兴", "correct", "punctuation"),
        ("我很高兴.", "correct", "punctuation"), ("我很高兴！", "correct", "punctuation"),
        ("我 很 高兴 。", "correct", "exact"), ("我很高兴。 ", "correct", "exact"),
        ("我非常高兴。", "correct", "alternative"), ("我真高兴！", "correct", "alternative"),
        ("我是很高兴。", "incorrect", "unchanged"), ("我是很高兴", "incorrect", "unchanged"),
        ("我是非常高兴。", "incorrect", "grammar"), ("我很高心。", "close", "typo"),
        ("", "incorrect", "different"), ("hello", "incorrect", "different"),
    ]:
        r = sc.check(a, exp, wrong=wrong)
        assert (r["verdict"], r["category"]) == (verdict, category), (a, r)
    r = sc.check("我很开心。", exp, wrong=wrong)
    assert r["verdict"] == "incorrect" and r["final"] is False, r  # left open for a model to judge
    print("[PASS] punctuation/spacing/degree-adverb variants are correct; unchanged and still-wrong ones are not; a slip is 'close'")


def test_corpus():
    """Every syllabus example and every story sentence is correct Chinese, so
    no ERROR-level rule may fire on any of them -- this is how the borrowed
    measure words (一碗汤, 一桌子书), the concessive 好看是好看 and 有老有少
    were found and excluded."""
    from app.services import books
    from app.services import grammar_lesson as gl

    sents = []
    with SessionLocal() as db:
        for t in db.query(models.GrammarTopic).all():
            for b in gl.example_blocks(t):
                sents += [b["zh"]] if b["kind"] == "sentence" else b.get("items", [])
    for bk in books.all_books():
        sents += [s["zh"] for ch in bk["chapters"] for s in ch["sentences"]]
    bad = [(s, i["code"]) for s in sents for i in sc.detect(s) if i["severity"] == "error"]
    assert len(sents) > 2000 and not bad, bad[:10]
    print(f"[PASS] no error-level rule fires on any of {len(sents)} syllabus and story sentences")


def register(client, name):
    data = expect(client, "post", "/api/auth/register", 201,
                  json={"username": name, "email": f"{name}@example.com", "password": "secret1"})
    return data["user"]["id"], {"Authorization": f"Bearer {data['access_token']}"}


def test_pet_teacher(client):
    uid, h = register(client, "pt_learner")
    with SessionLocal() as db:
        case = db.query(models.PetTeacherCase).filter_by(wrong_sentence="我是很高兴。").one()
        cid = case.id
        topic = db.get(models.GrammarTopic, case.grammar_topic_id)
        assert topic is not None and "形容词谓语句" in topic.title, topic and topic.title
    print("[PASS] the 我是很高兴。 case links to the adjective-predicate grammar topic (形容词谓语句), not 是")

    lesson = expect(client, "get", "/api/pet-teacher/lesson", 200, headers=h)
    assert lesson["taught_count"] == 0

    url = f"/api/pet-teacher/lesson/{cid}/answer"
    # The exact bug: the right correction with only the sentence as "explanation".
    r = expect(client, "post", url, 200, headers={**h, "X-Locale": "ru"},
               json={"correction": "我很高兴。", "explanation": "我很高兴"})
    assert r["correct_fix"] is True and r["correction_verdict"] == "correct", r
    assert r["outcome"] == "fixed_needs_explanation" and r["restated"] is True, r
    assert r["show_correct_sentence"] is False and r["issues"] == [], r
    print("[PASS] 我很高兴。 is accepted as CORRECT; a repeated sentence asks for the 'why' instead of failing the fix")

    for variant in ("我很高兴", "我很高兴.", "我非常高兴。", " 我很高兴！"):
        r = expect(client, "post", url, 200, headers=h, json={"correction": variant, "explanation": "x"})
        assert r["correct_fix"] is True, (variant, r)
    print("[PASS] the correction without 。, with '.', with 非常 or with ！ is accepted")

    r = expect(client, "post", url, 200, headers=h,
               json={"correction": "我很高兴。", "explanation": "adjective is the verb, no 是 before adjective"})
    assert r["success"] is True and r["outcome"] == "success", r
    print("[PASS] right correction + a real explanation succeeds")

    r = expect(client, "post", url, 200, headers={**h, "X-Locale": "ru"},
               json={"correction": "我很高兴。", "explanation": "是 не нужен, потому что прилагательное само сказуемое"})
    assert r["success"] is True, r
    print("[PASS] offline, an explanation written in Russian is understood too")

    r = expect(client, "post", url, 200, headers=h, json={"correction": "我是很高兴。", "explanation": "x"})
    assert r["correct_fix"] is False and r["correction_category"] == "unchanged" and r["show_correct_sentence"], r
    assert "shi_adj" in r["issues"] and r["grammar_topic_id"], r
    r = expect(client, "post", url, 200, headers=h, json={"correction": "我高心。", "explanation": "x"})
    assert r["outcome"] in ("close", "incorrect"), r
    print("[PASS] an unchanged / still-wrong correction is incorrect, names the issue and links the grammar page")

    # A model must not overturn the rules: even if it said the explanation
    # failed AND claimed the sentence was bad, the fix stays correct, and the
    # prompt it got carried the whole case and the reply language.
    seen = []

    def fake_chat(messages, **kw):
        seen.append(messages)
        return '{"understood": false, "feedback": "Нужно объяснить, почему 是 лишнее."}'

    orig = (ai_client._active_provider, ai_client._gemini_chat)
    ai_client._active_provider, ai_client._gemini_chat = (lambda: "gemini"), fake_chat
    try:
        r = expect(client, "post", url, 200, headers={**h, "X-Locale": "ru"},
                   json={"correction": "我很高兴。", "explanation": "просто так"})
    finally:
        ai_client._active_provider, ai_client._gemini_chat = orig
    assert r["correct_fix"] is True and r["outcome"] == "fixed_needs_explanation", r
    assert r["feedback"].startswith("Нужно"), r
    system, user = seen[-1][0]["content"], seen[-1][1]["content"]
    assert "Russian" in system and "correction is RIGHT" in system and "need no 是" in system, system
    assert "我是很高兴。" in user and "Learner's correction: 我很高兴。" in user, user
    print("[PASS] the model sees the whole case, is told the correction is right and to answer in the UI language")

    # A free-form alternative: the model may accept it; offline it is left
    # 'different' (never silently right or wrong by guess).
    def judge(messages, **kw):
        return '{"category": "alternative", "feedback": "Тоже верно."}'

    ai_client._active_provider, ai_client._gemini_chat = (lambda: "gemini"), judge
    try:
        r = expect(client, "post", url, 200, headers={**h, "X-Locale": "ru"},
                   json={"correction": "我很开心。", "explanation": "x"})
    finally:
        ai_client._active_provider, ai_client._gemini_chat = orig
    assert r["correct_fix"] is True and r["correction_verdict"] == "acceptable", r
    print("[PASS] a correct alternative (我很开心。) judged by the model counts as a right correction")

    with SessionLocal() as db:
        assert db.query(models.UserTaughtFact).filter_by(user_id=uid, case_id=cid).count() == 1
    print("[PASS] the case is recorded as taught exactly once")


def main():
    test_rules()
    test_check()
    with TestClient(app) as client:
        test_corpus()
        test_pet_teacher(client)
    print("ALL SENTENCE CHECK TESTS PASSED")


if __name__ == "__main__":
    main()
