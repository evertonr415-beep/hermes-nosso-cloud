#!/bin/bash
set -eu
# Render/Spaces startup: do NOT invoke s6-overlay on the critical boot path.
export TMPDIR=/tmp
export HERMES_GLOBAL_ROUTER_ENABLED=1
export HERMES_GLOBAL_KEYLESS_ALLOW=0
export HERMES_INFERENCE_MODE="${HERMES_INFERENCE_MODE:-groq}"
export HERMES_PUBLIC_ANONYMOUS_ENABLED="${HERMES_PUBLIC_ANONYMOUS_ENABLED:-0}"
export HERMES_FALLBACK_ON_HF_402="${HERMES_FALLBACK_ON_HF_402:-0}"
export PYTHONDONTWRITEBYTECODE=1

# Keep the original full-agent entrypoint accessible for later restoration;
# this mode still requires s6 and must be selected explicitly.
if [ "${HERMES_STARTUP_MODE:-light}" = "full" ]; then
  exec /usr/local/bin/hermes-railway-entrypoint "$@"
fi

# Router is a request/response CLI, not an HTTP daemon: run a *local*
# status check, then invoke it on demand from the web handler.
(
  /usr/bin/python3 -u /usr/local/bin/hermes-global-model-router --status >/dev/null 2>&1 || true
) &

# Memory sync is separate from the HTTP startup, and runs only when configured.
# No /opt/data/logs/gateways or s6-log requirement in light mode.
if [ -n "${HERMES_MEMORY_SYNC_URL:-}" ] && [ -n "${HERMES_MEMORY_SYNC_TOKEN:-}" ] && [ -n "${HERMES_MEMORY_AES_KEY:-}" ]; then
  (
    while true; do
      /usr/bin/python3 -u /usr/local/bin/hermes-memory-sync --once || true
      sleep 300
    done
  ) &
fi

# Replace PID 1 with a functioning web server, not a TCP proxy to a dead port.
exec /usr/bin/python3 -u /usr/local/bin/hermes-render-light-web
