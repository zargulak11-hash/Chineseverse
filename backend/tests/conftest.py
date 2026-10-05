"""Shared pytest setup for the backend suite.

Each test module gets its own SQLite database, so modules never see each
other's learners, XP or notifications -- the same isolation the old
standalone scripts had by building a temp database each. Building one from
scratch (every Alembic migration + the full curriculum seed) takes ~10 s,
so it happens once per run into a template file that each module copies.
The app's normal startup (migrations to head, idempotent seed) still runs
on every copy, exactly as on a deployed server.

Configuration comes from the environment set here only, never from the
developer's backend/.env: that file can hold real SMTP and Gemini
credentials, and a test must neither send real email nor spend AI quota.
Tests that exercise those paths stub the transport/model themselves.
"""

import os
import shutil
import sys
import tempfile
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
TESTS_DIR = Path(__file__).resolve().parent
for _p in (str(BACKEND_DIR), str(TESTS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

_TMP = Path(tempfile.mkdtemp(prefix="chineseverse-tests-"))
TEMPLATE_DB = _TMP / "template.db"


def sqlite_url(path: Path) -> str:
    return f"sqlite:///{path.as_posix()}"


os.environ.update(
    {
        "DATABASE_URL": sqlite_url(TEMPLATE_DB),
        "JWT_SECRET": "test-only-jwt-secret",
        "AI_PROVIDER": "offline",
        "GEMINI_API_KEY": "",
        "SMTP_HOST": "",
        "SMTP_USERNAME": "",
        "SMTP_PASSWORD": "",
        "SMTP_FROM": "",
        "GOOGLE_CLIENT_ID": "",
        "TRUSTED_PROXY_HOPS": "0",
    }
)
os.environ.pop("ALEMBIC_DATABASE_URL", None)

from app import config  # noqa: E402

# Settings() was already built at import and may have read a backend/.env
# in the working directory; replace every field with the environment-only
# values so a run is the same on any machine and in CI.
_clean = config.Settings(_env_file=None)
for _name in type(_clean).model_fields:
    setattr(config.settings, _name, getattr(_clean, _name))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402

from app import database  # noqa: E402
from app.main import app  # noqa: E402


def bind_database(url: str):
    """Point the app (engine, SessionLocal, Alembic's URL) at `url`.

    SessionLocal is one sessionmaker shared by every module that imported
    it, so rebinding it reaches all of them; anything needing the engine
    reads `database.engine` at call time."""
    old = database.engine
    engine = create_engine(url, pool_pre_ping=True)
    database.engine = engine
    database.SessionLocal.configure(bind=engine)
    config.settings.database_url = url
    old.dispose()
    return engine


def reset_process_state() -> None:
    """In-process limits and caches are keyed by user id or content and
    would otherwise carry over from one module's database to the next."""
    from app.routers import assistant
    from app.services import ai_client, grammar_lesson, lesson_path, login_throttle, stories

    assistant._chat_calls.clear()
    grammar_lesson._ai_calls.clear()
    stories._ai_calls.clear()
    ai_client._cooling_until.clear()
    ai_client._translation_cache.clear()
    lesson_path._practicable_cache.update(key=None, ids=frozenset())
    login_throttle.reset()


@pytest.fixture(scope="session")
def template_db() -> Path:
    bind_database(sqlite_url(TEMPLATE_DB))
    with TestClient(app):
        pass
    database.engine.dispose()
    return TEMPLATE_DB


@pytest.fixture(scope="module")
def module_db(template_db, request) -> str:
    """A fresh copy of the seeded template for this module; returns its URL."""
    path = _TMP / f"{request.module.__name__.rsplit('.', 1)[-1]}.db"
    shutil.copyfile(template_db, path)
    url = sqlite_url(path)
    bind_database(url)
    reset_process_state()
    return url


@pytest.fixture(scope="module")
def client(module_db):
    with TestClient(app) as c:
        yield c
    database.engine.dispose()


@pytest.fixture
def empty_db_url() -> str:
    """A URL for a database file that doesn't exist yet (migration tests)."""
    fd, name = tempfile.mkstemp(suffix=".db", dir=_TMP)
    os.close(fd)
    os.remove(name)
    return sqlite_url(Path(name))


@pytest.fixture(autouse=True)
def _fresh_login_throttle():
    # Failed logins in one test must not lock an account in the next.
    from app.services import login_throttle

    login_throttle.reset()
    yield
