#!/usr/bin/env bash
set -euo pipefail
echo "=== Xiao6 Preflight Check ==="
echo "[1] Port 8000 (Server):"
curl -sf http://localhost:8000/api/health >/dev/null 2>&1 && echo " OK" || echo " FAIL"
echo "[2] Port 9880 (GPT-SoVITS):"
if curl -sf http://localhost:9880/ >/dev/null 2>&1; then
  echo " OK"
else
  echo " ⚠️ WARN: GPT-SoVITS unavailable (optional)"
fi
echo "[3] ENV vars:"
for v in APP_VERSION TTS_BACKEND GPT_SOVITS_URL; do
  echo "  $v=${!v:-<NOT SET>}"
done
echo "[4] DB readable:"
DB_PATH="${DATABASE_PATH:-./xiao6-ui/data/xiao6.db}"
if [ -f "$DB_PATH" ]; then
  # Use Python instead of sqlite3 CLI (not available on Windows)
  TABLES=$(python -c "import sqlite3; conn=sqlite3.connect('$DB_PATH'); tables=[r[0] for r in conn.execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall()]; print(','.join(tables)); conn.close()" 2>/dev/null || echo "")
  if [ -n "$TABLES" ]; then
    echo " OK (tables: $TABLES)"
  else
    echo " FAIL (DB exists but query failed)"
  fi
else
  echo " ⚠️ WARN: DB not found at $DB_PATH"
fi
echo "=== Done ==="
