#!/bin/sh
set -eu

# Enable Vercel Sandbox only when one of Hermes' supported authentication
# modes is complete. Railway/Render/Docker should normally use VERCEL_TOKEN
# together with project/team IDs; OIDC remains supported when available.
auth_mode=""
if [ -n "${VERCEL_OIDC_TOKEN:-}" ]; then
  auth_mode="oidc"
elif [ -n "${VERCEL_TOKEN:-}" ] && [ -n "${VERCEL_PROJECT_ID:-}" ] && [ -n "${VERCEL_TEAM_ID:-}" ]; then
  auth_mode="access-token"
fi

if [ -z "$auth_mode" ]; then
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
terminal['vercel_image'] = 'vercel/sandbox/universal:latest'
# Vercel requires 2048 MB per vCPU.
terminal['container_cpu'] = 2
terminal['container_memory'] = 4096
# Remove the deprecated runtime pin if an older Hermes Nosso config wrote it.
terminal.pop('vercel_runtime', None)

p.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding='utf-8')
print('[vercel-sandbox] terminal backend configured: vercel_sandbox')
PY

echo "[vercel-sandbox] authentication mode: $auth_mode"
