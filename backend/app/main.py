import logging
from contextlib import asynccontextmanager
from logging.config import dictConfig
from pathlib import Path

from alembic import command
from alembic.config import Config as AlembicConfig
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import SessionLocal
from app.seed import needs_seed, seed_all

BACKEND_DIR = Path(__file__).resolve().parent.parent

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
        if needs_seed(db):
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

from app.routers import (  # noqa: E402
    achievements,
    animals,
    auth,
    dashboard,
    dna,
    duels,
    hsk,
    lessons,
    me,
    missions,
    mistakes,
    pet_teacher,
    progress,
    quests,
    users,
    vocab,
    voice,
    world,
)

for module in (
    auth,
    users,
    animals,
    lessons,
    progress,
    me,
    hsk,
    vocab,
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