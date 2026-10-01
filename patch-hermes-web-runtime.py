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

# Serve generated images to the dashboard. Hermes tools emit MEDIA:/absolute/path,
# but the dashboard PTY currently renders that token as plain text. Restrict this
# endpoint to the two image cache roots used by our Railway image.
media_marker = "def _hermes_nosso_media_file("
if media_marker not in text:
    # The injected media route uses pathlib.Path. Upstream sessions.py does not
    # consistently import it across Hermes Agent releases, so make the patch
    # self-contained and idempotent.
    if "from pathlib import Path" not in text:
        import_lines = text.splitlines()
        insert_at = 0
        if import_lines and import_lines[0].startswith("from __future__ import"):
            insert_at = 1
        import_lines.insert(insert_at, "from pathlib import Path")
        text = "\n".join(import_lines) + ("\n" if text.endswith("\n") else "")

    import_anchor = "from fastapi.responses import StreamingResponse"
    if import_anchor in text:
        text = text.replace(
            import_anchor,
            import_anchor + ", FileResponse",
            1,
        )
    elif "from fastapi.responses import FileResponse" not in text:
        raise SystemExit("sessions patch: fastapi.responses import marker not found")

    route_anchor = '_NOT_FOUND = "Session not found"\n'
    media_route = r'''

_HERMES_NOSSO_MEDIA_ROOTS = (
    Path("/opt/data/cache/images"),
    Path("/opt/data/image_cache"),
)


def _hermes_nosso_media_file(path: str):
    """Return one generated image while preventing arbitrary filesystem reads."""
    try:
        requested = Path(path)
        if not requested.is_absolute():
            raise ValueError("absolute path required")
        resolved = requested.resolve(strict=True)
    except (OSError, RuntimeError, ValueError):
        raise HTTPException(status_code=404, detail="Generated image not found")

    allowed = False
    for root in _HERMES_NOSSO_MEDIA_ROOTS:
        try:
            root_resolved = root.resolve(strict=False)
            if resolved == root_resolved or root_resolved in resolved.parents:
                allowed = True
                break
        except (OSError, RuntimeError):
            continue

    if not allowed or not resolved.is_file():
        raise HTTPException(status_code=404, detail="Generated image not found")

    suffix = resolved.suffix.lower()
    media_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
        ".svg": "image/svg+xml",
        ".avif": "image/avif",
    }
    media_type = media_types.get(suffix)
    if media_type is None:
        raise HTTPException(status_code=415, detail="Unsupported generated image type")

    return FileResponse(
        str(resolved),
        media_type=media_type,
        filename=resolved.name,
        content_disposition_type="inline",
        headers={"Cache-Control": "private, max-age=3600"},
    )


@manage_router.get("/api/hermes-nosso/media")
def hermes_nosso_media(path: str = Query(..., min_length=1)):
    return _hermes_nosso_media_file(path)
'''
    if route_anchor not in text:
        raise SystemExit("sessions patch: route insertion marker not found")
    text = text.replace(route_anchor, route_anchor + media_route + "\n", 1)

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
  }
})();
''', encoding="utf-8")

media_js = web_dist / "hermes-media-renderer.js"
media_js.write_text(r'''(() => {
  const VERSION = "20261001-1";
  const MEDIA_RE = /MEDIA:((?:\/opt\/data\/(?:cache\/images|image_cache)\/)[^\n\r\"'<>]+?\.(?:png|jpe?g|webp|gif|svg|avif))/ig;

  function makeImage(path) {
    const wrap = document.createElement("span");
    wrap.className = "hermes-nosso-media";
    wrap.dataset.hermesNossoMedia = VERSION;
    wrap.style.display = "block";
    wrap.style.margin = "10px 0";

    const img = document.createElement("img");
    img.src = "/api/hermes-nosso/media?path=" + encodeURIComponent(path);
    img.alt = "Imagem gerada pelo Hermes";
    img.loading = "lazy";
    img.style.display = "block";
    img.style.maxWidth = "min(100%, 1024px)";
    img.style.maxHeight = "75vh";
    img.style.objectFit = "contain";
    img.style.borderRadius = "12px";
    img.style.boxShadow = "0 1px 3px rgba(0,0,0,.18)";

    const fallback = document.createElement("a");
    fallback.href = img.src;
    fallback.target = "_blank";
    fallback.rel = "noopener noreferrer";
    fallback.textContent = "Abrir imagem gerada";
    fallback.style.display = "none";
    fallback.style.fontSize = "13px";

    img.addEventListener("error", () => {
      img.style.display = "none";
      fallback.style.display = "inline";
    });

    wrap.appendChild(img);
    wrap.appendChild(fallback);
    return wrap;
  }

  function renderTextNode(node) {
    if (!node || !node.parentElement) return;
    if (node.parentElement.closest("script,style,textarea,input,[data-hermes-nosso-media]")) return;
    const value = node.nodeValue || "";
    if (!value.includes("MEDIA:")) return;

    MEDIA_RE.lastIndex = 0;
    let match;
    let last = 0;
    let changed = false;
    const frag = document.createDocumentFragment();

    while ((match = MEDIA_RE.exec(value)) !== null) {
      changed = true;
      if (match.index > last) frag.appendChild(document.createTextNode(value.slice(last, match.index)));
      frag.appendChild(makeImage(match[1].trim()));
      last = MEDIA_RE.lastIndex;
    }
    if (!changed) return;
    if (last < value.length) frag.appendChild(document.createTextNode(value.slice(last)));
    node.parentNode.replaceChild(frag, node);
  }

  function scan(root) {
    if (!root) return;
    if (root.nodeType === Node.TEXT_NODE) {
      renderTextNode(root);
      return;
    }
    if (root.nodeType !== Node.ELEMENT_NODE && root.nodeType !== Node.DOCUMENT_NODE) return;
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const nodes = [];
    let current;
    while ((current = walker.nextNode())) nodes.push(current);
    for (const node of nodes) renderTextNode(node);
  }

  function start() {
    scan(document.body);
    const observer = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        for (const node of mutation.addedNodes) scan(node);
      }
    });
    observer.observe(document.body, { childList: true, subtree: true, characterData: true });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, { once: true });
  } else {
    start();
  }
})();
''', encoding="utf-8")

index = web_dist / "index.html"
html = index.read_text(encoding="utf-8")
recovery_tag = '<script src="/hermes-ui-recovery.js?v=20260929-3"></script>'
if recovery_tag not in html:
    html = html.replace("</head>", f"    {recovery_tag}\n  </head>")
media_tag = '<script src="/hermes-media-renderer.js?v=20261001-1"></script>'
if media_tag not in html:
    html = html.replace("</head>", f"    {media_tag}\n  </head>")
index.write_text(html, encoding="utf-8")
