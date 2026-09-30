---
name: chineseverse
description: Project rules for working on ChineseVerse (FastAPI + SQLAlchemy/Alembic + PostgreSQL backend, React/Vite frontend with EN/RU/TG/ZH i18n, HSK 3.0 curriculum, server-graded practice, Learning DNA, companions, Google Sign-In/JWT, Docker deploy via GitHub Actions). Use for any change, fix, feature, test, migration or review in this repository, and for committing/pushing that work.
---

# ChineseVerse — project rules

These rules describe the real repository. Read the files named here before changing them, and follow the patterns already in place.

## 1. Architecture and technologies

```
backend/                 FastAPI app (Python 3.12 in Docker; local .venv at repo root)
  app/main.py            lifespan: alembic upgrade head -> seed_all(db); registers every router
  app/config.py          pydantic-settings Settings (reads backend/.env)
  app/database.py        engine, SessionLocal (autoflush=False!), Base, get_db
  app/models.py          all SQLAlchemy models (one file)
  app/schemas.py         all Pydantic request/response models (one file)
  app/deps.py            get_current_user, require_admin, get_user_or_none, get_locale (X-Locale)
  app/security.py        PBKDF2 password hashing, JWT (PyJWT, HS256, sub = user id)
  app/crud.py            get_or_404, apply_updates, commit_or_409, delete_user_cascade_safe
  app/routers/*.py       one router per area, prefix /api/<area>
  app/services/*.py      shared logic: practice, srs, dna, gamification, activity,
                         curriculum, localization, hsk_band, ai_client, voice_eval
  app/seed*.py           idempotent content seed run on every startup
  app/seed_content/curriculum.json.gz   committed curriculum snapshot (natural keys)
  alembic/versions/      migrations; alembic/seed_data/ holds the Hanzi dataset
  scripts/               one-off/maintenance scripts (export_curriculum_snapshot.py, ...)
  tests/                 standalone test scripts (no pytest)
frontend/                React 18 + Vite 5, react-router-dom 6, i18next, animejs, framer-motion, hanzi-writer
  src/api.js             the only HTTP client (fetch, Bearer token, X-Locale header)
  src/App.jsx            routes, RequireAuth / RequireAdmin, AuthContext provider, /me revalidation on boot
  src/context/DashboardContext.jsx   one shared GET /api/dashboard per navigation (+ refresh())
  src/hooks/useApi.js    {data, setData, error, setError, reload}; refetches on language change
  src/components/        Layout (Sidebar + Topbar), ui.jsx (Bar, Ring, RingHero, Empty, Loading,
                         Celebration, ...), AnimalAvatar, UserAvatar, CompanionReaction, Icon, ...
  src/pages/             one component per route
  src/locales/{en,ru,tg,zh}.json    UI strings (2-space indent, CRLF)
  src/index.css          all styles; theme tokens (--accent, --good, --bad, --surface-2, ...)
  nginx.conf             serves the SPA, proxies /api/ and /static/ to backend:8000
docker-compose.yml       postgres:16 + backend + frontend (local Docker)
.github/workflows/deploy.yml   push to main -> SSH -> ~/deploy_chineseverse.sh on the server
```

Production is https://chineseverse.qobus.tj/ and has real users.

The core learning loop is: HSK level → lesson → vocabulary, Hanzi and grammar → practice (graded by the server) → result → companion reaction → progress, Learning DNA and XP → review.

## 2. Backend rules

- **New endpoints** go in the matching `app/routers/<area>.py`. Use `APIRouter(prefix="/api/<area>", tags=[...])`. If you create a new router, register it in both the import list and the `for module in (...)` tuple in `app/main.py`. Order matters there: `social` must stay before `users`.
- **Dependencies:** `db: Session = Depends(get_db)`, `user: models.User = Depends(get_current_user)` and `locale: str = Depends(get_locale)`. Admin-only routes use `Depends(require_admin)`.
- **Schemas:** request and response models go in `app/schemas.py`. A small router-local `BaseModel` is acceptable, and `vocab.py`, `hanzi.py`, `practice.py` and `grammar.py` already do this. Never accept `is_admin`, `user_id`-as-authority, XP or mastery from a request body.
- **Shared logic** belongs in `app/services/`. Routers stay thin. Reuse the existing helpers instead of writing new ones:
  - `services.srs.apply_srs(rec, correct, user, delta, counter)` is the only spaced-repetition update.
  - `services.dna.bump_skill(user, code, delta)` updates a DNA skill. Call `gamification.ensure_user_skills` first. The skill codes are speaking, listening, reading, writing, vocabulary, grammar, tones, memory and reaction_speed.
  - `gamification.record_mistake` and `reinforce_mistake`, `progress_quests`, `progress_missions`, `check_achievements` and `touch_streak`.
  - `activity.log_activity(db, user, action_type)`. When you add a new action type, also add its weight to `ACTION_WEIGHTS` and its section to `SECTION_LABELS`.
  - `practice.lesson_items(db, lesson)` returns the words and grammar a lesson teaches.
- **Localized DB content:** call `load_translations(db, content_type, keys, locale)` and then `tr(translations, key, field, fallback)`. Only human-language fields are translated, such as meanings, titles and descriptions. Chinese text, pinyin and code identifiers are never translated.
- **HSK 7/8/9** are one shared advanced band: a single `HSKLevel` row with `level=7` and `is_advanced_band=True`. Always filter through `services.hsk_band.resolve_level_filter(db, model, id_field, hsk_level)`, and never assume that a row exists for levels 8 or 9. Never invent separate official lists for levels 7, 8 and 9.
- **Errors:** raise `HTTPException` with a string `detail`. The frontend shows `detail` directly. Use 401 for a missing or invalid token and 403 for an authenticated user who lacks permission. Use 404 for a missing row, and also for another user's row so that ids don't leak. Use 409 for conflicts (`crud.commit_or_409`) and 422 for validation errors.
- **Sessions:** `SessionLocal` has `autoflush=False`. Call `db.flush()` before querying rows you added earlier in the same session. This has caused real seed bugs.
- **JSON columns:** reassign a new list or dict so SQLAlchemy marks the column dirty (see `answers` in `services/practice.py`).
- **AI:** go through `app/services/ai_client.py` only. Every AI function must have a deterministic offline fallback. AI failures must degrade to offline behaviour, never to a 500. Scores that feed Learning DNA must never use `random`.
- **Comments:** comments explain *why*, often with the history of a bug. Match that density and tone, and don't strip existing explanatory comments.

## 3. Frontend rules

- **HTTP:** all calls go through `api.get/post/put/patch/del/upload` from `src/api.js`, with paths relative to `/api`. Never call `fetch` directly and never hardcode a host.
- **Page shape:** wrap each page in `<Layout>`. Every page that depends on the API needs three states:
  - error: `if (error) return <Layout><Empty>{error}</Empty></Layout>;`
  - loading: `if (!data) return <Layout><Loading /></Layout>;`
  - a real empty state, which must never be shown while a request is still loading.
- **Data loading:** use `useApi(path)` for a simple GET. Use `useDashboard()` to read `dashboard`, and call `refresh()` after an action that changes XP, streak, companion or review count. Don't fetch `/dashboard` again separately.
- **Routes:** add new routes in `src/App.jsx`, wrapped in `<RequireAuth>` or `<RequireAdmin>`. Add navigation entries to both `GROUPS` in `components/Sidebar.jsx` and `NAV_INDEX` in `components/Topbar.jsx`, which is also used by search.
- **Admin:** visibility in the frontend only decides what the UI shows. `user.is_admin` always comes from the backend (`/me`, `/auth/*`), and the frontend must never set or assume it.
- **Avatars:** the user's avatar and the companion are two different things.
  - The user's avatar is `<UserAvatar url={profile.avatar_url} name={username} />`, which falls back to the user's initial.
  - The companion is `<AnimalAvatar slug=... state=... />`, where `state` is one of idle, happy, excited, thinking, confused, correct, wrong, celebrating, encouraging, speaking or listening.
  - Never use the companion image as a fallback for the user's avatar.
- **Companions:** the permanent companion is `user.animal_id` / `dashboard.animal`. The Daily Voice Companion is chosen for one session only and must never write `animal_id`. Companion reactions come from graded results: render `<CompanionReaction animal reaction context />` with the `reaction` object the API returns. Reactions must never shame the learner.
- **Chinese audio:** use `speakChinese(text, {onStart, onEnd})` from `src/zhSpeech.js`.
- **i18n:**
  - Every visible string goes through `t("section.key")`.
  - Add each new key to all four files: en, ru, tg and zh.
  - Keep the files' 2-space indent and CRLF line endings; `frontend/scripts/add_practice_i18n.py` shows the safe way to do this.
  - Plurals use i18next `_one`, `_few`, `_many` and `_other` suffixes.
  - Run `python frontend/scripts/check_i18n_keys.py` after any change to keys.
  - Pages that show backend content must refetch when `i18n.language` changes. `useApi` does this automatically.
- **Styling:**
  - Put styles in `src/index.css` using the existing classes: card, btn, btn.small, btn.primary, btn.ghost, badge, badge.good, badge.bad, badge.accent, row, row.spread, grid, grid-2, grid.cards, sub, h1, h2.
  - Use theme tokens rather than raw colours, because both the ink (dark) and paper (light) themes must work.
  - Layouts must work on phone, tablet and desktop. Add an `@media (max-width: …)` rule for anything wider than one column.
- **Motion:** `Layout`'s PageReveal animates page content. Sections with their own entrance animation opt out with `data-self-animate`. Respect `prefersReducedMotion()`.

## 4. Database and migration rules

- PostgreSQL is used in development and production. Tests use a throwaway SQLite database, so migrations must work on both. Use `op.batch_alter_table` for column changes.
- Every schema change needs a new file in `backend/alembic/versions/`:
  - use a new revision id, with `down_revision` set to the current head;
  - give it a docstring explaining why the change is needed;
  - update the model in `app/models.py` to match.
- Migrations run automatically at startup. Never edit an old migration that has already been applied.
- Data migrations and seeds must be insert-only and idempotent. Never overwrite rows an admin may have edited. Never touch user progress tables (`user_vocabulary`, `user_hanzi`, `user_grammar`, `progress`, `practice_sessions`, `learning_mistakes`, `user_skills`, `activity_events`, ...).
- **Content changes** must reach every database, not just the one in front of you:
  - add small hand-written content to the `seed_*.py` data;
  - regenerate the curated curriculum with `python scripts/export_curriculum_snapshot.py` and commit `app/seed_content/curriculum.json.gz`;
  - keys in that snapshot are natural keys (level + word, slug, code), never database ids, because ids differ between databases.
- New user-owned tables need an FK to `users.id` and either a `cascade="all, delete-orphan"` relationship on `User` or handling in `crud.delete_user_cascade_safe`. Otherwise deleting that user from Admin → Users fails.
- **Real data only:**
  - Never add fake users, demo accounts or fake progress.
  - Never add randomness to anything stored as progress or DNA.
  - Content seed data is fine.
- **Production database:**
  - Never drop, reset or bulk-delete it, and never run destructive SQL against it.
  - Never point local development at the production database.

## 5. API integration rules

- The frontend always calls same-origin `/api/...`. In development, Vite proxies `/api` and `/static` to `VITE_API_PROXY_TARGET` (default `http://127.0.0.1:8000`). In production, nginx proxies them to `backend:8000`.
- `api.js` attaches `Authorization: Bearer <token>` and `X-Locale`, clears the session on a 401, and turns `detail` into `Error.message`. Keep the backend's error `detail` values human-readable.
- **Practice and review** (`/api/practice/sessions`, `/answer`, `/complete`, `/review/summary`):
  - the server generates the questions and stores `item_id` and `option_ids`;
  - the client sends only `choice_id` and `response_ms`;
  - grading, mastery, XP, mistakes, DNA and lesson completion (score ≥ 70%) are all decided by the server;
  - never add an endpoint that lets the client declare an answer correct or a lesson complete.
- `/api/progress` is always scoped to the signed-in user. Only admins may read `/api/progress/user/{id}`.
- **Adding a field:** add it to the backend response schema first, then consume it in the frontend. Keep existing response shapes backward compatible.

## 6. Authentication and security rules

- **JWT:** `security.create_access_token(user.id)` with a 7-day expiry. The frontend stores the token in `localStorage` under `linguaverse_token` and `linguaverse_user`, and revalidates it with `GET /api/me` on boot.
- **Google Sign-In** (`POST /api/auth/google`) verifies the ID token against `GOOGLE_CLIENT_ID` and resolves the account in this order:
  1. `users.google_sub`
  2. the verified email, matched case-insensitively (`_find_by_email`); this links an existing account
  3. otherwise, a new account
  - It refuses with 409 to re-bind an account that is already linked to a different Google account.
  - Don't weaken this chain, because it prevents duplicate or hijacked accounts.
- **Admin:**
  - `is_admin` is granted only when a Google-verified email is in `settings.admin_emails` (`ADMIN_EMAILS`), or by a deliberate change in the database.
  - It is never granted by password registration or by any request payload.
  - Every `/api/admin/*` route and every content-write route (lessons, animals, `POST /api/users`) uses `require_admin`.
  - Admins cannot delete their own account.
- Inactive users get a 401 or 403. Login and Google sign-in both check `is_active`.
- When you add a route, decide deliberately whether it is public (reading content), for any authenticated user (their own data only), or admin-only. Any route that writes to a user must use `get_current_user` and never a `user_id` from the request.
- Secrets live only in `backend/.env`, `frontend/.env` and the root `.env`, all of which are gitignored. Keep the `*.env.example` files free of real values.

## 7. Testing and verification

Backend tests are standalone scripts with no pytest. Each one sets `DATABASE_URL` to a temporary SQLite database before importing `app.main`, then drives it with `TestClient`, and prints `[PASS] …` or `ALL … PASSED`. Run them from `backend/` with the repo's venv:

```
..\.venv\Scripts\python.exe tests\smoke_test.py              # CRUD + 401/403/ownership
..\.venv\Scripts\python.exe tests\google_auth_test.py        # identity chain + admin allowlist
..\.venv\Scripts\python.exe tests\practice_test.py           # graded practice/review/lessons/DNA
..\.venv\Scripts\python.exe tests\curriculum_parity_test.py  # fresh DB gets full curriculum
..\.venv\Scripts\python.exe tests\admin_dashboard_test.py
$env:PYTHONPATH="."; ..\.venv\Scripts\python.exe tests\phase2_boot_test.py
```

- `tests/admin_users_test.py` needs a live API on `http://127.0.0.1:8001` running against a throwaway SQLite database (`DATABASE_URL=sqlite:///...`). Never run it against the development or production database.
- On this Windows machine, anything that imports psycopg (the real Postgres) must run from PowerShell. From Git Bash, libpq fails to load. SQLite-based tests work from either shell.
- **Frontend:** `cd frontend && npm run build` must pass. Also run `python scripts/check_i18n_keys.py`. There is no frontend test runner and no ESLint, so check for identifiers you removed or no longer use.
- Add or extend a test script for each new backend behaviour, especially anything involving authorization, grading or data integrity.
- The dev servers are usually running: uvicorn with `--reload` on :8000 and Vite on :5173. Keep them running; the reload also applies new migrations to the local database. Confirm with `GET http://localhost:8000/health`.
- After a push to `main`, check that the deploy succeeded:
  - list the workflow runs at `https://api.github.com/repos/zargulak11-hash/Chineseverse/actions/runs?per_page=1`;
  - confirm `https://chineseverse.qobus.tj/` responds;
  - use only read-only GET requests against production, and never create accounts there.

## 8. Existing conventions and patterns

- **Python:** type hints; `from __future__ import annotations` in services; module and function docstrings that explain the reason for the code; `datetime.utcnow()` for timestamps; `db.query(...)` style (SQLAlchemy 2.0 installed, legacy Query API used throughout).
- **Idempotency:** every seed or import function checks for an existing row before inserting.
- **Frontend:** function components and hooks; 2-space indent; double quotes; semicolons; inline `style={{…}}` for one-off spacing and CSS classes for anything reused; `t()` everywhere; components import siblings with explicit `.jsx` extensions.
- **Naming:** the old project name "LinguaVerse" or "linguaverse" still appears in identifiers, including localStorage keys, the default database name and the npm package name. Don't rename these, because renaming them would log users out and break environments.
- **Commit messages:** conventional style, `type(scope): summary`, for example `fix(auth): …`, `feat(learning): …` or `docs: …`. The body explains the root cause and what changed.

## 9. Adding a new feature

1. Read the relevant router, service, page and tests first, then trace the full path: model → schema → router → service → `api.js` call → page → i18n.
2. Connect the feature to the learning loop through real data: mastery via `apply_srs`, mistakes, DNA via `bump_skill`, activity, XP and quests. Nothing should look complete if the backend doesn't actually do it.
3. If the feature adds a user-owned table, add a migration and a model, plus user-deletion cascade handling.
4. Add authorization, validation, and a clear `detail` on every error path.
5. Build the frontend page with loading, empty and error states; a mobile layout; strings in all four locales; and dashboard `refresh()` where needed.
6. Add or extend tests. Run the relevant backend tests, `npm run build` and the i18n check.
7. Commit and push (section 11).

## 10. Avoiding unnecessary changes

- Change only what the task needs. Don't refactor, rename, reformat or "clean up" unrelated code, locale files, CSS or comments.
- Don't rewrite whole files when a targeted edit will do. Rewriting a locale JSON file with a different indent turns a small change into a thousand-line diff.
- Don't change the architecture. That means no new state library, CSS framework, HTTP client, ORM style or test framework, unless the user explicitly asks for one.
- Don't add dependencies without a clear need.
- Keep decisions that earlier commits documented as intentional:
  - the admin Users list shows each user's companion;
  - Hanzi detail has "know it" self-check buttons alongside graded practice;
  - HSK 7–9 is one shared band.
  If one of these seems wrong, raise it with the user rather than changing it.
- Leave unrelated files alone, including anything under `.claude/`, local logs and the `backend/data_sources/` raw data, which is gitignored.

## 11. Git workflow (mandatory after every completed task)

Never finish a completed task without committing and pushing it. For every task:

1. Run `git status` and `git diff`, and review every change. Stage only the files that belong to this task, never with a blind `git add -A` that could pick up `.claude/` settings, logs or `.env` files.
2. Run the relevant tests and checks from section 7, and fix any failures before committing.
3. Scan the staged diff for secrets: `.env` files, passwords, API keys (`sk-…`), JWT secrets, OAuth client secrets, access tokens, SSH keys, database URLs with credentials. If anything like that is staged, unstage it and never commit it.
4. Verify the author identity without changing it:
   `git config user.name` must print `Zarina` and `git config user.email` must print `zargulak11@gmail.com`.
5. Commit with a clear, descriptive message (section 8 style).
   - Don't add any `Co-Authored-By: Claude`, Anthropic, OpenAI or other AI attribution trailer.
   - Use one logical feature per commit: no tiny meaningless commits, and no single commit mixing unrelated features.
6. Push to the current remote branch with `git push origin <current-branch>`; this is normally `main`, which triggers the production deploy.
7. Check that `git rev-parse HEAD` equals `git rev-parse origin/<branch>` and that `git status` is clean for the task's files.

Never force-push, never `git reset --hard` or delete branches, commits or other people's work, and never rewrite published history, unless the user explicitly asks. If a push is rejected, fetch and integrate the remote changes; don't overwrite them.
