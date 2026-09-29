#!/bin/sh
set -eu

if [ -n "${MATRIX_API_KEY:-}" ]; then
  python3 - <<'PY'
import json, os, urllib.request, urllib.error

key = os.environ.get("MATRIX_API_KEY", "")
base = "https://matrix.dgsis.com.br"
model = "claude-opus-5"

def req(path, payload=None):
    headers = {"Authorization": f"Bearer {key}", "Accept": "application/json"}
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode()
    r = urllib.request.Request(base + path, data=data, headers=headers, method="POST" if data else "GET")
    try:
        with urllib.request.urlopen(r, timeout=20) as resp:
            body = resp.read(1024 * 1024)
            return resp.status, body
    except urllib.error.HTTPError as e:
        return e.code, e.read(8192)
    except Exception as e:
        print("MATRIX_PROBE_ERROR type=" + type(e).__name__)
        return None, b""

status, body = req("/v1/models")
present = False
if status == 200:
    try:
        data = json.loads(body)
        ids = [str(x.get("id","")) for x in data.get("data",[]) if isinstance(x,dict)]
        present = model in ids
    except Exception:
        pass
print(f"MATRIX_MODELS status={status} model_present={str(present).lower()}")

if status == 200:
    status2, body2 = req("/v1/chat/completions", {
        "model": model,
        "messages": [{"role":"user","content":"Reply only OK"}],
        "max_tokens": 4,
        "temperature": 0
    })
    returned = ""
    if status2 == 200:
        try:
            returned = str(json.loads(body2).get("model",""))
        except Exception:
            pass
    print(f"MATRIX_CHAT status={status2} returned_model={returned[:120]}")
PY
fi

echo "[hermes-web] validating nginx configuration"
nginx -t
echo "[hermes-web] starting nginx on port 9119"
exec nginx -g 'daemon off;'
