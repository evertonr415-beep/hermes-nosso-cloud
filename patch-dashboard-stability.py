from pathlib import Path

web_dist = Path("/opt/hermes/hermes_cli/web_dist")
index = web_dist / "index.html"
compat = web_dist / "hermes-dashboard-stability.js"

# Revert the experimental WebGL interception. The native Hermes dashboard
# already handles renderer selection; monkey-patching canvas.getContext can
# make ChatPage fail during xterm/WebGL addon initialization and leave only the
# application background visible.
html = index.read_text(encoding="utf-8")
for tag in (
    '<script src="/hermes-dashboard-stability.js?v=20261003-1"></script>',
    '<script src="/hermes-dashboard-stability.js?v=20261003-2"></script>',
):
    html = html.replace("    " + tag + "\n", "").replace(tag, "")
index.write_text(html, encoding="utf-8")

try:
    compat.unlink()
except FileNotFoundError:
    pass
