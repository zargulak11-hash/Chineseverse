# ChineseVerse

A Chinese learning platform built around the real HSK 3.0 curriculum (levels 1–6 plus the shared 7–9 advanced band), with the interface in English, Russian, Tajik and Chinese. Every lesson, practice answer and review is graded on the server and feeds one learner record in PostgreSQL; that record drives mastery, spaced repetition, the Learning Compass (the nine-skill profile, called Learning DNA in the code) and the companion's reactions.

Production: https://chineseverse.qobus.tj/

## Learning loop

```
HSK level → Lesson → Vocabulary / Hanzi / Grammar → Practice → Result
          → Companion reaction → Progress + Learning Compass → Review → …
```

- **Curriculum**: 11,334 vocabulary items, 3,000 Hanzi with stroke data, about 600 grammar points and 111 lessons. All lessons are translated into Russian, Tajik and Chinese, and the meanings of every word the lessons teach (about 1,100) into Russian and Tajik; other meanings are shown in English. HSK 7–9 is one shared advanced pool, as in the official standard.
- **Lessons and the lesson path**: one current lesson at a time; a lesson is completed only by a practice round scoring at least 70%, and each HSK level ends with a final exam that opens the next level.
- **Practice and review**: the server builds every round, stores the answer key and grades each answer; the client only sends the option it chose. Spaced repetition schedules review; mistakes from practice, duels, voice and Hanzi tracing come back in Review.
- **Character writing**: strokes are traced over real stroke data and checked on the server.
- **Duels**: a real 1-vs-1 between two learners — same server-stored questions, a server-timed clock per player, and the winner decided by the server (correct answers, then score, then time). Answers are serialized with row locks.
- **Learning Compass**: nine skills (speaking, listening, reading, writing, vocabulary, grammar, tones, memory, reaction speed), each moved only by graded activity.
- **Companions**: the permanent companion reacts to graded results. The Daily Voice Companion is a separate, session-only Chinese-speaking partner.

Built on the same engine: HSK roadmap, Chinese Stories (a graded reading library, HSK 1–9), Real Chinese (a city map of everyday scenes), One Sentence lessons, Chinese Internet (adapted real-world texts), Sound World (listening), Detective Mode, Pet Teacher (the learner corrects the companion's grammar), Character DNA and the Vocabulary Ecosystem, missions, daily quests, achievements, follows and notifications, My Chinese Journey (a learner's story built only from their records), and an AI assistant that answers in the selected language.

**AI** (Google Gemini) is optional. Without `GEMINI_API_KEY`, or when the provider fails, every AI feature falls back to a deterministic offline mode and says so; grading never depends on it. The app itself needs a network connection — there is no offline/PWA mode.

## Architecture

```
frontend/  React 18 + Vite SPA, react-router, i18next (EN/RU/TG/ZH)
  src/api.js            the only HTTP client: Bearer token, X-Locale, error localization
  src/pages/            one component per route (48)
  src/components/       shared UI (layout, city map, companion, practice extras, ...)
  src/locales/          en.json, ru.json, tg.json, zh.json
  nginx.conf            serves the SPA in production and proxies /api and /static
backend/   FastAPI + SQLAlchemy 2 + Alembic
  app/main.py           startup: alembic upgrade head, then the idempotent content seed
  app/routers/          one router per area under /api/<area> (36 routers, ~140 endpoints)
  app/services/         the logic: grading, spaced repetition, Learning Compass, lesson path,
                        exams, duels, AI client with offline fallbacks, login throttling, ...
  app/models/           SQLAlchemy models, one module per area, re-exported from app.models
  alembic/versions/     schema and data migrations (31)
  tests/                pytest suite
docker-compose.yml       PostgreSQL 16 + backend + frontend
.github/workflows/       CI and deploy
```

The browser always calls same-origin `/api/...`; Vite proxies it in development and nginx in production.

## Local development

```bash
# backend
cp backend/.env.example backend/.env      # see "Configuration" below
python -m venv .venv && .venv/Scripts/pip install -r backend/requirements-dev.txt   # .venv/bin on macOS/Linux
cd backend && ../.venv/Scripts/python -m uvicorn app.main:app --reload --port 8000

# frontend
cp frontend/.env.example frontend/.env    # VITE_GOOGLE_CLIENT_ID (same client id as the backend)
cd frontend && npm install && npm run dev # http://localhost:5173, /api is proxied to :8000
```

Or with Docker: `cp .env.example .env && docker compose up --build` (frontend on :5173, API on :8000).

Point local development at a local database, never at production.

### Configuration

Backend settings come from `backend/.env` (see `backend/.env.example`; never commit the real file):

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL URL (`postgresql+psycopg://…`) |
| `JWT_SECRET` | signs session tokens — must be a long random value on any server; the API logs an error at startup while it is the placeholder |
| `GOOGLE_CLIENT_ID` | enables Google Sign-In (same value as the frontend's `VITE_GOOGLE_CLIENT_ID`) |
| `ADMIN_EMAILS` | Google-verified emails granted admin on sign-in |
| `AI_PROVIDER`, `GEMINI_API_KEY`, `GEMINI_MODEL` | optional AI; without a key everything runs offline |
| `SMTP_*`, `PUBLIC_APP_URL` | optional notification email; without `SMTP_HOST` notifications are in-app only |
| `TRUSTED_PROXY_HOPS` | reverse proxies in front of the API that append `X-Forwarded-For` (0 direct, 1 behind the compose nginx, 2 behind a host nginx as well); used to find the client address for login throttling |
| `CORS_ORIGINS` | allowed browser origins in development |

### Database and migrations

On every start the API runs `alembic upgrade head` and then an insert-only content seed, so any database — including a brand-new one — ends up with the full curriculum. The seed never touches user data and never overwrites admin edits. Schema changes go in a new file in `backend/alembic/versions/` and the matching model in `backend/app/models/`.

The curated curriculum ships as `backend/app/seed_content/curriculum.json.gz`, keyed by natural keys (level + word, slug, code) rather than database ids. After curating content, regenerate it with `cd backend && python scripts/export_curriculum_snapshot.py`. Hanzi and stroke data ship through the Alembic migration `06e70a177b1d`.

## Accounts and security

- **Passwords** are hashed with salted PBKDF2-SHA256 and compared in constant time. Sessions are signed JWTs (7 days); every request re-checks that the account still exists and is active.
- **Login throttling**: failed password logins are counted per account + address, per account from anywhere, and per address across accounts; past the allowance the API answers 429 for a lock that doubles from 30 s up to 15 minutes. Unknown usernames are treated exactly like real ones, so answers never reveal which accounts exist.
- **Google Sign-In** resolves an account by Google `sub`, then the verified email (case-insensitive), then a new account; an email already linked to a different Google account is refused.
- **Admin** rights come only from the server: a Google-verified email in `ADMIN_EMAILS`, or a deliberate database change. Registration and request payloads can never grant admin.
- **Authorization**: learners only ever read or change their own rows (another learner's practice round, duel, exam attempt or notification is a 404). Grades, XP, mastery and lesson completion are decided by the server, never accepted from the client.
- **AI endpoints** are rate-limited per learner.

## Tests

**Backend** — a pytest suite in `backend/tests/` (about 570 tests). Each test module runs against its own throwaway SQLite database copied from one migrated and seeded template, with SMTP and Gemini switched off whatever `backend/.env` says — no test touches a real database, mail server or AI provider. Tests cover authentication and security (login throttling, tokens, ownership, admin boundaries), the learning loop (practice grading, spaced repetition, lessons, exams, review), every major feature, data integrity (deleting a learner with foreign keys enforced), migrations against older schemas, and that every AI feature degrades to its offline result when the provider fails.

```bash
cd backend
python -m pytest -q                          # everything
python -m pytest -q --cov                    # with branch coverage of app/
python -m pytest -q tests/test_auth_login.py # one area
python -m pytest -q -m migration             # migrations against older schemas
```

**Frontend** — Vitest unit tests for the shared client logic (`src/api.js`, `src/apiErrors.js`): session and locale headers, signing out on an expired session, translated server errors in all four languages.

```bash
cd frontend
npm test
npm run build
python scripts/check_i18n_keys.py            # every used translation key exists in en/ru/tg/zh
```

## CI and deployment

`.github/workflows/deploy.yml` runs on every push and pull request:

1. **Backend tests** — the pytest suite on Python 3.12 with branch coverage; the job fails below 85%.
2. **PostgreSQL migrations** — a fresh PostgreSQL 16 database is migrated to head, the newest migration is re-applied, and the API boots on it and serves seeded content.
3. **Frontend** — `npm ci`, the Vitest unit tests, `vite build` and the i18n key check on Node 20.

Only when all three pass does a push to `main` deploy: the workflow connects to the server over SSH and runs its deploy script, which rebuilds the Docker stack (nginx serves the SPA and proxies `/api` and `/static` to the API).

## Languages

The whole interface is available in English, Russian, Tajik and Chinese (`frontend/src/locales/`). Database content (meanings, lesson text, missions, …) is translated through one `content_translations` table and served in the learner's language via the `X-Locale` header. API error messages a learner can meet are shown in their language (`frontend/src/apiErrors.js`). Chinese text and pinyin are never translated.
