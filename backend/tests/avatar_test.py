"""Profile photo or initial -- never a default picture. On a fresh SQLite
database: a new user has no photo anywhere the API describes a person; an
upload shows everywhere and replaces the previous one; removing it brings
the initial back; a stored photo whose file is gone is reported as no
photo (instead of a broken image); it all survives a new login."""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/avatar.db"
os.environ["AI_PROVIDER"] = "offline"

from fastapi.testclient import TestClient  # noqa: E402

from app import models  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.services import avatars  # noqa: E402

# A real 1x1 PNG.
PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d49444154789c6360f8cfc0f01f0005000201e2b1f7a40000000049454e44ae426082"
)


def expect(client, method, url, expected, **kwargs):
    resp = getattr(client, method)(url, **kwargs)
    assert resp.status_code == expected, f"{method.upper()} {url} -> {resp.status_code} (expected {expected}): {resp.text}"
    return resp.json() if resp.content else None


def register(client, name):
    data = expect(client, "post", "/api/auth/register", 201,
                  json={"username": name, "email": f"{name}@example.com", "password": "secret1"})
    return data["user"]["id"], {"Authorization": f"Bearer {data['access_token']}"}


def seen_by_everyone(client, uid, h, oh, name):
    """avatar_url for this user from every endpoint that describes them."""
    me = expect(client, "get", "/api/me", 200, headers=h)["profile"]["avatar_url"]
    dash = expect(client, "get", "/api/dashboard", 200, headers=h)["avatar_url"]
    public = expect(client, "get", f"/api/users/{uid}/public", 200, headers=oh)["avatar_url"]
    found = [u for u in expect(client, "get", f"/api/users/search?q={name}", 200, headers=oh) if u["id"] == uid]
    return {me, dash, public, found[0]["avatar_url"]}


with TestClient(app) as client:
    uid, h = register(client, "photoless")
    oid, oh = register(client, "onlooker")

    # 1. new user: no photo anywhere -- no animal, no default image
    assert seen_by_everyone(client, uid, h, oh, "photoless") == {None}
    with SessionLocal() as db:
        assert db.query(models.UserProfile).filter_by(user_id=uid).one().avatar_url is None
    expect(client, "post", "/api/me/animal", 200, headers=h, json={"animal_id": 1})
    assert seen_by_everyone(client, uid, h, oh, "photoless") == {None}, "choosing a companion must not become the photo"
    print("[PASS] a new user (with or without a companion) has no photo anywhere -> the UI shows the initial")

    # 2. upload: shows everywhere, and the file is really served
    expect(client, "post", "/api/me/avatar", 415, headers=h, files={"file": ("x.gif", b"GIF89a", "image/gif")})
    expect(client, "post", "/api/me/avatar", 401, files={"file": ("a.png", PNG, "image/png")})
    url = expect(client, "post", "/api/me/avatar", 200, headers=h, files={"file": ("a.png", PNG, "image/png")})["avatar_url"]
    assert url.startswith(avatars.UPLOAD_PREFIX) and avatars.file_for(url).is_file()
    assert seen_by_everyone(client, uid, h, oh, "photoless") == {url}
    assert client.get(url).status_code == 200
    print("[PASS] an uploaded photo is the avatar everywhere and is served")

    # 3. a later upload replaces it (and the old file is gone)
    url2 = expect(client, "post", "/api/me/avatar", 200, headers=h, files={"file": ("b.png", PNG, "image/png")})["avatar_url"]
    assert url2 != url and not avatars.file_for(url).exists() and seen_by_everyone(client, uid, h, oh, "photoless") == {url2}
    print("[PASS] uploading again replaces the photo")

    # 4. notifications show the sender's photo too
    expect(client, "post", f"/api/users/{oid}/follow", 201, headers=h)
    actor = next(n["actor"] for n in expect(client, "get", "/api/notifications", 200, headers=oh) if n["actor"])
    assert actor["id"] == uid and actor["avatar_url"] == url2, actor
    print("[PASS] notification senders carry the same photo")

    # 5. persists across a new login
    tok = expect(client, "post", "/api/auth/login", 200, json={"username": "photoless", "password": "secret1"})
    h2 = {"Authorization": f"Bearer {tok['access_token']}"}
    assert seen_by_everyone(client, uid, h2, oh, "photoless") == {url2}
    print("[PASS] the photo survives logging out and back in")

    # 6. the file is lost (e.g. a deploy before uploads had a volume):
    #    reported as no photo, the stored row is untouched
    path = avatars.file_for(url2)
    data = path.read_bytes()
    path.unlink()
    assert seen_by_everyone(client, uid, h2, oh, "photoless") == {None}
    actor = next(n["actor"] for n in expect(client, "get", "/api/notifications", 200, headers=oh) if n["actor"])
    assert actor["avatar_url"] is None
    with SessionLocal() as db:
        assert db.query(models.UserProfile).filter_by(user_id=uid).one().avatar_url == url2
    path.write_bytes(data)
    assert seen_by_everyone(client, uid, h2, oh, "photoless") == {url2}, "a restored file shows again"
    print("[PASS] a photo whose file is missing reads as 'no photo' (initial), never a broken image")

    # 7. removing it brings the initial back, and deletes the file
    expect(client, "delete", "/api/me/avatar", 200, headers=h2)
    assert not path.exists() and seen_by_everyone(client, uid, h2, oh, "photoless") == {None}
    expect(client, "delete", "/api/me/avatar", 200, headers=h2)  # idempotent
    print("[PASS] removing the photo returns to the initial")

    # 8. only real upload paths count; nothing outside the folder is touched
    for bad in ("/static/uploads/avatars/../../app/main.py", "/static/uploads/avatars/", "https://example.com/p.png",
                "/static/animals/panda.png", "", None):
        assert avatars.file_for(bad) is None or bad.endswith("/"), bad
        assert avatars.existing_url(bad) is None, bad
    print("[PASS] only an uploaded file in the avatars folder counts as a photo")

print("ALL AVATAR TESTS PASSED")
