#!/bin/sh
set -eu

mkdir -p /opt/data

# Keep the default Hermes gateway enabled across Railway restarts.
# The official s6 reconciler reads this before registering services.
printf '%s\n' '{"gateway_state":"running"}' > /opt/data/gateway_state.json

# Merge safe defaults into the persistent config without touching secrets
# or unrelated user settings. OAuth credentials live in the auth store.
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

# Preserve Hermes' built-in keyless web search/extract fallback.
web = data.setdefault("web", {})
if isinstance(web, dict):
    web.setdefault("keyless_fallback", True)

p.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
PY
fi

exec /opt/hermes/docker/entrypoint-dispatch.sh "$@"
