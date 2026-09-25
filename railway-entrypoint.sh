#!/bin/sh
set -eu

mkdir -p /opt/data

# Remove only the malformed gateway state written by an older bootstrap.
# The official Hermes stage2 hook will recreate it when
# HERMES_GATEWAY_BOOTSTRAP_STATE=running is set.
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

# Keep safe model/web defaults persistent.
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
model["provider"] = "openai-codex"
model["default"] = "gpt-5.6-sol"
model["persist_switch_by_default"] = True
web = data.setdefault("web", {})
if isinstance(web, dict):
    web.setdefault("keyless_fallback", True)
p.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
PY
fi

exec /opt/hermes/docker/entrypoint-dispatch.sh "$@"
