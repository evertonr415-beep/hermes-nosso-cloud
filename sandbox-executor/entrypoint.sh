#!/bin/sh
set -eu

if [ -z "${SSH_PUBLIC_KEY:-}" ]; then
  echo "[executor] SSH_PUBLIC_KEY is required" >&2
  exit 1
fi

install -d -m 700 -o hermes -g hermes /home/hermes/.ssh
printf '%s\n' "$SSH_PUBLIC_KEY" > /home/hermes/.ssh/authorized_keys
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
