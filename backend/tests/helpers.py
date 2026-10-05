"""HTTP helpers shared by the API tests (previously copied into every
standalone script)."""

import itertools

_serial = itertools.count(1)


def unique_name(prefix="learner"):
    """A username no other test in the module has used."""
    return f"{prefix}_{next(_serial)}"


def expect_response(client, method, url, expected, **kwargs):
    """Make a request and assert its status; returns the response."""
    resp = getattr(client, method)(url, **kwargs)
    assert resp.status_code == expected, (
        f"{method.upper()} {url} -> {resp.status_code} (expected {expected}): {resp.text[:500]}"
    )
    return resp


def expect(client, method, url, expected, **kwargs):
    """Like expect_response, but returns the decoded JSON body (or None)."""
    resp = expect_response(client, method, url, expected, **kwargs)
    return resp.json() if resp.content else None


def bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def register_raw(client, name, password="secret1"):
    """Register `name` (email name@example.com); returns the token response."""
    return expect(
        client, "post", "/api/auth/register", 201,
        json={"username": name, "email": f"{name}@example.com", "password": password},
    )


def register(client, name, password="secret1"):
    """Register a learner; returns (user_id, auth headers)."""
    data = register_raw(client, name, password)
    return data["user"]["id"], bearer(data["access_token"])
