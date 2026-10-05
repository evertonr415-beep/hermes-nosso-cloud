#!/bin/sh
set -eu

install -d -m 700 -o hermes -g hermes /home/hermes/.ssh

if [ -n "${EXECUTOR_KEY_SEED:-}" ]; then
  EXECUTOR_KEY_SEED="$EXECUTOR_KEY_SEED" /usr/bin/python3 - <<'PY' > /home/hermes/.ssh/authorized_keys
import hashlib, os
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
secret = os.environ['EXECUTOR_KEY_SEED']
seed = hashlib.sha256(('hermes-private-executor-v1:' + secret).encode('utf-8')).digest()
key = Ed25519PrivateKey.from_private_bytes(seed)
print(key.public_key().public_bytes(serialization.Encoding.OpenSSH, serialization.PublicFormat.OpenSSH).decode('ascii'))
PY
  echo "[executor] authorized key derived from shared Railway secret"
elif [ -n "${SSH_PUBLIC_KEY:-}" ]; then
  printf '%s\n' "$SSH_PUBLIC_KEY" > /home/hermes/.ssh/authorized_keys
  echo "[executor] authorized key loaded from explicit public key"
else
  echo "[executor] no SSH identity source configured" >&2
  exit 1
fi

chown hermes:hermes /home/hermes/.ssh/authorized_keys
chmod 600 /home/hermes/.ssh/authorized_keys

# Key-only authentication; no public password/root login.
cat >/etc/ssh/sshd_config.d/hermes-executor.conf <<'EOF'
Port 2222
ListenAddress 0.0.0.0
PermitRootLogin no
PasswordAuthentication no
KbdInteractiveAuthentication no
PubkeyAuthentication yes
AllowUsers hermes
X11Forwarding no
AllowTcpForwarding yes
GatewayPorts no
ClientAliveInterval 60
ClientAliveCountMax 3
AcceptEnv LANG LC_* NEXT_PUBLIC_* VITE_* DATABASE_URL SUPABASE_URL SUPABASE_ANON_KEY
EOF

mkdir -p /workspace
chown hermes:hermes /workspace

ssh-keygen -A >/dev/null 2>&1

echo "[executor] ready on private SSH port 2222"
exec /usr/sbin/sshd -D -e
