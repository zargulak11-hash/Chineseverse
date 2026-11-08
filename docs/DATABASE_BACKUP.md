# Database backup and restore

Production runs PostgreSQL in the `postgres` service of `docker-compose.yml`
on the server (`~/Chineseverse`). The deploy script makes **no** backup, and
migrations run on their own when the backend container starts, so a backup
must be taken by hand before any deploy that carries a migration (a file in
`backend/alembic/versions/` that is new since the last deploy).

## Take a backup (and prove it restores)

On the server, from `~/Chineseverse`:

```bash
bash ops/backup_db.sh
```

It writes `~/backups/chineseverse-<UTC time>-at-<git rev>.dump`
(custom format, mode 600), then restores that file into a scratch database
`cv_restore_check`, compares the row count of every table with the live
database, and drops the scratch database. Expected last line:

```
OK: restored 50 tables, <n> users
```

Anything else (`FAILED: …`, exit code ≠ 0) means the file is not a usable
backup — do not deploy until a backup verifies.

- The live database is only read (`pg_dump` takes a consistent snapshot).
- `cv_restore_check` is the only database the script creates or drops.
- Old backups are kept. `KEEP=14 bash ops/backup_db.sh` keeps the newest 14
  of its own files and deletes older ones — only if you ask for it.
- Check an existing file again: `bash ops/backup_db.sh --verify FILE`.
- A line like `progress: backup 120, live 123 (written since the dump)` is
  normal on a live site.

Copy important backups off the server too (the server's disk is a single
point of failure), e.g. from your computer:
`scp chineseverse-prod:backups/<file>.dump .` and keep it private: it holds
every account's data.

Tested 2026-11-08 against a local PostgreSQL 18 copy (`PG_EXEC=""` mode):
a good dump verified (50 tables, 60 users); a truncated dump was rejected
with exit 1 and the scratch database was removed.

## Restore (manual, deliberate)

Restoring replaces what learners did after the backup. Never restore over
the live database in place. Restore into a new database, check it, then
switch to it:

```bash
cd ~/Chineseverse
docker compose stop backend                       # no writes during the switch
docker compose exec -T postgres createdb -U "$POSTGRES_USER" chineseverse_restored </dev/null
docker compose exec -T postgres pg_restore -U "$POSTGRES_USER" -d chineseverse_restored \
    --no-owner --exit-on-error < ~/backups/<file>.dump
docker compose exec -T postgres psql -U "$POSTGRES_USER" -d chineseverse_restored \
    -c "select count(*) from users" </dev/null    # looks right?
```

Then point the backend at it: set `POSTGRES_DB=chineseverse_restored` in the
root `.env` (the compose file builds `DATABASE_URL` from it) and
`docker compose up -d backend`. The old database stays untouched until you
decide to drop it. (`$POSTGRES_USER` above is the value from the root `.env`.)

## Locally

The same script runs against a local server:

```bash
PG_EXEC="" DB_USER=postgres DB_NAME=LinguaVerse PGHOST=localhost \
  PGPASSWORD=… BACKUP_DIR=/some/dir bash ops/backup_db.sh
```

(the PostgreSQL `bin` directory must be on `PATH`).
