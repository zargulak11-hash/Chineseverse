"""Chinese-locale vocabulary 'meaning' -- per the spec's own worked example
(target word 你好 / meaning 你好 when the UI language is Chinese itself),
the gloss mirrors the simplified word for every vocabulary word. This is
mechanical and covers all words regardless of HSK level, run once."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app import models
from app.services.localization import set_translation

db = SessionLocal()
words = db.query(models.VocabularyWord).all()
for w in words:
    set_translation(db, "vocab_word", str(w.id), "meanings", "zh", w.simplified)
db.commit()
print(f"Chinese vocab mirror: {len(words)} words covered.")
