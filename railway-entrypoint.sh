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

if [ -n "${OPENAI_API_KEY:-}" ]; then
  /opt/hermes/.venv/bin/python - <<'PY'
from pathlib import Path
import os
p = Path("/opt/data/.env")
key = os.environ.get("OPENAI_API_KEY", "").strip()
if key:
    lines = p.read_text(encoding="utf-8").splitlines() if p.exists() else []
    kept = [line for line in lines if not line.startswith("OPENAI_API_KEY=")]
    kept.append("OPENAI_API_KEY=" + key)
    p.write_text("\n".join(kept) + "\n", encoding="utf-8")
    p.chmod(0o600)
PY
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
providers = data.setdefault("providers", {})
if not isinstance(providers, dict):
    providers = {}
    data["providers"] = providers
providers["matrix"] = {
    "name": "Matrix",
    "api": "https://matrix.dgsis.com.br/v1",
    "key_env": "MATRIX_API_KEY",
    "transport": "chat_completions",
    "models": {
        "claude-opus-5": {},
    },
}
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

if [ "${HERMES_MODEL_VALIDATE:-0}" = "1" ]; then
  (
    sleep 20
    echo "[model-validate] start"
    if timeout 120 hermes -z "Reply with exactly: GPT6_HERMES_OK"; then
      echo "[model-validate] command-ok"
    else
      rc=$?
      echo "[model-validate] command-failed rc=$rc"
    fi
  ) &
fi

if [ "${HERMES_MATRIX_VALIDATE:-0}" = "1" ] && [ -n "${MATRIX_API_KEY:-}" ]; then
  (
    sleep 15
    /opt/hermes/.venv/bin/python - <<'PY'
import json, os, urllib.request, urllib.error
base = "https://matrix.dgsis.com.br"
key = os.environ.get("MATRIX_API_KEY", "")
model = "claude-opus-5"

def call(path, payload=None):
    headers = {"Authorization": "Bearer " + key, "Accept": "application/json"}
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(base + path, data=data, headers=headers,
                                 method="POST" if data else "GET")
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            return resp.status, resp.read(1024 * 1024)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(8192)
    except Exception as exc:
        print("[matrix-validate] network-error type=" + type(exc).__name__)
        return None, b""

status, body = call("/v1/models")
present = False
if status == 200:
    try:
        payload = json.loads(body)
        ids = [str(x.get("id", "")) for x in payload.get("data", []) if isinstance(x, dict)]
        present = model in ids
    except Exception:
        pass
print(f"[matrix-validate] models-status={status} model-present={str(present).lower()}")

chat_status, chat_body = call("/v1/chat/completions", {
    "model": model,
    "messages": [{"role": "user", "content": "Reply only OK"}],
    "max_tokens": 4,
    "temperature": 0,
})
returned_model = ""
if chat_status == 200:
    try:
        returned_model = str(json.loads(chat_body).get("model", ""))
    except Exception:
        pass
print(f"[matrix-validate] chat-status={chat_status} returned-model={returned_model[:100]}")
PY
  ) &
fi

echo "[storage-diag] filesystem:"
df -h /opt/data 2>/dev/null || true
echo "[storage-diag] top-level usage:"
du -h -d 1 /opt/data 2>/dev/null | sort -h || true
exec /opt/hermes/docker/entrypoint-dispatch.sh "$@"
