"""The Android / iOS app (Capacitor) runs the frontend from the phone itself
and calls this API across origins: https://localhost on Android,
capacitor://localhost on iOS. Its requests must pass CORS -- the preflight
for an authenticated JSON call included -- while a stranger's origin still
gets no CORS grant."""

import pytest

from helpers import bearer, expect_response, register, unique_name

APP_ORIGINS = ["https://localhost", "capacitor://localhost"]


@pytest.mark.parametrize("origin", APP_ORIGINS)
def test_the_app_preflight_is_allowed(client, origin):
    resp = client.options(
        "/api/auth/login",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type,x-locale,x-timezone",
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.headers["access-control-allow-origin"] == origin


@pytest.mark.parametrize("origin", APP_ORIGINS)
def test_the_app_reads_its_own_data_with_a_token(client, origin):
    _, headers = register(client, unique_name("mobile"))
    resp = expect_response(client, "get", "/api/me", 200, headers={**headers, "Origin": origin})
    assert resp.headers["access-control-allow-origin"] == origin


def test_an_unknown_origin_gets_no_cors_grant(client):
    resp = client.options(
        "/api/auth/login",
        headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"},
    )
    assert "access-control-allow-origin" not in resp.headers


def test_the_website_origin_list_still_applies(client):
    resp = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert resp.headers["access-control-allow-origin"] == "http://localhost:5173"
