# Project completion audit — progress record

Session of 2026-11-08 on branch `fix/auth-unverified-email-linking`.
Everything below was checked against the code and a running local stack,
not taken from earlier reports.

## State of the repository (updated after phase 2)

- Branch `fix/auth-unverified-email-linking`: `main`'s `d473168` + 9 earlier
  commits + phase 1 (5 commits) + phase 2 (see below). Nothing merged to
  `main`, nothing deployed, production untouched.
- `e409fa2` (Hanzi writing dialog scrolls) from `main` is now on the branch
  (cherry-picked as `5afac92`), so the branch contains all of `main`.
- `.github/workflows/deploy.yml` (SSH host-key pinning) is committed on the
  branch (`7db7ce6`). **Before merging to `main`, add the repository secret
  `SSH_KNOWN_HOSTS`** or every deploy stops (see "External steps").
- `docs/DEMO_DAY_STUDY_GUIDE.md` stays untracked and untouched; backups at
  the repo root and `stash@{0}` were not touched.

## Phase 2 (2026-11-08)

| Item | Result | Commit |
|---|---|---|
| Model ↔ schema drift (4 items) | All four were the models' mistake (DB already NOT NULL; PK indexes declared twice). Model-only fix, no migration. PostgreSQL scratch check now 0 differences; `test_schema_drift.py` fails on the old models and passes now | `f31893a` |
| `e409fa2` from `main` | cherry-picked | `5afac92` |
| deploy.yml / SSH_KNOWN_HOSTS | committed; scanned key `SHA256:yZipbmzi…FJN8` matches the key this PC has trusted since its first connection | `7db7ce6` |
| Backup & restore | `ops/backup_db.sh` + `docs/DATABASE_BACKUP.md`; tested on local PG 18: good dump verified (50 tables, 60 users), truncated dump rejected (exit 1), scratch DB cleaned up | `965a56b` |
| Android release build | `assembleRelease` OK; signer SHA-1 `0dc49b6f…59e4` = the SHA-1 registered for the Android OAuth client (created 2026-10-26); package `tj.qobus.chineseverse` v1.1 (2) | — |
| Android on emulator (Android 16) | release APK installs and launches; login screen loads and shows Google sign-in (providers fetched from production); pressing it initializes the plugin with the release SHA-1 + web client id and opens Credential Manager. No crash | — |
| iOS | no macOS here; `cap sync ios` clean; Info.plist has microphone + speech-recognition reasons; SPM lists the 5 plugins; Google sign-in hidden on iOS by design | — |
| Curriculum audit (11,334 words, 3,000 Hanzi, 602 grammar points, 111 lessons) | translations complete for words, Hanzi, lessons in ru/tg/zh; no lesson empty. **3 HSK 7–9 words had one character's pinyin + meaning** (得意扬扬 "yáng / ocean", 火暴, 无可厚非) — fixed in the snapshot and by migration `b5e1d7a3c962`; whole-snapshot syllable check added | `fa04e4b` |
| Grammar explanations | 572/602 points get an AI lesson on first visit (cached). When Gemini is busy the page said "not available" with no way to retry; a **Try again** button added (4 languages), browser-checked | `b6d4b80` |
| Firefox | sweep over every route: no JS errors, failed API calls, overflow or untranslated text; only "network idle" waits under the dev server | — |
| Tests at end of phase 2 | backend 1133 passed / 0 failed; vitest 116 / 0; build and i18n pass | — |
| Dependencies | npm audit: 2 moderate React Router 6 advisories (SSR hydration; open redirect from user-supplied paths) — neither applies (client-only SPA; no navigation to user-supplied paths). Fix needs the breaking v7; not done | — |

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

## Phase 3 (2026-11-08): learning content

| Item | Result | Commit |
|---|---|---|
| Word example sentences | 430 of 11,334 words had one, none translated. `scripts/seed_vocab_story_examples.py` takes real sentences from the 119 stories and 10 detective cases (written for learners, with en/ru/tg translations): source and every other word at or below the word's level, whole-word match (forward and backward split agree), no polyphonic word or character anywhere (so the curriculum pinyin cannot be wrong), pinyin written word by word with apostrophes (bǎo'ān). **495 words gained a translated example** (189 HSK 1, 118 HSK 2, 68 HSK 3, 49 HSK 4, 28 HSK 5, 13 HSK 6, 30 HSK 7–9). New column `example_translation` (migration `c8a2f4e6b913`), ru/tg as content translations, served by `/api/vocab`, shown on the Vocabulary page. Snapshot diff: exactly 495 examples + 990 translations | `6ad753d` |
| Grammar: 会/能 | hand-written lesson (4 languages, HSK 1–2 words); `"also"` lets it serve the identical syllabus entry 能愿动词：会、能, which had only an AI lesson | `c3b41c0` |
| Grammar: 几/多少 | hand-written lesson (4 languages) | `bd0b0c2` |
| Checks | `test_vocab_story_examples.py` (word present, one pinyin syllable per character, ru/tg present, real source sentence, HSK 1 examples use HSK 1 words, API per language); authored lessons pass `test_authored_content`; browser: Vocabulary and the two lessons in ru/tg/zh on a phone, no AI calls, no overflow; both migrations on PostgreSQL 18, 0 drift | — |

Still missing (content work, not code): examples for ~10,400 words — the
existing corpus is used up (1,201 plain story sentences; more need new
human-written or human-reviewed sentences); hand-written lessons for the
other ~570 syllabus grammar points (12 of 602 now authored).

Phase 2 files: `backend/app/models/users.py`, `backend/app/models/localization.py`,
`backend/tests/test_schema_drift.py` (new), `.github/workflows/deploy.yml`,
`ops/backup_db.sh` (new), `docs/DATABASE_BACKUP.md` (new),
`backend/app/seed_content/curriculum.json.gz`,
`backend/alembic/versions/b5e1d7a3c962_fix_three_band7_word_entries.py` (new),
`backend/tests/test_band7_word_fix_migration.py` (new),
`frontend/src/pages/GrammarTopic.jsx`, `frontend/src/locales/{en,ru,tg,zh}.json`
(one key each), `frontend/src/components/HanziTrace.jsx` + `index.css`
(cherry-pick), `docs/FINAL_PRODUCT_READINESS.md` (new), this file.

## Known, not fixed (deliberate)

- **This batch carries a migration** (`b5e1d7a3c962`, three vocabulary
  rows). Back up first: `bash ops/backup_db.sh` on the server.
- 572 of 602 grammar points rely on an AI lesson generated on first visit
  (then cached for everyone). Pre-generating them needs ~2,300 Gemini calls
  (4 languages) and human review of the output; not done while Gemini was
  overloaded, and generated teaching text should be reviewed before it is
  stored for everyone.
- 10,904 of 11,334 words have no example sentence of their own (lessons and
  grammar carry examples). Writing them is content work, not a code fix.
- React Router 6 → 7 for two moderate advisories that don't apply here.
- Entry bundle 648 kB (216 kB gzip); small gain from further splitting.
- Google Fonts answered in ~11 s from this network; the app loads fonts
  without blocking, so users see system fonts first.

## Not verified (needs a person, a device or production)

- A real Android phone: microphone, speech recognition, Chinese TTS,
  offline banner. (Emulator: install, launch, API, sign-in hand-off only.)
- A complete Google sign-in in the app (needs a phone with a Google account).
- iOS build and run (needs macOS + Xcode).
- Production: no deploy, no production migration, no production data read.

## Readiness (honest estimate, after phase 2)

| Area | % | Why not higher |
|---|---|---|
| Backend / API | 96 | AI features depend on Gemini's availability |
| Database | 95 | backup now scripted and tested; deploy script still doesn't call it |
| Security | 92 | CSP still report-only; host-key secret still to be added |
| Frontend web | 94 | Chromium + Firefox checked; Safari not available |
| Localization | 96 | heuristic scans can't prove every backend string |
| Learning content | 88 | 3 bad entries fixed; grammar explanations and word examples rely on AI / are missing for most items |
| Android | 80 | release build verified incl. signing SHA-1; never run on a real phone |
| iOS | 30 | config checked and synced; never built (no Mac) |
| Deployment | 82 | backup procedure exists; secret and merge pending |

## How to continue

1. Add the `SSH_KNOWN_HOSTS` repository secret (see `docs/FINAL_PRODUCT_READINESS.md`).
2. Open a PR from this branch to `main`; let CI run.
3. On the server before deploying: `bash ops/backup_db.sh` (this batch has a migration).
4. Install the release APK on a real phone; test microphone, TTS, Google sign-in.
5. Local stack used here: backend `uvicorn` on :8000 with `SMTP_HOST=" "`
   (the local `.env` sends real email), Vite on :5173, probe account
   `audit1c46a6` (local DB only).
