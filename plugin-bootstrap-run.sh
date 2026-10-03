#!/bin/sh
set -u

export HERMES_HOME=/opt/data
MARKER=/opt/data/.curated-plugins-v2.done

# Give the gateway and profile bootstrap time to settle before touching plugin state.
sleep 20

echo "[plugin-stability] start home=$HERMES_HOME"

# Determine the effective gateway UID/GID once. The production gateway currently
# runs unprivileged; this also gives us a safe fallback if that changes later.
GATEWAY_IDS="$(/opt/hermes/.venv/bin/python - <<'PY'
from pathlib import Path
import json, os
uid, gid = 10000, 10000
try:
    data = json.loads(Path('/opt/data/gateway.pid').read_text(encoding='utf-8'))
    pid = int(data.get('pid') or 0)
    if pid:
        for line in Path(f'/proc/{pid}/status').read_text(encoding='utf-8').splitlines():
            if line.startswith('Uid:'):
                uid = int(line.split()[2])
            elif line.startswith('Gid:'):
                gid = int(line.split()[2])
except Exception:
    pass
print(f'{uid}:{gid}')
PY
)"
GATEWAY_UID="${GATEWAY_IDS%:*}"
GATEWAY_GID="${GATEWAY_IDS#*:}"
echo "[plugin-stability] gateway-ids uid=$GATEWAY_UID gid=$GATEWAY_GID"

# Keep the main settings file readable only by the Hermes runtime owner. This is
# also a self-heal for a prior atomic replacement that inherited root ownership.
if [ -f /opt/data/config.yaml ]; then
  chown "$GATEWAY_UID:$GATEWAY_GID" /opt/data/config.yaml || true
  chmod 600 /opt/data/config.yaml || true
fi

# Repair config-backup permissions before invoking any Hermes CLI command, since
# plugin enable/disable can itself trigger config backup writes.
mkdir -p /opt/data/backups/config
chgrp "$GATEWAY_GID" /opt/data/backups 2>/dev/null || true
chmod 750 /opt/data/backups 2>/dev/null || true
chown "$GATEWAY_UID:$GATEWAY_GID" /opt/data/backups/config 2>/dev/null || true
chmod 750 /opt/data/backups/config 2>/dev/null || true

# tool-slimmer remains installed for validation, but disabled because it has
# coincided with full-page reload loops on the current Models dashboard.
timeout 30 hermes plugins disable tool-slimmer >/tmp/plugin-disable-tool-slimmer.log 2>&1 || true
cat /tmp/plugin-disable-tool-slimmer.log 2>/dev/null || true

# Install/enable the three plugins that are currently safe to keep active.
# The marker only skips installation; health checks below always run on boot.
if [ ! -f "$MARKER" ]; then
  echo "[plugin-stability] curated install required"
  for plugin in afterforge toolaria tokenwatch; do
    echo "[plugin-stability] processing $plugin"
    if ! printf 'y\ny\ny\n' | timeout 300 hermes plugins install "$plugin" --enable >/tmp/plugin-install-$plugin.log 2>&1; then
      cat /tmp/plugin-install-$plugin.log 2>/dev/null || true
      timeout 120 hermes plugins enable "$plugin" --no-allow-tool-override >/tmp/plugin-enable-$plugin.log 2>&1 || true
      cat /tmp/plugin-enable-$plugin.log 2>/dev/null || true
    else
      cat /tmp/plugin-install-$plugin.log 2>/dev/null || true
    fi
  done
else
  echo "[plugin-stability] curated install already complete; running health checks"
fi

# Prove that the same UID/GID as the gateway can create and remove a backup
# file. Never make the directory world-writable.
/opt/hermes/.venv/bin/python - "$GATEWAY_UID" "$GATEWAY_GID" <<'PY'
from pathlib import Path
import os, sys
uid, gid = int(sys.argv[1]), int(sys.argv[2])
config_backups = Path('/opt/data/backups/config')
probe = config_backups / '.hermes-write-test'
orig_euid, orig_egid = os.geteuid(), os.getegid()
try:
    if orig_euid == 0:
        os.setegid(gid)
        os.seteuid(uid)
    probe.write_text('ok\n', encoding='utf-8')
    probe.unlink()
    print(f'[plugin-stability] backup-permission-test=ok gateway_uid={uid} gateway_gid={gid} mode=0750')
finally:
    if orig_euid == 0:
        os.seteuid(orig_euid)
        os.setegid(orig_egid)
PY
PERM_RC=$?
if [ "$PERM_RC" -ne 0 ]; then
  echo "[plugin-stability] backup-permission-test=failed rc=$PERM_RC"
fi

# Toolaria 3.x registers rescuer_fetch under the 'rescuer' toolset. Hermes
# 0.21.x lacks ambient-toolset support, so add rescuer only to platform lists
# that already exist. Do NOT create platform_toolsets.cron when absent because
# an explicit cron list is restrictive and could unintentionally remove tools.
/opt/hermes/.venv/bin/python - <<'PY'
from pathlib import Path
import json, os, yaml

home = Path('/opt/data')
config_path = home / 'config.yaml'
try:
    original = config_path.stat()
    cfg = yaml.safe_load(config_path.read_text(encoding='utf-8')) or {}
except Exception as exc:
    print(f'[plugin-stability] toolaria-config-skip reason={type(exc).__name__}')
    raise SystemExit(0)

changed = []
pts = cfg.get('platform_toolsets')
if isinstance(pts, dict):
    for key in ('cli', 'api_server', 'cron'):
        current = pts.get(key)
        if isinstance(current, list) and 'rescuer' not in current:
            current.append('rescuer')
            changed.append(key)

if changed:
    tmp = config_path.with_suffix('.yaml.plugin-stability.tmp')
    tmp.write_text(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True), encoding='utf-8')
    os.chown(tmp, original.st_uid, original.st_gid)
    tmp.chmod(original.st_mode & 0o777 or 0o600)
    tmp.replace(config_path)
    print('[plugin-stability] toolaria-rescuer-added=' + ','.join(changed))
else:
    print('[plugin-stability] toolaria-rescuer-added=none')

# Audit cron jobs with their own explicit tool allowlist. We intentionally do
# not rewrite jobs.json while the scheduler is live.
jobs_path = home / 'cron' / 'jobs.json'
restricted = []
try:
    payload = json.loads(jobs_path.read_text(encoding='utf-8'))
    rows = payload if isinstance(payload, list) else payload.get('jobs', []) if isinstance(payload, dict) else []
    for row in rows:
        if not isinstance(row, dict):
            continue
        tools = row.get('enabled_toolsets')
        if isinstance(tools, list) and 'rescuer' not in tools:
            restricted.append(str(row.get('id') or row.get('job_id') or row.get('name') or 'unknown'))
except Exception:
    pass
print(f'[plugin-stability] toolaria-restricted-cron-jobs={len(restricted)}')
PY

# Validate all four installed plugin packages by their real IDs. tool-slimmer
# is intentionally disabled, but its package still must pass doctor.
all_ok=1
for installed_id in agent-fix-lab tool-slimmer toolaria tokenwatch; do
  echo "[plugin-stability] doctor $installed_id"
  if timeout 180 hermes plugins doctor "$installed_id" --ci >/tmp/plugin-doctor-$installed_id.log 2>&1; then
    cat /tmp/plugin-doctor-$installed_id.log 2>/dev/null || true
  else
    rc=$?
    cat /tmp/plugin-doctor-$installed_id.log 2>/dev/null || true
    echo "[plugin-stability] doctor-failed id=$installed_id rc=$rc"
    all_ok=0
  fi
done

echo "[plugin-stability] enabled user plugins:"
LIST_OUTPUT="$(timeout 120 hermes plugins list --enabled --user --plain 2>&1 || true)"
printf '%s\n' "$LIST_OUTPUT"

for required in agent-fix-lab toolaria tokenwatch; do
  if ! printf '%s\n' "$LIST_OUTPUT" | grep -Fq "$required"; then
    echo "[plugin-stability] required-enabled-missing=$required"
    all_ok=0
  fi
done

if printf '%s\n' "$LIST_OUTPUT" | grep -Fq 'tool-slimmer'; then
  echo "[plugin-stability] warning=tool-slimmer unexpectedly enabled; disabling again"
  timeout 30 hermes plugins disable tool-slimmer >/dev/null 2>&1 || true
fi

if [ "$all_ok" -eq 1 ] && [ "$PERM_RC" -eq 0 ]; then
  printf '%s\n' "afterforge toolaria tokenwatch; tool-slimmer installed-disabled" > "$MARKER"
  echo "[plugin-stability] complete=true"
else
  echo "[plugin-stability] complete=false"
fi

exec sleep infinity
