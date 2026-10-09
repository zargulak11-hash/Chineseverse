"""Translations of DB-driven content (one generic table for every language)."""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    UniqueConstraint,
)

from app.database import Base

# ---------------------------------------------------------------------------
# Localization — one generic table for every translatable DB-driven string,
# instead of a locale column bolted onto each content table (which would
# mean a migration per table per language) or a duplicate table per
# language (explicitly ruled out). `content_key` is the row's own primary
# key as a string for normal content (lesson id, mission id, ...), or a
# stable code for content that isn't a single DB row (e.g. a quest
# template, keyed by its quest_type). English is never stored here — it's
# always the original column value, which callers use as the fallback.
# ---------------------------------------------------------------------------


class ContentTranslation(Base):
    __tablename__ = "content_translations"
    __table_args__ = (
        UniqueConstraint("content_type", "content_key", "field", "locale", name="uq_content_translation"),
    )

    id = Column(Integer, primary_key=True, index=True)
    content_type = Column(String(40), nullable=False, index=True)  # "lesson", "vocab_word", "quest_template", ...
    content_key = Column(String(40), nullable=False, index=True)   # str(row.id) or a stable code
    field = Column(String(40), nullable=False)                     # "title", "description", "meanings", ...
    locale = Column(String(5), nullable=False)                     # "ru" | "tg" | "zh"
    text = Column(Text, nullable=False)
    # NULL = authored; "draft" = written to close a gap and awaiting native
    # review (scripts/export_translation_review.py lists them).
    source = Column(String(20), nullable=True)
