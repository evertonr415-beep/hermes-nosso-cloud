#!/command/with-contenv sh
set -eu

if [ "${HERMES_RUNTIME_SMOKE:-0}" != "1" ]; then
  exec sleep infinity
fi

mkdir -p /opt/data/smoke
if [ -f /opt/data/smoke/runtime-smoke-complete ]; then
  exec sleep infinity
fi

# Wait for dashboard/gateway/profile reconciliation and OAuth stores.
sleep 20
echo "[runtime-smoke] starting"
/usr/local/bin/hermes-smoke-tests
touch /opt/data/smoke/runtime-smoke-complete
echo "[runtime-smoke] complete"
exec sleep infinity
