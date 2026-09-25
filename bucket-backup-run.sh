#!/bin/sh
set -eu

# Wait for the dashboard/gateway and volume to settle before the first backup.
sleep 300

while true; do
  if [ -n "${HERMES_BUCKET_NAME:-}" ] && [ -n "${HERMES_BUCKET_ENDPOINT:-}" ]; then
    /opt/hermes/.venv/bin/python /usr/local/bin/hermes-bucket-backup || true
  fi
  sleep 21600
done
