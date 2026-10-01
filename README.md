# ChineseVerse

A Chinese learning platform built around the real HSK 3.0 curriculum (levels 1–6 plus the shared 7–9 advanced band). Every lesson, practice answer and review feeds the same learner record in PostgreSQL. That record drives mastery, the Learning DNA and the companion's reactions.

Production: https://chineseverse.qobus.tj/

## Learning loop

```
HSK level → Lesson → Vocabulary / Hanzi / Grammar → Practice → Result
          → Companion reaction → Progress + Learning DNA → Review → …
```

- **Curriculum**: 11,334 vocabulary items, 3,000 Hanzi with stroke data, 600 grammar points, 111 lessons, and ru/tg/zh translations. HSK 7–9 is one shared advanced pool, as in the official standard.
- **Practice** (`/practice`, `POST /api/practice/sessions`): the server builds and grades each round. Question types are word ↔ meaning, listening, Hanzi meaning, Hanzi pinyin (with tone distractors) and grammar-in-context. The client only sends the option id it chose.
- **Duels** (`/duels`): a real 1-vs-1 between two users. A challenge is accepted or declined by the invited player; both then get the same server-stored questions and their own server-timed clock, and the server decides the winner (correct answers, then score, then time).
- **Review** (`/review`): items due under spaced repetition, plus unresolved mistakes. Mistakes come from practice, duels, voice and Hanzi tracing.
- **Lessons**: a lesson links to the words and grammar it teaches (`GET /api/lessons/{id}/items`). It counts as completed only when its practice round scores at least 70%.
- **Learning DNA**: nine skills. Speaking, Listening, Reading, Writing, Vocabulary, Grammar, Tones, Memory and Reaction Speed are all updated from graded activity.
- **Companion**: the permanent main companion reacts to graded results, and each species voices those reactions in its own way. The **Daily Voice Companion** is a separate, session-only partner that speaks only Chinese. It uses Google Gemini when a key is configured and a deterministic offline mode otherwise.

## Stack

- Frontend: React + Vite (`frontend/`), i18n in EN / RU / TG / ZH
- Backend: FastAPI + SQLAlchemy + Alembic (`backend/`), JWT auth, Google Sign-In
- Database: PostgreSQL
- Deploy: GitHub Actions → server script → Docker (nginx serves the SPA and proxies `/api` and `/static`)

## Local development

```bash
# backend
cp backend/.env.example backend/.env      # set DATABASE_URL, JWT_SECRET, GOOGLE_CLIENT_ID, optional GEMINI_API_KEY
python -m venv .venv && .venv/Scripts/pip install -r backend/requirements.txt   # Windows path; use .venv/bin on macOS/Linux
cd backend && ../.venv/Scripts/python -m uvicorn app.main:app --reload --port 8000

# frontend
cp frontend/.env.example frontend/.env    # VITE_GOOGLE_CLIENT_ID (same client id as the backend)
cd frontend && npm install && npm run dev # http://localhost:5173, /api is proxied to :8000
```

On startup the API runs `alembic upgrade head` and then an insert-only content seed. Together these give any database the full curriculum. The seed never touches user data. Point local development at a local database, never at production.

Or with Docker: `cp .env.example .env && docker compose up --build`.

## Accounts, Google Sign-In and admin

- Google sign-in resolves an account in this order: Google `sub` (stored in `users.google_sub`), then the verified email (case-insensitive), then a new account. If an email is already linked to a different Google account, sign-in is refused, so no duplicate account is created silently.
- Admin rights come only from the backend. A Google-**verified** email listed in `ADMIN_EMAILS` (backend setting, defaults to the project owner) is granted `is_admin` on sign-in. Password registration can never grant admin, and admin status is never accepted from the client.
- Local and production are separate databases, so the same person has separate progress in each.

## Curriculum data

`backend/app/seed_content/curriculum.json.gz` holds the curated vocabulary, grammar, lessons and translations. Rows are keyed by natural keys (level + word, slug, code) rather than database ids. After curating content in a database, regenerate the file with:

```bash
cd backend && python scripts/export_curriculum_snapshot.py
```

Hanzi and stroke data ship through the Alembic migration `06e70a177b1d`.

## Tests

```bash
cd backend
python tests/smoke_test.py              # CRUD + authorization (401/403/ownership)
python tests/google_auth_test.py        # identity chain, account linking, admin allowlist
python tests/practice_test.py           # server-graded practice, review, lesson completion, DNA
python tests/curriculum_parity_test.py  # fresh DB gets the full curriculum, idempotently
python tests/duel_test.py               # real 1-vs-1 duels: lifecycle, per-player clocks, scoring, authorization
python tests/duel_migration_test.py     # legacy duels survive the real-duel migration
python tests/admin_dashboard_test.py
PYTHONPATH=. python tests/phase2_boot_test.py
# admin_users_test.py runs against a live API (default http://127.0.0.1:8001) on a throwaway database

cd ../frontend
npm run build
python scripts/check_i18n_keys.py       # every used translation key exists in en/ru/tg/zh
```
