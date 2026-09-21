from contextlib import asynccontextmanager
from logging.config import dictConfig

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.seed import needs_seed, seed_all

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

ALWAYS_MISSING_COLUMNS = [
    ("animals", "slug", "VARCHAR(50)"),
    ("animals", "accent_color", "VARCHAR(20)"),
    ("animals", "personality", "VARCHAR(300)"),
    ("animals", "tone_style", "TEXT"),
    ("animals", "preferred_mechanics", "TEXT"),
    ("animals", "special_ability", "VARCHAR(300)"),
    ("users", "is_active", "BOOLEAN DEFAULT true"),
    ("lessons", "summary", "VARCHAR(300)"),
    ("lessons", "lesson_type", "VARCHAR(30)"),
    ("lessons", "hsk_level_id", "INTEGER"),
]

# Columns removed from the current models that used to exist in V1 tables.
OBSOLETE_COLUMNS = [
    ("lessons", "hsk_level"),
]


def _ensure_schema() -> None:
    """Bring a pre-existing database up to the current model (idempotent)."""
    dialect = engine.url.get_backend_name()
    with engine.begin() as conn:
        for table, column, column_type in ALWAYS_MISSING_COLUMNS:
            if dialect == "postgresql":
                conn.execute(
                    text(
                        f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {column_type}"
                    )
                )
        for table, column in OBSOLETE_COLUMNS:
            if dialect == "postgresql":
                conn.execute(text(f"ALTER TABLE {table} DROP COLUMN IF EXISTS {column}"))


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    try:
        _ensure_schema()
    except Exception as exc:  # non-postgres dialects
        import logging

        logging.getLogger("app").warning("Schema ensure skipped: %s", exc)
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