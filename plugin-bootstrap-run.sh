#!/bin/sh
set -u

export HERMES_HOME=/opt/data
MARKER=/opt/data/.curated-plugins-v2.done
PLUGINS="afterforge tool-slimmer toolaria tokenwatch"

# Stability safeguard (2026-10-03): tool-slimmer injects dashboard code and
# coincides with full-page reload loops on the Models surface in the current
# upstream dashboard. Keep it installed on disk but disabled until the
# dashboard/plugin compatibility is fixed upstream.
timeout 30 hermes plugins disable tool-slimmer >/tmp/plugin-disable-tool-slimmer.log 2>&1 || true
cat /tmp/plugin-disable-tool-slimmer.log 2>/dev/null || true

if [ -f "$MARKER" ]; then
  echo "[plugin-bootstrap-v2] already complete (tool-slimmer forced disabled for dashboard stability)"
  exec sleep infinity
fi

# Let the Hermes home/profile initialization finish first.
sleep 20

echo "[plugin-bootstrap-v2] starting official CLI installation home=$HERMES_HOME"
all_ok=1

for plugin in $PLUGINS; do
  # tool-slimmer is intentionally skipped while the dashboard compatibility
  # issue is active. Other plugins keep their existing bootstrap behavior.
  if [ "$plugin" = "tool-slimmer" ]; then
    echo "[plugin-bootstrap-v2] skipping tool-slimmer (dashboard stability safeguard)"
    continue
  fi

  echo "[plugin-bootstrap-v2] processing $plugin"
  if ! printf 'y\ny\ny\n' | timeout 300 hermes plugins install "$plugin" --enable >/tmp/plugin-install-$plugin.log 2>&1; then
    # An already-installed plugin may make install return non-zero; try the official enable path.
    cat /tmp/plugin-install-$plugin.log 2>/dev/null || true
    timeout 120 hermes plugins enable "$plugin" --no-allow-tool-override >/tmp/plugin-enable-$plugin.log 2>&1 || true
    cat /tmp/plugin-enable-$plugin.log 2>/dev/null || true
  else
    cat /tmp/plugin-install-$plugin.log 2>/dev/null || true
  fi
done

echo "[plugin-bootstrap-v2] enabled user plugins:"
LIST_OUTPUT="$(timeout 120 hermes plugins list --enabled --user --plain 2>&1 || true)"
printf '%s\n' "$LIST_OUTPUT"

# Catalog name afterforge installs with plugin id agent-fix-lab.
for installed_id in agent-fix-lab toolaria tokenwatch; do
  if ! printf '%s\n' "$LIST_OUTPUT" | grep -Fq "$installed_id"; then
    echo "[plugin-bootstrap-v2] missing enabled plugin id=$installed_id"
    all_ok=0
    continue
  fi

  echo "[plugin-bootstrap-v2] doctor $installed_id"
  if timeout 180 hermes plugins doctor "$installed_id" --ci >/tmp/plugin-doctor-$installed_id.log 2>&1; then
    cat /tmp/plugin-doctor-$installed_id.log 2>/dev/null || true
  else
    cat /tmp/plugin-doctor-$installed_id.log 2>/dev/null || true
    all_ok=0
  fi
done

if [ "$all_ok" -eq 1 ]; then
  printf '%s\n' "afterforge toolaria tokenwatch" > "$MARKER"
  echo "[plugin-bootstrap-v2] complete=true"
else
  echo "[plugin-bootstrap-v2] complete=false"
fi

exec sleep infinity
