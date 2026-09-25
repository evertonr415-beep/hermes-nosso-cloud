#!/bin/sh
set -eu

mkdir -p /opt/data

rm -rf /opt/data/smoke
rm -f /opt/data/workspace/hermes-smoke-file.txt
rm -f /opt/data/scripts/hermes_smoke_cron.py

if [ "${HERMES_STORAGE_CLEANUP:-0}" = "1" ]; then
  echo "[storage-cleanup] removing disposable caches only"
  rm -rf /opt/data/home/.npm/_cacache /opt/data/home/.npm/_logs /opt/data/home/.npm/_npx
  rm -rf /opt/data/home/.cache/*
  rm -rf /opt/data/cache/scratch/*
  echo "[storage-cleanup] after cleanup"
  df -h /opt/data || true
fi

if [ "${HERMES_STORAGE_AUDIT:-0}" = "1" ]; then
  echo "[storage-audit] df"
  df -h /opt/data || true
  echo "[storage-audit] largest paths"
  du -xh --max-depth=2 /opt/data 2>/dev/null | sort -h | tail -40 || true
fi

if [ -f /opt/data/gateway_state.json ] && ! /opt/hermes/.venv/bin/python - <<'PY'
from pathlib import Path
import json, sys
p = Path("/opt/data/gateway_state.json")
try:
    json.loads(p.read_text(encoding="utf-8-sig"))
except Exception:
    sys.exit(1)
PY
then
  rm -f /opt/data/gateway_state.json
fi

if [ -x /opt/hermes/.venv/bin/python ]; then
  /opt/hermes/.venv/bin/python - <<'PY'
from pathlib import Path
import yaml
p = Path("/opt/data/config.yaml")
try:
    data = yaml.safe_load(p.read_text(encoding="utf-8")) if p.exists() else {}
except Exception:
    data = {}
if not isinstance(data, dict):
    data = {}
model = data.setdefault("model", {})
if not isinstance(model, dict):
    model = {}
    data["model"] = model
model["provider"] = "openai-api"
model["default"] = "gpt-6-sol"
model["persist_switch_by_default"] = True
data["fallback_providers"] = [
    {"provider": "openai-codex", "model": "gpt-6-sol"},
    {"provider": "openai-codex", "model": "gpt-5.6-sol"},
]
web = data.setdefault("web", {})
if isinstance(web, dict):
    web.setdefault("keyless_fallback", True)
p.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
PY
fi

# The Hermes Docker image already owns gateway/API supervision through s6.
# Do not launch a second gateway here. HERMES_GATEWAY_BOOTSTRAP_STATE=running
# and API_SERVER_* configure the single supervised gateway after s6 is ready.
if [ "${HERMES_RUN_SMOKE_TESTS:-0}" = "1" ]; then
  (
    sleep 20
    /usr/local/bin/hermes-smoke-tests
  ) &
fi

echo "[storage-diag] filesystem:"
df -h /opt/data 2>/dev/null || true
echo "[storage-diag] top-level usage:"
du -h -d 1 /opt/data 2>/dev/null | sort -h || true
exec /opt/hermes/docker/entrypoint-dispatch.sh "$@"
