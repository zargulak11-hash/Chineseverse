from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.deps import get_current_user, get_locale
from app.services.hsk_band import resolve_level_filter
from app.services.localization import load_translations, tr
from app.services.gamification import ensure_user_skills
from app.services.srs import is_slipping

router = APIRouter(prefix="/api/vocab", tags=["vocabulary"])

# Read-only. POST /{word_id}/review used to take {"correct": true} from the
# browser and apply it as a graded answer: nine requests in a row marked any
# word "mastered", and each one bumped Learning DNA, quests and missions. No
# screen called it any more -- words are learned through the server-graded
# rounds in /api/practice -- so it was removed rather than kept as a bypass.


@router.get("", response_model=list[schemas.WordWithStatus])
def list_words(
    hsk_level: int | None = None,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    locale: str = Depends(get_locale),
):
    ensure_user_skills(db, user)
    query = db.query(models.VocabularyWord)
    if hsk_level is not None:
        level_id, id_subset = resolve_level_filter(db, models.VocabularyWord, models.VocabularyWord.hsk_level_id, hsk_level)
        query = query.filter(models.VocabularyWord.hsk_level_id == (level_id or 0))
        if id_subset is not None:
            query = query.filter(models.VocabularyWord.id.in_(id_subset or [0]))
    words = query.order_by(models.VocabularyWord.id).all()

    # Only `meanings` is localized -- simplified/traditional/pinyin/example
    # are the actual Chinese being taught and stay Chinese in every locale.
    translations = load_translations(db, "vocab_word", [str(w.id) for w in words], locale)
    user_map = {w.word_id: w for w in user.user_vocabulary}
    now = datetime.utcnow()
    out = []
    for word in words:
        item = schemas.WordWithStatus.model_validate(word)
        item.meanings = tr(translations, word.id, "meanings", item.meanings)
        rec = user_map.get(word.id)
        item.status = rec.status if rec else "new"
        item.mastery = rec.mastery if rec else 0.0
        item.due_for_review = bool(rec and rec.next_review_at and rec.next_review_at <= now)
        item.slipping = is_slipping(rec, now)
        out.append(item)
    # Resurface what's actually due first, instead of a fixed id order —
    # this is the "Memory of the World" reading the schedule it writes.
    out.sort(key=lambda w: (not w.due_for_review, w.id))
    return out


@router.get("/ecosystem")
def vocabulary_ecosystem(
    center: str | None = Query(default=None, max_length=4),
    hsk_max: int | None = Query(default=None, ge=1, le=9),
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    locale: str = Depends(get_locale),
):
    """A small network around one character: its compounds within the HSK
    filter and the characters they connect to, with the learner's own
    status on every node (services/character_dna.ecosystem). Read-only."""
    from fastapi import HTTPException

    from app.services import character_dna as svc

    ensure_user_skills(db, user)
    try:
        return svc.ecosystem(db, user, center, hsk_max, locale)
    except svc.CharacterError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.detail) from exc


@router.post("/{word_id}/track")
def track_word(
    word_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add one word to the learner's review schedule (e.g. from the Chinese
    Internet word helper). Refused with 409 when the word is already being
    reviewed or is mastered -- nothing is duplicated, mastery is untouched."""
    from fastapi import HTTPException

    from app.services import internet as svc

    try:
        return svc.track_word(db, user, word_id)
    except svc.InternetError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.detail) from exc
