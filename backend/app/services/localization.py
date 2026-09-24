"""Locale-aware lookup for database-driven content.

One generic table (`ContentTranslation`) instead of a locale column per
content table or a duplicate table per language — see the model's own
docstring in models.py. English is never stored here; it's always the
content table's own column, used as the fallback when a translation row
doesn't exist for the requested locale (or the locale is "en").
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app import models

SUPPORTED_LOCALES = {"ru", "tg", "zh"}


def load_translations(
    db: Session, content_type: str, keys: list[str], locale: str
) -> dict[str, dict[str, str]]:
    """Batch-fetch every translated field for `keys` in one query, returned
    as {content_key: {field: text}}. English/unsupported locales return {}
    without a query — callers just fall through to the original column."""
    if locale not in SUPPORTED_LOCALES or not keys:
        return {}
    rows = (
        db.query(models.ContentTranslation)
        .filter(
            models.ContentTranslation.content_type == content_type,
            models.ContentTranslation.content_key.in_(keys),
            models.ContentTranslation.locale == locale,
        )
        .all()
    )
    out: dict[str, dict[str, str]] = {}
    for r in rows:
        out.setdefault(r.content_key, {})[r.field] = r.text
    return out


def tr(translations: dict[str, dict[str, str]], key: str, field: str, fallback: str | None) -> str | None:
    """Pick the localized value for one row/field, or fall back to the
    original (English) column value when no translation exists."""
    row = translations.get(str(key))
    if row and field in row:
        return row[field]
    return fallback


def set_translation(db: Session, content_type: str, content_key: str, field: str, locale: str, text: str) -> None:
    """Idempotent upsert, used by the seeding script -- re-running it never
    creates duplicate rows."""
    existing = (
        db.query(models.ContentTranslation)
        .filter_by(content_type=content_type, content_key=str(content_key), field=field, locale=locale)
        .first()
    )
    if existing:
        existing.text = text
    else:
        db.add(models.ContentTranslation(
            content_type=content_type, content_key=str(content_key), field=field, locale=locale, text=text,
        ))
