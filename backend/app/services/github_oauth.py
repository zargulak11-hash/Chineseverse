"""GitHub sign-in: the provider side of the OAuth App authorization-code
flow (routers/auth.py owns state, cookies and redirects).

The browser only ever sees GitHub's authorize page and our callback. The
code-for-token exchange happens here, server to server, with the client
secret; the GitHub access token it returns is used for two read-only calls
(the profile and the email list) and then dropped -- it is never stored,
logged or sent to the frontend.

Every failure is raised as GitHubAuthError with a short stable `code` the
router turns into a redirect the frontend can translate.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
TOKEN_URL = "https://github.com/login/oauth/access_token"
API_URL = "https://api.github.com"
CALLBACK_PATH = "/api/auth/github/callback"
# read:user for the profile, user:email for the email list -- a private
# primary email is missing from /user without it. Nothing else.
SCOPE = "read:user user:email"
TIMEOUT = 10.0


class GitHubAuthError(Exception):
    def __init__(self, code: str, log_message: str = ""):
        super().__init__(log_message or code)
        self.code = code


@dataclass
class GitHubIdentity:
    id: str
    email: str
    name: str | None
    login: str | None


def is_configured() -> bool:
    return bool(settings.github_client_id and settings.github_client_secret)


def redirect_uri() -> str:
    if settings.github_redirect_uri:
        return settings.github_redirect_uri
    return settings.public_app_url.rstrip("/") + CALLBACK_PATH


def authorize_url(state: str) -> str:
    query = urlencode(
        {
            "client_id": settings.github_client_id,
            "redirect_uri": redirect_uri(),
            "scope": SCOPE,
            "state": state,
            "allow_signup": "true",
        }
    )
    return f"{AUTHORIZE_URL}?{query}"


def _api_headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def exchange_code(code: str) -> str:
    """The authorization code -> a GitHub access token (never logged)."""
    try:
        resp = httpx.post(
            TOKEN_URL,
            data={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
                "redirect_uri": redirect_uri(),
            },
            headers={"Accept": "application/json"},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise GitHubAuthError("github_unreachable", f"token exchange failed: {type(exc).__name__}") from exc
    token = data.get("access_token")
    if not token:
        # GitHub answers 200 with an "error" field: bad_verification_code
        # (expired, already used -- e.g. the callback opened twice),
        # incorrect_client_credentials, redirect_uri_mismatch. Only the
        # error name is logged, never the request.
        error = data.get("error") or "no_access_token"
        if error == "bad_verification_code":
            raise GitHubAuthError("github_code", "authorization code rejected: bad_verification_code")
        raise GitHubAuthError("github_failed", f"token exchange refused: {error}")
    return token


def fetch_identity(token: str) -> GitHubIdentity:
    """The account id and a VERIFIED email. GitHub lists every address on
    the account with its own verified flag; only a verified one may create
    or link a ChineseVerse account (the same rule Google sign-in follows),
    preferring the primary address."""
    try:
        with httpx.Client(timeout=TIMEOUT, headers=_api_headers(token)) as client:
            user_resp = client.get(f"{API_URL}/user")
            user_resp.raise_for_status()
            profile = user_resp.json()
            emails_resp = client.get(f"{API_URL}/user/emails")
            emails_resp.raise_for_status()
            emails = emails_resp.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise GitHubAuthError("github_unreachable", f"profile request failed: {type(exc).__name__}") from exc

    account_id = profile.get("id")
    if account_id is None:
        raise GitHubAuthError("github_failed", "profile without an id")
    verified = [
        e for e in (emails if isinstance(emails, list) else [])
        if isinstance(e, dict) and e.get("verified") and e.get("email")
    ]
    # noreply addresses can't receive mail and say nothing about who owns
    # them; they must not create an account or match an existing one.
    verified = [e for e in verified if not e["email"].lower().endswith("@users.noreply.github.com")]
    if not verified:
        raise GitHubAuthError("github_no_email", "no verified email on the account")
    chosen = next((e for e in verified if e.get("primary")), verified[0])
    return GitHubIdentity(
        id=str(account_id),
        email=chosen["email"],
        name=profile.get("name"),
        login=profile.get("login"),
    )
