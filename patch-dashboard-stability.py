from pathlib import Path

web_dist = Path("/opt/hermes/hermes_cli/web_dist")
index = web_dist / "index.html"
compat = web_dist / "hermes-dashboard-stability.js"

compat.write_text(r'''(() => {
  // Hermes dashboard stability shim for Railway/Chrome on Windows.
  // The embedded xterm WebGL renderer has known blank-render failures on some
  // desktop GPU/ANGLE combinations. Returning null for WebGL contexts makes
  // Hermes' existing try/catch fall back to the default canvas renderer.
  try {
    const originalGetContext = HTMLCanvasElement.prototype.getContext;
    if (!originalGetContext.__hermesNossoCanvasFallback) {
      const wrapped = function(type, ...args) {
        const kind = String(type || "").toLowerCase();
        if (kind === "webgl" || kind === "webgl2" || kind === "experimental-webgl") {
          return null;
        }
        return originalGetContext.call(this, type, ...args);
      };
      Object.defineProperty(wrapped, "__hermesNossoCanvasFallback", { value: true });
      HTMLCanvasElement.prototype.getContext = wrapped;
    }
  } catch (_) {
    // Never block dashboard startup if a browser prevents prototype patching.
  }

  // Rotate stale PTY attachment state once after this compatibility patch is
  // introduced. This avoids reattaching a terminal identity created by the
  // broken renderer while preserving normal Hermes session history.
  try {
    const marker = "hermes-nosso-dashboard-stability-20261003-v1";
    if (sessionStorage.getItem(marker) !== "done") {
      for (const key of Object.keys(localStorage)) {
        if (/hermes.*pty.*token/i.test(key) || /pty.*attach/i.test(key)) {
          localStorage.removeItem(key);
        }
      }
      sessionStorage.setItem(marker, "done");
    }
  } catch (_) {
  }
})();
''', encoding="utf-8")

html = index.read_text(encoding="utf-8")
tag = '<script src="/hermes-dashboard-stability.js?v=20261003-1"></script>'
if tag not in html:
    # Must run before the Vite module so WebGL is disabled before ChatPage
    # constructs xterm and loads @xterm/addon-webgl.
    html = html.replace("</head>", f"    {tag}\n  </head>")
index.write_text(html, encoding="utf-8")
