"""Every API route's access rule, checked from the app's own route table.

The audit found every route correctly gated, but only by reading them one
by one; a new router added without Depends(get_current_user) would be
public and nothing would notice. Here:

- the routes reachable without signing in must be exactly PUBLIC below, so
  adding one is a deliberate edit to this file;
- every other route answers 401 with no token or a garbage one;
- every admin route answers 403 to a signed-in learner.

Path parameters are filled with "1"; the auth dependency runs before the
route body or its own validation, so no route actually does anything.
"""

import re

import pytest
from fastapi.routing import APIRoute

from app.main import app
from helpers import bearer, register_raw, unique_name

# (method, path) of every route that works without a session. Content
# catalogues, sign-in itself and health checks only; the OPT ones show more
# (lesson bodies, unlocks) to a signed-in viewer but nothing private to
# anyone else.
PUBLIC = {
    ("GET", "/"), ("GET", "/health"), ("GET", "/api/health"),
    ("GET", "/api/auth/providers"), ("POST", "/api/auth/register"), ("POST", "/api/auth/login"),
    ("POST", "/api/auth/google"), ("POST", "/api/auth/password/forgot"),
    ("POST", "/api/auth/password/reset/check"), ("POST", "/api/auth/password/reset"),
    ("GET", "/api/auth/github/start"), ("GET", "/api/auth/github/callback"),
    ("POST", "/api/auth/github/session"),
    ("GET", "/api/animals"), ("GET", "/api/animals/{animal_id}"),
    ("GET", "/api/hsk/levels"), ("GET", "/api/hsk/skills"),
    # OPT: get_user_or_none
    ("GET", "/api/lessons"), ("GET", "/api/world/scenarios"), ("GET", "/api/world/scenarios/{slug}"),
}


def _deps(dependant, acc):
    for sub in dependant.dependencies:
        acc.add(getattr(sub.call, "__name__", ""))
        _deps(sub, acc)
    return acc


def _routes(routes):
    for r in routes:
        if hasattr(r, "original_router"):  # an included router (newer FastAPI)
            yield from _routes(r.original_router.routes)
        elif isinstance(r, APIRoute):
            yield r


ROUTES = [
    (method, r.path, _deps(r.dependant, set()))
    for r in _routes(app.routes)
    for method in sorted(r.methods)
]
NEEDS_USER = [(m, p) for m, p, d in ROUTES if {"get_current_user", "require_admin"} & d]
ADMIN_ONLY = [(m, p) for m, p, d in ROUTES if "require_admin" in d]


def concrete(path):
    return re.sub(r"\{[^}]+\}", "1", path)


def call(client, method, path, **kw):
    return client.request(method, concrete(path), **kw)


def test_the_route_table_was_read():
    # A FastAPI upgrade that changes how routes are nested must fail here,
    # not make every check below silently pass on an empty list.
    assert len(ROUTES) > 150 and len(ADMIN_ONLY) >= 20


def test_only_the_known_routes_work_without_a_session():
    unauthenticated = {(m, p) for m, p, d in ROUTES if not {"get_current_user", "require_admin"} & d}
    assert unauthenticated == PUBLIC, (
        "New route reachable without signing in -- gate it, or add it to PUBLIC on purpose: "
        f"{sorted(unauthenticated - PUBLIC)}; listed but gone: {sorted(PUBLIC - unauthenticated)}"
    )


@pytest.mark.parametrize("method, path", NEEDS_USER)
def test_no_token_or_a_bad_token_is_a_401(client, method, path):
    assert call(client, method, path).status_code == 401
    assert call(client, method, path, headers=bearer("not.a.jwt")).status_code == 401


@pytest.fixture(scope="module")
def learner(client):
    return bearer(register_raw(client, unique_name("routecheck"))["access_token"])


@pytest.mark.parametrize("method, path", ADMIN_ONLY)
def test_a_learner_gets_403_from_every_admin_route(client, learner, method, path):
    r = call(client, method, path, headers=learner, json={})
    assert r.status_code == 403, (method, path, r.status_code, r.text[:200])
    assert r.json()["detail"] == "Admin access required"
