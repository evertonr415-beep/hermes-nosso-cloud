#!/command/with-contenv sh
set -u

# One-shot cleanup for the synthetic validation cron left by earlier smoke tests.
# It removes only the known validation job/name and does not touch user cron jobs.
sleep 25

echo "[cron-cleanup] removing stale validation cron if present"
timeout 30 hermes cron remove 2a25f2dd19be >/tmp/cron-cleanup-id.log 2>&1 || true
cat /tmp/cron-cleanup-id.log 2>/dev/null || true

timeout 30 hermes cron remove HERMES_CRON_VALIDATION >/tmp/cron-cleanup-name.log 2>&1 || true
cat /tmp/cron-cleanup-name.log 2>/dev/null || true

echo "[cron-cleanup] complete"
exec sleep infinity
