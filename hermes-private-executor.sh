#!/bin/sh
set -eu

# Prefer Vercel Sandbox whenever a complete Vercel auth mode is available.
if [ -n "${VERCEL_OIDC_TOKEN:-}" ] || { [ -n "${VERCEL_TOKEN:-}" ] && [ -n "${VERCEL_PROJECT_ID:-}" ] && [ -n "${VERCEL_TEAM_ID:-}" ]; }; then
  echo "[private-executor] Vercel credentials detected; keeping Vercel Sandbox backend"
  exit 0
fi

# Reuse the API server secret Hermes already persists on /opt/data. Railway's
# service-reference variable can be absent during early init, while /opt/data/.env
# is durable and is the value Hermes itself loads with override=True.
seed="${API_SERVER_KEY:-}"
if [ -z "$seed" ] && [ -f /opt/data/.env ]; then
  seed="$(awk '/^API_SERVER_KEY=/{sub(/^API_SERVER_KEY=/, ""); print; exit}' /opt/data/.env 2>/dev/null || true)"
fi
if [ -z "$seed" ]; then
  echo "[private-executor] shared key seed unavailable; keeping existing terminal backend"
  exit 0
fi
export HERMES_EXECUTOR_SEED="$seed"

key_dir=/opt/data/.ssh
key_path="$key_dir/hermes-executor"
known_hosts="$key_dir/known_hosts"
install -d -m 700 "$key_dir"

/usr/bin/python3 - <<'PY' > "$key_path"
import hashlib, os
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
secret = os.environ['HERMES_EXECUTOR_SEED']
seed = hashlib.sha256(('hermes-private-executor-v1:' + secret).encode('utf-8')).digest()
key = Ed25519PrivateKey.from_private_bytes(seed)
print(key.private_bytes(
    serialization.Encoding.PEM,
    serialization.PrivateFormat.OpenSSH,
    serialization.NoEncryption(),
).decode('ascii'), end='')
PY
chmod 600 "$key_path"
unset HERMES_EXECUTOR_SEED seed

if ! ssh-keygen -y -f "$key_path" >/dev/null 2>&1; then
  echo "[private-executor] derived SSH key failed validation; keeping local backend" >&2
  rm -f "$key_path"
  exit 0
fi

# Prove private DNS + TCP + SSH authentication before changing Hermes config.
# A failed executor therefore cannot strand Hermes on an unreachable backend.
probe_ok=0
i=1
while [ "$i" -le 8 ]; do
  result="$(ssh -i "$key_path" -p 2222 \
      -o BatchMode=yes \
      -o ConnectTimeout=4 \
      -o StrictHostKeyChecking=accept-new \
      -o UserKnownHostsFile="$known_hosts" \
      -o LogLevel=ERROR \
      hermes@hermes-executor.railway.internal 'printf EXECUTOR_OK' 2>/dev/null || true)"
  if [ "$result" = "EXECUTOR_OK" ]; then
    probe_ok=1
    break
  fi
  i=$((i + 1))
  sleep 2
done

if [ "$probe_ok" != "1" ]; then
  echo "[private-executor] SSH probe failed; forcing safe local backend" >&2
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
terminal['backend'] = 'local'
p.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding='utf-8')
PY
  rm -f "$key_path"
  exit 0
fi

# The supervised Hermes processes run as the hermes user.
chown -R hermes:hermes "$key_dir"
chmod 700 "$key_dir"
chmod 600 "$key_path"
[ ! -f "$known_hosts" ] || chmod 600 "$known_hosts"

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
print('[private-executor] SSH probe OK; terminal backend configured: ssh')
PY
