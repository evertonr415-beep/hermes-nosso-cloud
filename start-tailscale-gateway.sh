#!/bin/sh
set -eu

mkdir -p "${TS_STATE_DIR:-/var/lib/tailscale}"

echo "[tailscale-gateway] starting Tailscale userspace networking"
/usr/local/bin/containerboot &
TS_PID=$!

echo "[tailscale-gateway] starting private Hermes reverse proxy on :8642"
python3 /opt/hermes-gateway/proxy.py &
PROXY_PID=$!

trap 'kill "$PROXY_PID" "$TS_PID" 2>/dev/null || true' INT TERM

while kill -0 "$TS_PID" 2>/dev/null && kill -0 "$PROXY_PID" 2>/dev/null; do
  sleep 2
done

wait "$TS_PID" || true
wait "$PROXY_PID" || true
exit 1
