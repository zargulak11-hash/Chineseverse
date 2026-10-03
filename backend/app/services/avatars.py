"""The user's profile photo -- the one rule every response follows.

A user either has a real uploaded photo or has none; there is no default
picture (no companion animal, no stock image). The UI shows the photo when
`avatar_url` is set and the user's initial when it is null.

Why the file is checked: uploads are stored on the backend's disk
(static/uploads/avatars). Before they lived on a Docker volume, every
deploy rebuilt the container and silently dropped the files while
`user_profiles.avatar_url` still pointed at them -- the app then claimed a
photo that didn't exist and browsers drew a broken image. A stored path
whose file is gone is reported as "no photo" (the row itself is left as
it is, so a restored file simply shows again).
"""

from __future__ import annotations

from pathlib import Path

from app import models

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
AVATAR_DIR = BACKEND_DIR / "static" / "uploads" / "avatars"
UPLOAD_PREFIX = "/static/uploads/avatars/"


def file_for(url: str | None) -> Path | None:
    """The on-disk file behind an uploaded-avatar URL (None for anything else)."""
    if not url or not url.startswith(UPLOAD_PREFIX):
        return None
    name = url[len(UPLOAD_PREFIX):]
    if not name or "/" in name or "\\" in name or name.startswith("."):
        return None
    return AVATAR_DIR / name


def existing_url(url: str | None) -> str | None:
    """`url` if it names an uploaded photo that is really there, else None."""
    path = file_for(url)
    return url if path is not None and path.is_file() else None


def photo_url(user: models.User | None) -> str | None:
    """The user's real profile photo URL, or None (-> the UI shows the initial)."""
    profile = user.profile if user is not None else None
    return existing_url(profile.avatar_url) if profile is not None else None
