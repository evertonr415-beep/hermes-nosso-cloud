#!/bin/sh
set -u

MARKER=/opt/data/.curated-plugins-v2.done
PLUGINS="afterforge tool-slimmer toolaria tokenwatch"

if [ -f "$MARKER" ]; then
  echo "[plugin-bootstrap-v2] already complete"
  exec sleep infinity
fi

# Let the Hermes home/profile initialization finish first.
sleep 20

echo "[plugin-bootstrap-v2] starting official CLI installation"
all_ok=1

for plugin in $PLUGINS; do
  if [ -d "/opt/data/plugins/$plugin" ]; then
    echo "[plugin-bootstrap-v2] $plugin already present; ensuring enabled"
    timeout 120 hermes plugins enable "$plugin" --no-allow-tool-override >/tmp/plugin-enable-$plugin.log 2>&1 || true
    cat /tmp/plugin-enable-$plugin.log 2>/dev/null || true
  else
    echo "[plugin-bootstrap-v2] installing $plugin"
    # The owner explicitly approved these four catalog plugins. --enable skips
    # the enable prompt; stdin answers only dependency-consent prompts from the
    # official installer. No dependency/admission checks are bypassed.
    if ! printf 'y\ny\ny\n' | timeout 300 hermes plugins install "$plugin" --enable >/tmp/plugin-install-$plugin.log 2>&1; then
      rc=$?
      echo "[plugin-bootstrap-v2] install failed plugin=$plugin rc=$rc"
      cat /tmp/plugin-install-$plugin.log 2>/dev/null || true
      all_ok=0
      continue
    fi
    cat /tmp/plugin-install-$plugin.log 2>/dev/null || true
  fi

  echo "[plugin-bootstrap-v2] doctor $plugin"
  if ! timeout 180 hermes plugins doctor "$plugin" --ci >/tmp/plugin-doctor-$plugin.log 2>&1; then
    rc=$?
    echo "[plugin-bootstrap-v2] doctor failed plugin=$plugin rc=$rc"
    cat /tmp/plugin-doctor-$plugin.log 2>/dev/null || true
    all_ok=0
  else
    cat /tmp/plugin-doctor-$plugin.log 2>/dev/null || true
  fi
done

echo "[plugin-bootstrap-v2] enabled plugins:"
timeout 120 hermes plugins list --enabled --plain 2>&1 || true

for plugin in $PLUGINS; do
  if [ ! -d "/opt/data/plugins/$plugin" ]; then
    all_ok=0
  fi
done

if [ "$all_ok" -eq 1 ]; then
  printf '%s\n' "$PLUGINS" > "$MARKER"
  echo "[plugin-bootstrap-v2] complete=true"
else
  echo "[plugin-bootstrap-v2] complete=false"
fi

exec sleep infinity
