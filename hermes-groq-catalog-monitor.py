#!/usr/bin/env python3
"""Read-only GroqCloud catalogue monitor. No model switching or paid inference."""
import json
import os
import re
import time
import urllib.error
import urllib.request

CATALOG_URL = "https://api.groq.com/openai/v1/models"
MODEL_PATTERN = re.compile(r"(?i)(?:^qwen/|^llama[-/]|^meta-llama/)")
EXCLUDE = re.compile(r"(?i)(?:guard|safety|moderation)")
MAX_BYTES = 256 * 1024
CHECK_INTERVAL = 6 * 60 * 60
_cache = {"until": 0.0, "result": None}


def candidate_ids(data):
    """Return active, general-purpose Qwen/Llama IDs, not proof of Free access."""
    records = data.get("data", []) if isinstance(data, dict) else []
    if not isinstance(records, list) or len(records) > 1000:
        raise ValueError("invalid_catalog")
    ids = set()
    for row in records:
        if not isinstance(row, dict) or row.get("active") is False:
            continue
        name = row.get("id")
        if isinstance(name, str) and len(name) <= 128 and MODEL_PATTERN.search(name) and not EXCLUDE.search(name):
            ids.add(name)
    return sorted(ids)


def check_catalog(*, opener=None, now=None):
    """Cached, bounded read-only check; credentials never reach logs or response."""
    now = time.monotonic() if now is None else now
    if now < _cache["until"]:
        return _cache["result"]
    token = os.getenv("GROQ_API_KEY", "")
    if not re.fullmatch(r"gsk_[A-Za-z0-9_-]{20,}", token):
        return {"ok": False, "error": "groq_not_configured"}
    req = urllib.request.Request(CATALOG_URL, headers={
        "Authorization": "Bearer " + token, "Accept": "application/json"
    })
    try:
        with (opener or urllib.request.urlopen)(req, timeout=5) as resp:
            raw = resp.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError("catalog_too_large")
        result = {"ok": True, "models": candidate_ids(json.loads(raw)),
                  "free_status": "unverified", "performance": "unverified"}
        _cache.update(until=now + CHECK_INTERVAL, result=result)
        return result
    except (urllib.error.URLError, OSError, ValueError, UnicodeError, TypeError):
        return {"ok": False, "error": "catalog_unavailable"}


if __name__ == "__main__":
    print(json.dumps(check_catalog(), ensure_ascii=False))
