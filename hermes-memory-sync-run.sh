#!/command/with-contenv sh
set -eu
# Separate low-resource background worker. Errors never stop Hermes gateway.
# Immediate one-off scan for any existing USER.md and MEMORY.md in the mounted volume.
sleep 2
/usr/bin/python3 -u /usr/local/bin/hermes-memory-sync --once || true
# Probe with a fixed public prompt; never send user content or memory.
echo '[hermes-model] public endpoint connectivity probe starting'
# Probe is non-blocking. External DNS or community endpoints must never stall memory sync.
if command -v timeout >/dev/null 2>&1; then
  (
    timeout -k 2s 35s /usr/local/bin/hermes-global-model-router --probe ||
      echo '[hermes-model] probe failed or timed out; retained existing chat backend'
  ) &
else
  echo '[hermes-model] timeout utility unavailable; probe skipped safely'
fi
while true; do
  /usr/bin/python3 -u /usr/local/bin/hermes-memory-sync --once || true
  sleep 300
done
