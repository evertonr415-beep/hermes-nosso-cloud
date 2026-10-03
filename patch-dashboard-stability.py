from pathlib import Path

web_dist = Path("/opt/hermes/hermes_cli/web_dist")
index = web_dist / "index.html"

# Keep the Hermes dashboard as close to upstream as possible. The custom
# recovery/media scripts mutate local/session storage and live DOM nodes outside
# React. On ChatPage this can render briefly and then crash/unmount the React
# tree, leaving only the application background visible.
html = index.read_text(encoding="utf-8")
for tag in (
    '<script src="/hermes-dashboard-stability.js?v=20261003-1"></script>',
    '<script src="/hermes-dashboard-stability.js?v=20261003-2"></script>',
    '<script src="/hermes-ui-recovery.js?v=20260929-3"></script>',
    '<script src="/hermes-media-renderer.js?v=20261001-1"></script>',
):
    html = html.replace("    " + tag + "\n", "").replace(tag, "")
index.write_text(html, encoding="utf-8")

# Remove the generated browser shims from the final image. The backend media
# route remains available; only the unsafe client-side DOM instrumentation is
# disabled until it can be reimplemented inside React.
for name in (
    "hermes-dashboard-stability.js",
    "hermes-ui-recovery.js",
    "hermes-media-renderer.js",
):
    try:
        (web_dist / name).unlink()
    except FileNotFoundError:
        pass
