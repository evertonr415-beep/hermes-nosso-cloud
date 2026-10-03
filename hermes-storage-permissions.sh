#!/bin/sh
set -eu

# The upstream Hermes gateway in this image runs as uid/gid 10000. Repair only
# the private settings/backup paths needed by Hermes before stage2 reads them.
RUNTIME_UID="${HERMES_RUNTIME_UID:-10000}"
RUNTIME_GID="${HERMES_RUNTIME_GID:-10000}"

if [ -f /opt/data/config.yaml ]; then
  chown "$RUNTIME_UID:$RUNTIME_GID" /opt/data/config.yaml
  chmod 600 /opt/data/config.yaml
fi

mkdir -p /opt/data/backups/config
chown root:"$RUNTIME_GID" /opt/data/backups 2>/dev/null || true
chmod 750 /opt/data/backups 2>/dev/null || true
chown "$RUNTIME_UID:$RUNTIME_GID" /opt/data/backups/config
chmod 750 /opt/data/backups/config

echo "[storage-permissions] config/backups ready uid=$RUNTIME_UID gid=$RUNTIME_GID"
