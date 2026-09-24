import logging
from contextlib import asynccontextmanager
from logging.config import dictConfig
from pathlib import Path

from alembic import command
from alembic.config import Config as AlembicConfig
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import SessionLocal
from app.seed import seed_all

BACKEND_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BACKEND_DIR / "static"
(STATIC_DIR / "uploads" / "avatars").mkdir(parents=True, exist_ok=True)

dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {"std": {"format": "%(asctime)s %(levelname)s %(name)s: %(message)s"}},
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "std",
            }
        },
        "root": {"handlers": ["console"], "level": "INFO"},
        "loggers": {
            "app": {"level": "INFO", "handlers": ["console"], "propagate": False},
            "uvicorn": {"level": "INFO", "handlers": ["console"], "propagate": False},
            "uvicorn.error": {"level": "INFO", "handlers": ["console"], "propagate": False},
            "uvicorn.access": {"level": "INFO", "handlers": ["console"], "propagate": False},
        },
    }
)

def _run_migrations() -> None:
    """Bring the database schema up to date via Alembic.

    This replaces an earlier ad-hoc ALTER TABLE patch list that only
    understood Postgres and had to be hand-maintained per column. Schema
    changes now go through `alembic revision --autogenerate` + a migration
    file in alembic/versions/, and this just applies whatever is pending —
    including creating every table from scratch on a brand-new database.
    """
    cfg = AlembicConfig(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    command.upgrade(cfg, "head")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    _run_migrations()
    logging.getLogger("app").info("Database migrations applied.")
    with SessionLocal() as db:
        # Every seed_* function guards against duplicates by checking for an
        # existing row before inserting, so this is safe (and cheap) to run
        # on every startup. It used to be gated behind needs_seed() (only
        # HSKLevel.count() == 0), which meant a seed function added after
        # the DB was first seeded — e.g. seed_pet_teacher_cases — silently
        # never ran on existing databases.
        seed_all(db)
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Uploaded profile pictures (see routers/me.py: POST /api/me/avatar) — a
# plain local static directory, not a cloud storage integration, since
# nothing in this project already talks to one.
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.middleware("http")
async def crash_logger(request, call_next):
    # Temporary diagnostic: the logging module setup in this process isn't
    # reliably surfacing uvicorn access/error logs to the console (root
    # cause still under investigation), so unhandled exceptions were
    # invisible. This writes a plain-file traceback for any 500, bypassing
    # the logging module entirely, so real crashes can be seen and this can
    # be removed once that's resolved.
    import traceback as _traceback

    try:
        return await call_next(request)
    except Exception:
        with open(BACKEND_DIR / "crash.log", "a", encoding="utf-8") as f:
            f.write(f"\n=== {request.method} {request.url.path} ===\n")
            f.write(_traceback.format_exc())
            f.write("\n")
        raise

from app.routers import (  # noqa: E402
    achievements,
    analytics,
    animals,
    assistant,
    auth,
    dashboard,
    dna,
    duels,
    grammar,
    hanzi,
    hsk,
    lessons,
    me,
    missions,
    mistakes,
    onboarding,
    pet_teacher,
    progress,
    quests,
    social,
    users,
    vocab,
    voice,
    world,
)

for module in (
    auth,
    # social must precede users: both share the /api/users prefix, and
    # social's literal /api/users/search path needs to win route matching
    # over users.py's catch-all GET /api/users/{user_id} (see social.py).
    social,
    users,
    animals,
    lessons,
    progress,
    me,
    onboarding,
    hsk,
    vocab,
    grammar,
    hanzi,
    world,
    voice,
    missions,
    dna,
    duels,
    quests,
    achievements,
    mistakes,
    pet_teacher,
    dashboard,
    assistant,
    analytics,
):
    app.include_router(module.router)


@app.get("/")
def root():
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "status": "ok",
    }


@app.get("/health")
def health():
    return {"status": "ok"}