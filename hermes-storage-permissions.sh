#!/bin/sh
set -eu

# The upstream Hermes gateway in this image runs as uid/gid 10000. Repair only
# the private settings/backup paths needed by Hermes before stage2 reads them.
RUNTIME_UID="${HERMES_RUNTIME_UID:-10000}"
RUNTIME_GID="${HERMES_RUNTIME_GID:-10000}"

# Keep the persistent volume healthy without touching user data. Hermes can
# generate very large rotating logs and transient SQLite journal files; when the
# 500 MB Railway volume fills, /v1/responses fails even though the model itself
# answered correctly. Only disposable runtime artifacts are cleaned here.
for dir in /opt/data/logs /opt/data/log /opt/data/tmp /opt/data/temp; do
  if [ -d "$dir" ]; then
    find "$dir" -type f -name '*.log' -exec sh -c ': > "$1"' _ {} \; 2>/dev/null || true
    find "$dir" -type f \( -name '*.log.*' -o -name '*.tmp' -o -name '*.temp' -o -name '*.pid' \) -delete 2>/dev/null || true
  fi
done

# Remove stale SQLite sidecars only when their main DB is not actively using
# them at container boot. We deliberately preserve every *.db/*.sqlite file.
find /opt/data -maxdepth 4 -type f \( -name '*.db-shm' -o -name '*.sqlite-shm' \) -delete 2>/dev/null || true

if [ -f /opt/data/config.yaml ]; then
  chown "$RUNTIME_UID:$RUNTIME_GID" /opt/data/config.yaml
  chmod 600 /opt/data/config.yaml
fi

mkdir -p /opt/data/backups/config
chown root:"$RUNTIME_GID" /opt/data/backups 2>/dev/null || true
chmod 750 /opt/data/backups 2>/dev/null || true
chown "$RUNTIME_UID:$RUNTIME_GID" /opt/data/backups/config
chmod 750 /opt/data/backups/config

echo "[storage-permissions] safe cleanup complete; config/backups ready uid=$RUNTIME_UID gid=$RUNTIME_GID"
df -h /opt/data 2>/dev/null || true
