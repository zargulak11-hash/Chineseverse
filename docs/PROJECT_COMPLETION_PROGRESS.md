# Project completion audit — progress record

Session of 2026-11-08 on branch `fix/auth-unverified-email-linking`.
Everything below was checked against the code and a running local stack,
not taken from earlier reports.

## State of the repository

- Branch `fix/auth-unverified-email-linking` = `origin/main`'s ancestor
  `d473168` + 9 earlier commits (Android Google sign-in, verified-email
  linking, security headers, CI checks) + 4 commits from this session.
  Nothing is merged to `main`; nothing was deployed.
- `origin/main` has one commit this branch lacks: `e409fa2`
  (Hanzi writing dialog scrolls). Merge or rebase before opening a PR.
- Left untouched on purpose (the owner's uncommitted work):
  - `.github/workflows/deploy.yml` — pins the server's SSH host key
    instead of `StrictHostKeyChecking=no`. Correct, but once on `main`
    every deploy stops until the repository secret `SSH_KNOWN_HOSTS`
    exists. Add the secret first, then commit it.
  - `docs/DEMO_DAY_STUDY_GUIDE.md` (untracked).
- Backups at the repo root (`*.bundle`, `*.dump`, `known_hosts.txt`) are
  ignored by git and were not touched; neither was `stash@{0}`.

## What was checked, and the result

| Area | How | Result |
|---|---|---|
| Backend tests | full pytest, SQLite | 1119 passed before changes; 1129 passed, 0 failed after (warnings 1118 → 6) |
| Frontend tests | vitest | 116 passed (15 files) |
| Production build | `vite build` | passes; entry chunk 648 kB (216 kB gzip), all 54 pages lazy |
| i18n keys | `check_i18n_keys.py` | 2569 keys × 4 locales, 0 missing |
| Migrations | empty PostgreSQL 18 scratch DB → head, then model diff | upgrade OK; 4 cosmetic drifts (below); scratch DB dropped |
| Authorization | introspected all 172 routes | 17 public, all legitimately (auth, health, catalogue); every by-id lookup of user data checks ownership (404) |
| Auth | read auth/deps/security | sound: verified-email linking, session revocation, constant-time compare, login/sign-up throttles |
| Pages | Playwright, every route × (EN desktop, EN phone, RU paper phone, TG paper phone, ZH ink phone) | 255 + 20 loads: no JS errors, no failed API calls, no phone overflow, no raw i18n keys, no English UI strings in RU/TG/ZH. Detectors proven by injecting each defect |
| Backend content language | scan of 25 content pages in RU/TG | one leak (Mistakes) — fixed |
| AI | real Gemini roleplay turns on the local stack | works, but ~53 s per turn while the primary model hangs — fixed |
| Android | `vite build --mode mobile`, `cap sync`, `gradlew assembleDebug` | debug APK builds (9.1 MB); config reviewed (HTTPS only, no backup, signing outside the repo, wrapper 8.14.3) |

## Fixed in this session (commits)

1. `c4861fb` fix(security): PBKDF2 600k rounds (was 100k, OWASP minimum is
   600k); old hashes upgraded at the next successful sign-in without
   ending sessions; timing kept even for not-yet-upgraded accounts.
2. `e07a113` fix(ai): a timed-out Gemini model cools down 10 min; one call
   finishes within ~55 s so nginx's 60 s never turns it into a 504.
3. `e558f93` fix(i18n): missed conversation lines ("Say: …") showed in
   English on Mistakes in every language, and as a large "Chinese"
   headword.
4. `9def706` test: two tests that failed under load / by chance
   (SRS clock, pinyin distractor choice) made deterministic.

Files changed: `backend/app/config.py`, `backend/app/security.py`,
`backend/app/routers/auth.py`, `backend/app/routers/mistakes.py`,
`backend/app/services/ai_client.py`, `backend/app/services/localization.py`,
`backend/tests/conftest.py`, `backend/tests/test_password_hashing.py` (new),
`backend/tests/test_assistant_locale.py`, `backend/tests/test_locale_content.py`,
`backend/tests/test_pinyin_course.py`, `backend/tests/test_srs.py`,
`frontend/src/mistakes.js`, `frontend/src/mistakes.test.js` (new), this file.

## Known, not fixed (low impact, deliberate)

- Model/schema drift: `activity_events.created_at` is nullable in the
  database but not in the model; redundant indexes declared on three
  primary keys (`activity_events`, `content_translations`, `follows`).
  Harmless; not worth a production migration on its own.
- Entry bundle could be split further (i18next + English strings); gain
  is small.
- Gemini itself was overloaded during testing (503s, timeouts). Roleplay
  has no offline mode by design and asks the learner to resend.

## Not verified (needs a person, a device or production)

- A real Android phone (only a build; the emulator was not run this
  session). Microphone, speech recognition and Chinese TTS on a device.
- Native Google sign-in end to end (needs the Android OAuth client in
  Google Cloud and a phone with a Google account).
- iOS (no macOS here).
- Offline behaviour of the app.
- Production: no deploy, no production migration, no production data read.

## Readiness (honest estimate)

| Area | % | Why not higher |
|---|---|---|
| Backend / API | 95 | drift items; AI depends on Gemini's availability |
| Security | 90 | CSP still report-only; SSH host pinning not committed |
| Frontend web | 93 | not tested on real phones/browsers other than Chromium |
| Localization | 95 | heuristic scans can't prove every backend string |
| Learning features | 90 | verified by tests and page loads; microphone features not exercised |
| Android | 70 | builds; not run on a device this session; Google sign-in blocked on Cloud setup |
| iOS | 20 | project exists; never built |
| Deployment | 80 | CI green path exists; no DB backup in the deploy script |

## How to continue

1. Merge `origin/main` (`e409fa2`) into this branch, open a PR, let CI run.
2. Add the `SSH_KNOWN_HOSTS` secret, then commit `deploy.yml`.
3. Before deploying: back up the production DB (no migration in this
   batch, but the deploy script never backs up).
4. Install the debug or release APK on a real phone; test microphone,
   TTS, sign-in, offline banner.
5. Local stack used here: backend `uvicorn` on :8000 with `SMTP_HOST=" "`
   (the local `.env` sends real email), Vite on :5173, probe account
   `audit1c46a6` (local DB only).
