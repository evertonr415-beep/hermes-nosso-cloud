#!/bin/sh
set -eu

# Enable the isolated Vercel Sandbox backend only when credentials are present.
# This keeps the existing local backend untouched until authentication is ready.
if [ -z "${VERCEL_OIDC_TOKEN:-}" ] || [ -z "${VERCEL_PROJECT_ID:-}" ] || [ -z "${VERCEL_TEAM_ID:-}" ]; then
  echo "[vercel-sandbox] credentials not complete; keeping existing terminal backend"
  exit 0
fi

/opt/hermes/.venv/bin/python - <<'PY'
from pathlib import Path
import yaml

p = Path('/opt/data/config.yaml')
try:
    data = yaml.safe_load(p.read_text(encoding='utf-8')) if p.exists() else {}
except Exception:
    data = {}
if not isinstance(data, dict):
    data = {}
terminal = data.setdefault('terminal', {})
if not isinstance(terminal, dict):
    terminal = {}
    data['terminal'] = terminal
terminal['backend'] = 'vercel_sandbox'
terminal['vercel_runtime'] = 'node24'
terminal['container_cpu'] = 2
terminal['container_memory'] = 4096
p.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding='utf-8')
print('[vercel-sandbox] terminal backend configured: vercel_sandbox')
PY
