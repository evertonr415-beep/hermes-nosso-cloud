#!/command/with-contenv sh
set -u

# One-shot cleanup for synthetic validation crons left by earlier smoke tests.
# Remove only the known validation job IDs; never touch user-created cron jobs.
sleep 25

echo "[cron-cleanup] removing stale validation cron jobs if present"
for job_id in 2a25f2dd19be c67d151f6c34 f0fd8032bd3c 789d3a768dc1; do
  echo "[cron-cleanup] remove id=$job_id"
  timeout 30 hermes cron remove "$job_id" >/tmp/cron-cleanup-$job_id.log 2>&1 || true
  cat /tmp/cron-cleanup-$job_id.log 2>/dev/null || true
done

echo "[cron-cleanup] complete"
exec sleep infinity
