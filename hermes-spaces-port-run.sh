#!/command/with-contenv sh
set -eu
# Platform-agnostic temporary storage for ephemeral diagnostics/cache.
# socat logs to stderr (captured by Render/Spaces), never /opt/data/logs.
export TMPDIR=/tmp
# The base Hermes container uses s6; on Spaces publish the already-supervised
# Cloud gateway/UI on one public HTTP port. Do not expose private model APIs.
if [ -z "${SPACE_ID:-}" ] && [ "${HERMES_SPACE_MODE:-0}" != "1" ]; then
  exec sleep infinity
fi
exec /usr/bin/socat TCP-LISTEN:8080,bind=0.0.0.0,reuseaddr,fork TCP:127.0.0.1:9119
