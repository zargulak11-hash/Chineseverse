"""Shared logic for the HSK 7-9 advanced band: per the real HSK 3.0
standard, levels 7/8/9 share ONE vocabulary/Hanzi/grammar pool rather than
three independent official lists (see HSKLevel.is_advanced_band). Every
endpoint that lets a user filter/browse by "HSK level" 7, 8 or 9 must slice
that one real pool the same way, so counts shown on the roadmap always match
what the vocabulary/Hanzi/grammar pages actually list -- never three
separately-fabricated lists and never a mismatch between screens.
"""
from sqlalchemy.orm import Session

from app import models


def split_thirds(ids: list[int]) -> list[list[int]]:
    n = len(ids)
    a, b = n // 3, (2 * n) // 3
    return [ids[:a], ids[a:b], ids[b:]]


def resolve_level_filter(db: Session, model, id_field, hsk_level: int):
    """Given a requested `hsk_level` (1-9) and the model/column to filter on,
    returns (hsk_level_id, id_subset_or_None) to apply as filters. For 1-6 or
    any level with its own real HSKLevel row, id_subset is None (no extra
    slicing). For 7/8/9 served by a shared advanced-band row, id_subset is
    the real ids belonging to that stage's third of the band."""
    lvl = db.query(models.HSKLevel).filter(models.HSKLevel.level == hsk_level).first()
    if lvl is not None and not lvl.is_advanced_band:
        return lvl.id, None

    # hsk_level is 7/8/9 served by the shared advanced band (whether `lvl`
    # itself is that band's own row, at level 7, or 8/9 have no row at all):
    # always slice into the same three real thirds the roadmap uses, so
    # "HSK 7" here never silently means "the whole band."
    if hsk_level not in (7, 8, 9):
        return None, None
    band = lvl if (lvl is not None and lvl.is_advanced_band) else (
        db.query(models.HSKLevel).filter(models.HSKLevel.is_advanced_band.is_(True)).first()
    )
    if band is None:
        return None, None
    ids = [row.id for row in db.query(model.id).filter(id_field == band.id).order_by(model.id).all()]
    thirds = split_thirds(ids)
    stage_index = hsk_level - 7
    return band.id, thirds[stage_index]


def display_level_for_row(db: Session, model, id_field, row) -> int:
    """The inverse of resolve_level_filter: given one real row that belongs
    to the advanced band, which of the three real thirds (-> which of HSK
    7/8/9) does it fall in? Used so a per-row response (e.g. a lesson) can
    report the correct stage even when fetched outside a level-filtered
    list. Non-band rows just report their real HSKLevel.level."""
    level = row.level if hasattr(row, "level") else db.get(models.HSKLevel, getattr(row, "hsk_level_id", None))
    if level is None or not level.is_advanced_band:
        return level.level if level else None
    ids = [r.id for r in db.query(model.id).filter(id_field == level.id).order_by(model.id).all()]
    thirds = split_thirds(ids)
    for stage_index, chunk in enumerate(thirds):
        if row.id in chunk:
            return 7 + stage_index
    return level.level
