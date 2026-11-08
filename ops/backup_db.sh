#!/usr/bin/env bash
# Back up the ChineseVerse PostgreSQL database and prove the backup restores.
#
#   ops/backup_db.sh                 dump, then verify by restoring it
#   ops/backup_db.sh --verify FILE   only verify an existing dump
#
# Run on the server from ~/Chineseverse (next to docker-compose.yml) BEFORE
# every deploy that carries a migration: the deploy script makes no backup,
# and migrations run by themselves when the backend starts.
#
# What it does to databases: reads the live one (pg_dump takes a consistent
# snapshot; nothing is written to it), and creates, fills, compares and drops
# ONE scratch database, cv_restore_check. It never restores over the live
# database -- that is a manual decision (docs/DATABASE_BACKUP.md).
#
# Settings (environment):
#   BACKUP_DIR  where dumps go                     (default ~/backups)
#   KEEP        keep only the newest N dumps here  (default: keep all)
#   PG_EXEC     how to run the PostgreSQL tools    (default: the compose
#               service, "docker compose exec -T postgres"; empty = run the
#               tools directly, e.g. against a local server)
#   DB_USER / DB_NAME  default to the container's POSTGRES_USER/POSTGRES_DB
set -euo pipefail

CHECK_DB=cv_restore_check
BACKUP_DIR=${BACKUP_DIR:-$HOME/backups}
PG_EXEC=${PG_EXEC-docker compose exec -T postgres}

# `docker compose exec -T` reads stdin; inside a `ssh host 'bash -s' <<EOF`
# it swallowed the rest of the script. Every call gets its own stdin.
run() {  # run TOOL ARGS... with stdin closed
  if [ -n "$PG_EXEC" ]; then $PG_EXEC "$@" </dev/null; else "$@" </dev/null; fi
}
run_from() {  # run_from FILE TOOL ARGS... with FILE as stdin
  local input=$1; shift
  if [ -n "$PG_EXEC" ]; then $PG_EXEC "$@" <"$input"; else "$@" <"$input"; fi
}

if [ -z "${DB_USER:-}" ] || [ -z "${DB_NAME:-}" ]; then
  [ -n "$PG_EXEC" ] || { echo "Set DB_USER and DB_NAME when PG_EXEC is empty" >&2; exit 2; }
  DB_USER=${DB_USER:-$(run printenv POSTGRES_USER | tr -d '\r')}
  DB_NAME=${DB_NAME:-$(run printenv POSTGRES_DB | tr -d '\r')}
fi
if [ "$DB_NAME" = "$CHECK_DB" ]; then
  echo "Refusing: the live database is named like the scratch database" >&2; exit 2
fi

psql_q() {  # psql_q DB SQL -> unaligned rows
  run psql -X -v ON_ERROR_STOP=1 -U "$DB_USER" -d "$1" -tA -F' ' -c "$2"
}

# Exact row count of every table, one "table count" line each.
COUNTS_SQL="select table_name, (xpath('/row/c/text()', query_to_xml(format('select count(*) as c from %I.%I', table_schema, table_name), false, true, '')))[1]::text
            from information_schema.tables where table_schema = 'public' and table_type = 'BASE TABLE' order by 1"

verify() {
  local dump=$1
  echo "Verifying $dump by restoring it into $CHECK_DB ..."
  run dropdb -U "$DB_USER" --if-exists "$CHECK_DB"
  run createdb -U "$DB_USER" "$CHECK_DB"
  # --exit-on-error: a dump that does not restore cleanly fails here.
  if ! run_from "$dump" pg_restore -U "$DB_USER" -d "$CHECK_DB" --no-owner --exit-on-error; then
    run dropdb -U "$DB_USER" --if-exists "$CHECK_DB"
    echo "FAILED: the dump does not restore" >&2; return 1
  fi
  local live restored problems=0
  live=$(psql_q "$DB_NAME" "$COUNTS_SQL")
  restored=$(psql_q "$CHECK_DB" "$COUNTS_SQL")
  run dropdb -U "$DB_USER" --if-exists "$CHECK_DB"
  # Every live table must be in the dump. The live database may have grown
  # since the snapshot (learners keep learning), never shrunk below it --
  # unless rows were deleted meanwhile, which is reported, not hidden.
  while read -r table n; do
    [ -n "$table" ] || continue
    r=$(awk -v t="$table" '$1 == t {print $2}' <<<"$restored")
    if [ -z "$r" ]; then echo "  MISSING in backup: $table"; problems=1
    elif [ "$r" -gt "$n" ]; then echo "  $table: backup has $r rows, live has $n (rows deleted since the dump?)"
    elif [ "$r" -lt "$n" ]; then echo "  $table: backup $r, live $n (written since the dump)"
    fi
  done <<<"$live"
  tables=$(grep -c . <<<"$restored" || true)
  users=$(awk '$1 == "users" {print $2}' <<<"$restored")
  if [ "$problems" -ne 0 ]; then echo "FAILED: tables missing from the backup" >&2; return 1; fi
  echo "OK: restored $tables tables, ${users:-0} users"
}

if [ "${1:-}" = "--verify" ]; then
  verify "${2:?usage: --verify FILE}"
  exit
fi

umask 077  # the dump holds every account; only its owner may read it
mkdir -p "$BACKUP_DIR"
stamp=$(date -u +%Y%m%dT%H%M%SZ)
rev=$(git rev-parse --short HEAD 2>/dev/null || echo unknown)
dump="$BACKUP_DIR/chineseverse-$stamp-at-$rev.dump"
echo "Dumping $DB_NAME to $dump ..."
if ! run pg_dump -U "$DB_USER" -d "$DB_NAME" -Fc >"$dump.partial"; then
  rm -f "$dump.partial"; echo "FAILED: pg_dump" >&2; exit 1
fi
mv "$dump.partial" "$dump"
chmod 600 "$dump"
echo "Wrote $(du -h "$dump" | cut -f1)"
verify "$dump"

if [ -n "${KEEP:-}" ]; then
  # Only this script's own files, oldest first, and never the one just made.
  ls -1t "$BACKUP_DIR"/chineseverse-*-at-*.dump 2>/dev/null | tail -n +"$((KEEP + 1))" | while read -r old; do
    [ "$old" = "$dump" ] || { echo "Removing old backup $old"; rm -f -- "$old"; }
  done
fi
