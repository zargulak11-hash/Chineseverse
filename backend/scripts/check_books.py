"""Check every Chinese Stories book against the HSK curriculum.

    ..\.venv\Scripts\python.exe scripts\check_books.py [slug-or-level ...]

Boots a throwaway SQLite database with the real curriculum (never a real
database), loads every book file (the same validation the app runs at
startup) and prints, per book: chapters, sentences, characters, average
sentence length, difficulty, reading time, the words above the book's
level (with the allowed number) and any character the curriculum doesn't
know. Exits 1 if any book breaks a rule.
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/books_check.db"
os.environ["AI_PROVIDER"] = "offline"
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

from fastapi.testclient import TestClient  # noqa: E402

from app.database import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.services import books, stories  # noqa: E402


def main() -> int:
    wanted = set(sys.argv[1:])
    with TestClient(app):
        pass  # migrations + curriculum seed
    bad = 0
    per_level: dict[int, int] = {}
    with SessionLocal() as db:
        for b in books.all_books():
            per_level[b["level"]] = per_level.get(b["level"], 0) + 1
            if wanted and b["slug"] not in wanted and str(b["level"]) not in wanted:
                continue
            r = stories.vocabulary_report(db, b)
            flag = "ok " if r["ok"] else "BAD"
            bad += not r["ok"]
            cap = "-" if r["cap"] is None else r["cap"]
            print(f"{flag} HSK{b['level']} {b['slug']:<28} ch={len(b['chapters']):<2} sent={b['sentence_count']:<3} "
                  f"chars={b['characters']:<5} avg={r['avg_len']:<5} {r['difficulty']:<11} ~{r['minutes']}min "
                  f"above={len(r['above'])}/{cap}")
            if r["above"] and (not r["ok"] or wanted):
                print("      above level:", " ".join(r["above"]))
            if r["unknown_chars"]:
                print("      not in the curriculum:", "".join(r["unknown_chars"]))
    print("books per level:", dict(sorted(per_level.items())), "total:", sum(per_level.values()))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
