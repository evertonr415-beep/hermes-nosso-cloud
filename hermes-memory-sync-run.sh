#!/command/with-contenv sh
set -eu
# Separate low-resource background worker. Errors never stop Hermes gateway.
sleep 45
while true; do
  /usr/bin/python3 -u /usr/local/bin/hermes-memory-sync --once || true
  sleep 300
done
