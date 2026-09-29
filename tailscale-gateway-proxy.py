import json
import os
import socket
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TARGET = os.environ.get("HERMES_LOCAL_TARGET", "http://100.91.1.35:8642").rstrip("/")
HTTP_PROXY = os.environ.get("TAILSCALE_HTTP_PROXY", "http://127.0.0.1:1056")
LISTEN_PORT = int(os.environ.get("PORT", "8642"))

HOP_BY_HOP = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "transfer-encoding", "upgrade", "host", "content-length",
}

opener = urllib.request.build_opener(
    urllib.request.ProxyHandler({"http": HTTP_PROXY, "https": HTTP_PROXY})
)

class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        print("[tailscale-gateway] " + (fmt % args), flush=True)

    def _json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _proxy(self):
        if self.path == "/health":
            return self._json(200, {"ok": True, "service": "hermes-tailscale-gateway"})

        url = TARGET + self.path
        length = int(self.headers.get("Content-Length", "0") or "0")
        body = self.rfile.read(length) if length else None

        headers = {}
        for k, v in self.headers.items():
            if k.lower() not in HOP_BY_HOP:
                headers[k] = v
        headers["Host"] = urllib.parse.urlsplit(TARGET).netloc

        req = urllib.request.Request(
            url,
            data=body,
            headers=headers,
            method=self.command,
        )

        try:
            resp = opener.open(req, timeout=120)
        except urllib.error.HTTPError as exc:
            resp = exc
        except Exception as exc:
            return self._json(502, {
                "ok": False,
                "error": type(exc).__name__,
                "detail": str(exc)[:200],
            })

        self.send_response(resp.status)
        for k, v in resp.headers.items():
            if k.lower() not in HOP_BY_HOP:
                self.send_header(k, v)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

        try:
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                self.wfile.write(chunk)
                self.wfile.flush()
        finally:
            resp.close()

    do_GET = _proxy
    do_POST = _proxy
    do_PUT = _proxy
    do_PATCH = _proxy
    do_DELETE = _proxy
    do_OPTIONS = _proxy

if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", LISTEN_PORT), Handler)
    print(f"[tailscale-gateway] listening on 0.0.0.0:{LISTEN_PORT}", flush=True)
    server.serve_forever()
