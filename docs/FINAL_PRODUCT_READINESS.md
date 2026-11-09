# ChineseVerse — product readiness

State of branch `fix/auth-unverified-email-linking` on 2026-11-08, after two
audit-and-fix phases. Every result below was checked in this environment
(tests, a local stack on PostgreSQL 18, Chromium and Firefox, the Android
emulator). Details and history: `docs/PROJECT_COMPLETION_PROGRESS.md`.

## Verified

| Area | What was checked | Result |
|---|---|---|
| Backend tests | full pytest | see "Test results" |
| Frontend tests | vitest | 116 passed |
| Build | `vite build` (web) and `--mode mobile` | pass |
| Localization | 2,570 UI keys × EN/RU/TG/ZH; all 11,334 words, 3,000 Hanzi, 111 lessons translated; browser scans for raw keys and English leaks | complete; two leaks found and fixed |
| Pages | every route: EN desktop + phone, RU/TG (paper) and ZH (ink) phone, in Chromium; every route in Firefox | no JS errors, failed API calls, phone overflow or raw keys |
| Authorization | all 172 endpoints introspected | 17 public, all legitimately; user data ownership-checked |
| Passwords | PBKDF2-SHA256 600k rounds, upgrade at sign-in | tested |
| Migrations | empty PostgreSQL → head; models vs schema | 0 differences; guarded by a test |
| Backup | `ops/backup_db.sh` dump + restore-verify | good dump verified; broken dump rejected |
| AI | real Gemini on the local stack while it was overloaded | timeouts no longer stall every message; grammar lessons can be retried |
| Curriculum | pinyin syllables vs characters for every word | 3 bad entries found and fixed (snapshot + migration) |
| Android | release APK: signing SHA-1, install, launch, API, Google sign-in hand-off on the emulator | works up to Google's account picker |
| iOS | Info.plist privacy strings, plugin list, `cap sync ios` | consistent; not compiled |

## External actions only you can do

1. **GitHub secret `SSH_KNOWN_HOSTS`** — required before this branch reaches
   `main`, or deploys stop by design. Value: the contents of `known_hosts.txt`
   at the repo root (key `SHA256:yZipbmzi5rdwFmwradmdyrL1gG9YTF8S7ZJ0p/zFJN8`).
   First confirm that fingerprint in the Hetzner console
   (`ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub`). Needs your GitHub
   and Hetzner accounts.
2. **Back up production before deploying** — this batch has two migrations
   (`b5e1d7a3c962` word fix, `c8a2f4e6b913` example translations; both
   additive or guarded):
   on the server, `bash ops/backup_db.sh` (needs SSH to the server).
3. **Merge and deploy** — a PR to `main`; you asked that this not be done
   without your permission.
4. **Real Android phone** — install the release APK; try microphone answers,
   Chinese speech, offline banner, and "Continue with Google" with a Google
   account (needs a device).
5. **iOS** — build in Xcode on a Mac; an iOS OAuth client and Sign in with
   Apple are needed before Google sign-in can be offered there.

## Known limitations (not defects)

- 15 hand-written grammar lessons serve 16 of 602 topics (14 of HSK 1's 60);
  the rest get an AI lesson on first visit, cached for everyone afterwards;
  when Gemini is down the learner sees the syllabus examples and can retry.
- 1,014 of 11,334 words have an example sentence (HSK 1: 362 of 509).
  584 of them are translated: 495 taken from the stories and case files,
  89 written for HSK 1 and checked by `seed_vocab_authored_examples.py`.
- Needs a native speaker: the Russian and Tajik of the 6 lessons written in
  phases 3–4 and the 178 draft example translations
  (`scripts/export_translation_review.py` lists the drafts).
- The Content-Security-Policy is report-only until checked on the live site.
- React Router 6 has two moderate advisories that don't apply to this app;
  the fix needs a v7 migration.

## Readiness

| Area | % |
|---|---|
| Backend / API | 96 |
| Database & backups | 95 |
| Security | 92 |
| Web frontend | 94 |
| Localization | 96 |
| Learning content | 88 |
| Android | 80 |
| iOS | 30 |
| Deployment | 82 |

## Test results

End of phase 4: backend **1142 passed, 0 failed** (full run); vitest 116
passed; build and i18n (2,570 keys) pass.

End of phase 3: backend **1138 passed, 1 failed** on the full run; the one
failure was a test that indexed a word's translations without their field
(a word now also has an example translation) — fixed to compare meanings
only, its module then 13 passed. Vitest 116 passed, build and i18n pass,
PostgreSQL migrations to head with 0 drift.

End of phase 2, on the committed branch:

- Backend pytest: **1133 passed, 0 failed** (SQLite; includes migration,
  schema-drift and whole-snapshot pinyin checks).
- Frontend vitest: **116 passed, 0 failed**.
- `vite build` passes; i18n check 2,570 keys × 4 locales, 0 missing.
- PostgreSQL 18 scratch database: all migrations to head, 0 model drift.
- Android `assembleRelease` passes.
