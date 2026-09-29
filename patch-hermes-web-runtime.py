from pathlib import Path

sessions = Path("/opt/hermes/hermes_cli/web_routers/sessions.py")
text = sessions.read_text(encoding="utf-8")

old_active = '''def _is_active(row: dict, now: float) -> bool:
    return (
        row.get("ended_at") is None
        and (now - row.get("last_active", row.get("started_at", 0))) < _ACTIVE_WINDOW_S)
'''

new_active = '''def _client_session_row(row: dict) -> dict:
    """Normalize session metadata at the HTTP boundary without mutating state.db."""
    out = row

    def _number(name: str, fallback=0):
        value = out.get(name)
        if value is None or value == "":
            out[name] = fallback
            return
        try:
            out[name] = float(value) if name in ("started_at", "last_active") else int(value)
        except (TypeError, ValueError):
            out[name] = fallback

    _number("message_count", 0)
    _number("tool_call_count", 0)
    _number("input_tokens", 0)
    _number("output_tokens", 0)

    started = out.get("started_at")
    try:
        started = float(started)
    except (TypeError, ValueError):
        started = 0.0
    out["started_at"] = started

    last_active = out.get("last_active")
    try:
        last_active = float(last_active)
    except (TypeError, ValueError):
        last_active = started
    out["last_active"] = last_active or started

    out["id"] = str(out.get("id") or "")
    out["source"] = str(out.get("source") or "unknown")
    if out.get("preview") is None:
        out["preview"] = ""
    return out


def _is_active(row: dict, now: float) -> bool:
    row = _client_session_row(row)
    return (
        row.get("ended_at") is None
        and (now - row["last_active"]) < _ACTIVE_WINDOW_S)
'''

if old_active not in text and "def _client_session_row(row: dict)" not in text:
    raise SystemExit("sessions patch: _is_active marker not found")
if old_active in text:
    text = text.replace(old_active, new_active, 1)

old_detail = '''        if not session:
            raise HTTPException(status_code=404, detail=_NOT_FOUND)
        # Always stamp the owner: unowned default-profile rows made multi-profile
'''
new_detail = '''        if not session:
            raise HTTPException(status_code=404, detail=_NOT_FOUND)
        _client_session_row(session)
        # Always stamp the owner: unowned default-profile rows made multi-profile
'''
if old_detail in text:
    text = text.replace(old_detail, new_detail, 1)
# Detail normalization is optional for compatibility with upstream refactors.

sessions.write_text(text, encoding="utf-8")

web_dist = Path("/opt/hermes/hermes_cli/web_dist")
recovery = web_dist / "hermes-ui-recovery.js"
recovery.write_text(r'''(() => {
  const marker = "hermes-nosso-ui-recovery-20260929-v3";
  try {
    if (localStorage.getItem(marker) === "done") return;

    const shouldReset = (key) =>
      /(?:^|[._-])(pty|chat|session|sessions|profile|workspace)(?:$|[._-])/i.test(key) ||
      key === "hermes-chat-panel-collapsed";

    for (const key of Object.keys(localStorage)) {
      if (key !== marker && shouldReset(key)) localStorage.removeItem(key);
    }
    for (const key of Object.keys(sessionStorage)) {
      if (shouldReset(key)) sessionStorage.removeItem(key);
    }

    localStorage.setItem(marker, "done");
  } catch (_) {
    // Browser storage may be unavailable; never block the app.
  }
})();
''', encoding="utf-8")

index = web_dist / "index.html"
html = index.read_text(encoding="utf-8")
tag = '<script src="/hermes-ui-recovery.js?v=20260929-3"></script>'
if tag not in html:
    html = html.replace("</head>", f"    {tag}\n  </head>")
index.write_text(html, encoding="utf-8")
