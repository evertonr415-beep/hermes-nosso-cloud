#!/bin/sh
set -eu

# Prefer Vercel Sandbox whenever a complete Vercel auth mode is available.
if [ -n "${VERCEL_OIDC_TOKEN:-}" ] || { [ -n "${VERCEL_TOKEN:-}" ] && [ -n "${VERCEL_PROJECT_ID:-}" ] && [ -n "${VERCEL_TEAM_ID:-}" ]; }; then
  echo "[private-executor] Vercel credentials detected; keeping Vercel Sandbox backend"
  exit 0
fi

if [ -z "${HERMES_EXECUTOR_SSH_PRIVATE_KEY:-}" ]; then
  echo "[private-executor] SSH key not configured; keeping existing terminal backend"
  exit 0
fi

key_dir=/opt/data/.ssh
key_path="$key_dir/hermes-executor"
install -d -m 700 -o hermes -g hermes "$key_dir"
printf '%s\n' "$HERMES_EXECUTOR_SSH_PRIVATE_KEY" > "$key_path"
chown hermes:hermes "$key_path"
chmod 600 "$key_path"

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

terminal['backend'] = 'ssh'
terminal['cwd'] = '/workspace'
terminal['ssh_host'] = 'hermes-executor.railway.internal'
terminal['ssh_user'] = 'hermes'
terminal['ssh_port'] = 2222
terminal['ssh_key'] = '/opt/data/.ssh/hermes-executor'
terminal['persistent_shell'] = True

p.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding='utf-8')
print('[private-executor] terminal backend configured: ssh')
PY
