#!/usr/bin/env bash
# Nightly backup of the Wayfara database (cluster 16/finnguide, port 5433).
# Targets ONLY the wayfara DB — Ash's replica on 5432 is never touched.
#
# Custom-format dump (-Fc): compressed, restorable table-by-table with
# pg_restore. Keeps 14 days locally. This is the dev-machine safety net;
# production gets managed Postgres with PITR instead.
#
# Restore: pg_restore -d "$WAYFARA_DB_URL" --clean --if-exists <file>.dump

set -euo pipefail

DB_URL="${WAYFARA_DB_URL:-postgres://awais-faiz@:5433/wayfara}"
BACKUP_DIR="${WAYFARA_BACKUP_DIR:-$HOME/backups/wayfara}"
KEEP_DAYS="${WAYFARA_BACKUP_KEEP_DAYS:-14}"

mkdir -p "$BACKUP_DIR"

STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="$BACKUP_DIR/wayfara-$STAMP.dump"

pg_dump --dbname="$DB_URL" -Fc --no-owner --file="$OUT"

# A dump this small means something went wrong — fail loudly, don't rotate.
if [ ! -s "$OUT" ] || [ "$(stat -c%s "$OUT")" -lt 1024 ]; then
    echo "ERROR: backup $OUT is missing or suspiciously small" >&2
    exit 1
fi

# Prune only after a verified-good new dump exists.
find "$BACKUP_DIR" -name 'wayfara-*.dump' -mtime +"$KEEP_DAYS" -delete

echo "$(date -Is) OK $OUT ($(stat -c%s "$OUT") bytes)"
