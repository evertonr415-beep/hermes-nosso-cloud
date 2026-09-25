#!/bin/sh
set +e
SMOKE=/opt/data/smoke
mkdir -p "$SMOKE" /opt/data/workspace /opt/data/scripts
LOG="$SMOKE/results.log"
: > "$LOG"
echo "SMOKE_START" >> "$LOG"

run_test() {
  name="$1"; shift
  echo "=== $name ===" >> "$LOG"
  "$@" >> "$LOG" 2>&1
  rc=$?
  echo "RC=$rc" >> "$LOG"
  return $rc
}

# 1. Main model / real prompt
run_test CHAT hermes -z "Reply with exactly: CHAT_OK"

# 2. Files: create a persistent file and make Hermes read it.
printf '%s\n' 'FILES_OK_2719' > /opt/data/workspace/hermes-smoke-file.txt
run_test FILES hermes -z "Read /opt/data/workspace/hermes-smoke-file.txt using your file or terminal tools. Reply with exactly the text contained in that file and nothing else."

# 3. Web Search
run_test WEB_SEARCH hermes -z "You must use the web_search tool once. Search the web for the official OpenAI homepage. If the web_search tool succeeds, reply exactly: WEB_SEARCH_OK"

# 4. Browser
run_test BROWSER hermes -z "You must use the browser/agent-browser tool to open https://example.com and inspect the page. If the page title is Example Domain, reply exactly: BROWSER_OK"

# 5. Skills inventory
run_test SKILLS hermes skills list --source all --enabled-only

# 6. Cron scheduler status + real no-agent job execution
cat > /opt/data/scripts/hermes_smoke_cron.py <<'PY'
from pathlib import Path
Path('/opt/data/smoke/cron-ran.txt').write_text('CRON_OK\n', encoding='utf-8')
print('CRON_OK')
PY
run_test CRON_STATUS hermes cron status
CREATE_OUT="$(hermes cron create "every 1h" "Hermes smoke cron" --name HERMES_SMOKE_CRON --script hermes_smoke_cron.py --no-agent --deliver local 2>&1)"
printf '%s\n' "$CREATE_OUT" >> "$LOG"
JOB_ID="$(printf '%s\n' "$CREATE_OUT" | grep -Eo '[0-9a-fA-F-]{8,}' | head -n1)"
if [ -n "$JOB_ID" ]; then
  echo "CRON_JOB_ID=$JOB_ID" >> "$LOG"
  hermes cron run "$JOB_ID" >> "$LOG" 2>&1
  sleep 12
  if [ -f /opt/data/smoke/cron-ran.txt ]; then
    cat /opt/data/smoke/cron-ran.txt >> "$LOG"
  else
    echo "CRON_MARKER_MISSING" >> "$LOG"
  fi
  hermes cron remove "$JOB_ID" >> "$LOG" 2>&1
else
  echo "CRON_JOB_ID_NOT_FOUND" >> "$LOG"
fi

echo "SMOKE_DONE" >> "$LOG"
cat "$LOG"
