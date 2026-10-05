"""The per-learner AI budget (services/ai_budget.py): model calls made while
grading spend from it; past it the same request is graded offline -- never
refused -- and the assistant keeps its own, separate limit."""

import pytest

from app.services import ai_budget, ai_client
from helpers import expect, register, unique_name

RIGHT_VERDICT = "顾客是对的，老板错了，他收了二十五元"


class Clock:
    def __init__(self):
        self.t = 5_000.0

    def __call__(self):
        return self.t


@pytest.fixture
def clock(monkeypatch):
    c = Clock()
    monkeypatch.setattr(ai_budget, "_now", c)
    ai_budget.reset()
    yield c
    ai_budget.reset()


@pytest.fixture
def model(monkeypatch):
    """A configured model that records every call it receives."""
    calls = []

    def chat(messages, max_tokens=200, temperature=0.8, json_mode=False):
        calls.append(messages)
        return '{"solved": true, "feedback": "model says yes"}' if json_mode else "model reply"

    monkeypatch.setattr(ai_client.settings, "ai_provider", "gemini")
    monkeypatch.setattr(ai_client.settings, "gemini_api_key", "test-key")
    monkeypatch.setattr(ai_client, "_gemini_chat", chat)
    return calls


def test_the_budget_allows_its_calls_per_hour_then_refuses_until_they_age_out(clock, monkeypatch):
    monkeypatch.setattr(ai_budget, "CALLS_PER_HOUR", 3)
    assert [ai_budget.spend(1) for _ in range(4)] == [True, True, True, False]
    assert ai_budget.spend(2), "each learner has their own budget"
    clock.t += 3599
    assert not ai_budget.spend(1)
    clock.t += 1
    assert ai_budget.spend(1)


def test_offline_unless_forces_the_offline_path_only_inside_the_block(monkeypatch):
    monkeypatch.setattr(ai_client.settings, "ai_provider", "gemini")
    monkeypatch.setattr(ai_client.settings, "gemini_api_key", "test-key")
    assert ai_client._active_provider() == "gemini"
    with ai_client.offline_unless(True):
        assert ai_client._active_provider() == "gemini"
    with pytest.raises(RuntimeError):
        with ai_client.offline_unless(False):
            assert ai_client._active_provider() == "offline"
            raise RuntimeError("the block failed")
    assert ai_client._active_provider() == "gemini", "the switch is restored even after an error"


def test_over_budget_a_case_verdict_is_graded_offline_not_refused(client, clock, model, monkeypatch):
    monkeypatch.setattr(ai_budget, "CALLS_PER_HOUR", 2)
    _, h = register(client, unique_name("budget"))
    for _ in range(2):
        r = expect(client, "post", "/api/world/scenarios/the-missing-bill/solve", 200, headers=h,
                   json={"conclusion": "不知道"})
        assert r["feedback"] == "model says yes"
    assert len(model) == 2
    # Budget spent: still answered (by the offline keyword grader), no model call.
    r = expect(client, "post", "/api/world/scenarios/the-missing-bill/solve", 200, headers=h,
               json={"conclusion": RIGHT_VERDICT})
    assert r["solved"] is True and r["feedback"] != "model says yes"
    assert len(model) == 2
    # Another learner still has their own budget.
    _, other = register(client, unique_name("budget_other"))
    expect(client, "post", "/api/world/scenarios/the-missing-bill/solve", 200, headers=other,
           json={"conclusion": "不知道"})
    assert len(model) == 3


def test_the_assistant_keeps_its_own_separate_limit(client, clock, model, monkeypatch):
    monkeypatch.setattr(ai_budget, "CALLS_PER_HOUR", 0)  # grading budget exhausted
    uid, h = register(client, unique_name("budget_chat"))
    assert not ai_budget.spend(uid)
    body = expect(client, "post", "/api/assistant/chat", 200, headers=h,
                  json={"messages": [{"role": "user", "content": "你好"}]})
    assert body["source"] == "ai" and body["reply"] == "model reply"
