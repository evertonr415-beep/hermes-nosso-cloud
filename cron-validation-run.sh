#!/bin/sh
set -eu

if [ "${HERMES_CRON_VALIDATE:-0}" != "1" ]; then
  exec sleep infinity
fi

mkdir -p /opt/data/cron-validation /opt/data/scripts
rm -f /opt/data/cron-validation/ran.txt
cat > /opt/data/scripts/cron_validation.py <<'PY'
from pathlib import Path
Path('/opt/data/cron-validation/ran.txt').write_text('CRON_OK\n', encoding='utf-8')
print('CRON_OK')
PY
chmod 644 /opt/data/scripts/cron_validation.py

echo "[cron-validation] direct-script-check"
/opt/hermes/.venv/bin/python - <<'PY'
from cron.scheduler_script import _run_job_script
print(_run_job_script("cron_validation.py"))
PY

echo "[cron-validation] scheduler-status"
hermes cron status || true

CREATE_OUT="$(hermes cron create "1m" "Cron scheduler validation" --name HERMES_CRON_VALIDATION --script cron_validation.py --no-agent --deliver local 2>&1)"
printf '%s\n' "$CREATE_OUT"
JOB_ID="$(printf '%s\n' "$CREATE_OUT" | grep -Eo '[0-9a-fA-F-]{8,}' | head -n1)"
echo "[cron-validation] job=$JOB_ID"

if [ -z "$JOB_ID" ]; then
  echo "[cron-validation] CREATE_FAILED"
  exec sleep infinity
fi

# Wait for the real scheduler tick, not a manual trigger.
sleep 85

if [ -f /opt/data/cron-validation/ran.txt ]; then
  echo "[cron-validation] MARKER=$(cat /opt/data/cron-validation/ran.txt)"
else
  echo "[cron-validation] MARKER_MISSING"
fi

hermes cron runs "$JOB_ID" --limit 5 || true
hermes cron remove "$JOB_ID" || true
echo "[cron-validation] done"
exec sleep infinity
