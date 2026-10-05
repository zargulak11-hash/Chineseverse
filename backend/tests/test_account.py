"""The signed-in learner's own account (routers/me.py) and the social graph
around it (routers/social.py): what a learner may change about themselves,
what they may never change, and what others can see of them."""

import pytest

from app import models
from app.database import SessionLocal
from helpers import bearer, expect, register, register_raw, unique_name


@pytest.fixture
def learner(client):
    name = unique_name("acct")
    uid, h = register(client, name)
    return uid, h, name


def test_me_returns_the_account_profile_and_streak_without_secrets(client, learner):
    uid, h, name = learner
    expect(client, "get", "/api/me", 401)
    me = expect(client, "get", "/api/me", 200, headers=h)
    assert me["user"]["id"] == uid and me["user"]["username"] == name and me["user"]["is_admin"] is False
    assert {"profile", "streak"} <= set(me)
    assert not {"password", "password_hash"} & set(me["user"])


def test_profile_fields_are_saved_and_validated(client, learner):
    _, h, _ = learner
    p = expect(client, "patch", "/api/me/profile", 200, headers=h,
               json={"daily_goal_minutes": 30, "goal_text": "HSK 3 by summer", "native_language": "Tajik"})
    assert (p["daily_goal_minutes"], p["goal_text"], p["native_language"]) == (30, "HSK 3 by summer", "Tajik")
    for bad in ({"daily_goal_minutes": 4}, {"daily_goal_minutes": 241}, {"bio": "x" * 1001}):
        expect(client, "patch", "/api/me/profile", 422, headers=h, json=bad)
    assert expect(client, "get", "/api/me", 200, headers=h)["profile"]["daily_goal_minutes"] == 30


def test_privileged_fields_in_a_payload_are_never_applied(client, learner):
    uid, h, _ = learner
    expect(client, "patch", "/api/me/profile", 200, headers=h,
           json={"is_admin": True, "total_xp": 99999, "user_id": 1, "goal_text": "ok"})
    expect(client, "patch", "/api/me/account", 200, headers=h,
           json={"username": unique_name("renamed"), "is_admin": True, "is_active": False, "email": "x@evil.test"})
    with SessionLocal() as db:
        u = db.get(models.User, uid)
        assert u.is_admin is False and u.is_active is True and (u.total_xp or 0) == 0
        assert u.email.endswith("@example.com")


def test_renaming_signs_in_under_the_new_name_only(client, learner):
    _, h, old = learner
    new = unique_name("renamed")
    assert expect(client, "patch", "/api/me/account", 200, headers=h, json={"username": new})["username"] == new
    expect(client, "post", "/api/auth/login", 200, json={"username": new, "password": "secret1"})
    expect(client, "post", "/api/auth/login", 401, json={"username": old, "password": "secret1"})


def test_a_username_that_is_taken_in_any_letter_case_is_refused(client, learner):
    # Registration already refused case variants; renaming used to allow them.
    _, h, _ = learner
    taken = unique_name("taken")
    register_raw(client, taken)
    for variant in (taken, taken.upper(), taken.capitalize()):
        body = expect(client, "patch", "/api/me/account", 409, headers=h, json={"username": variant})
        assert body["detail"] == "username already taken"
    expect(client, "patch", "/api/me/account", 422, headers=h, json={"username": "ab"})


def test_renaming_to_a_different_case_of_ones_own_name_is_allowed(client, learner):
    _, h, name = learner
    assert expect(client, "patch", "/api/me/account", 200, headers=h,
                  json={"username": name.upper()})["username"] == name.upper()


def test_choosing_and_changing_the_permanent_companion(client, learner):
    uid, h, _ = learner
    expect(client, "post", "/api/me/animal", 404, headers=h, json={"animal_id": 999999})
    expect(client, "post", "/api/me/animal", 422, headers=h, json={"animal_id": 0})
    first = expect(client, "post", "/api/me/animal", 200, headers=h, json={"animal_id": 1})
    second = expect(client, "post", "/api/me/animal", 200, headers=h, json={"animal_id": 2})
    assert first["bond_level"] == 1 and second["animal_id"] == 2 and second["interactions"] == first["interactions"] + 1
    with SessionLocal() as db:
        assert db.get(models.User, uid).animal_id == 2
        assert db.query(models.UserAnimal).filter_by(user_id=uid).count() == 1


def test_the_daily_ping_counts_a_day_once(client, learner):
    _, h, _ = learner
    first = expect(client, "post", "/api/me/ping", 200, headers=h)
    again = expect(client, "post", "/api/me/ping", 200, headers=h)
    assert first["new_day"] is True and first["streak"]["current_streak"] == 1
    assert again["new_day"] is False and again["streak"]["current_streak"] == 1
    expect(client, "post", "/api/me/ping", 401)


def test_followers_and_following_lists(client, learner):
    uid, h, name = learner
    aid, ah = register(client, unique_name("fan"))
    bid, _ = register(client, unique_name("idol"))
    expect(client, "post", f"/api/users/{uid}/follow", 201, headers=ah)
    expect(client, "post", f"/api/users/{bid}/follow", 201, headers=h)
    followers = expect(client, "get", f"/api/users/{uid}/followers", 200, headers=h)
    following = expect(client, "get", f"/api/users/{uid}/following", 200, headers=h)
    assert [f["id"] for f in followers] == [aid] and followers[0]["is_following"] is False
    assert [f["id"] for f in following] == [bid] and following[0]["is_following"] is True
    for row in followers + following:
        assert "email" not in row and "password_hash" not in row
    expect(client, "get", "/api/users/999999/followers", 404, headers=h)
    expect(client, "get", "/api/users/999999/following", 404, headers=h)
    expect(client, "get", f"/api/users/{uid}/followers", 401)


def test_search_finds_others_never_oneself_and_exposes_no_email(client, learner):
    uid, h, name = learner
    oid, _ = register(client, unique_name("findme"))
    found = expect(client, "get", "/api/users/search?q=findme", 200, headers=h)
    assert oid in [u["id"] for u in found]
    assert uid not in [u["id"] for u in expect(client, "get", f"/api/users/search?q={name}", 200, headers=h)]
    assert all("email" not in u for u in found)
    expect(client, "get", "/api/users/search?q=", 422, headers=h)
    expect(client, "get", "/api/users/search?q=a", 401)
