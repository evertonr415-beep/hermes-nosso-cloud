#!/usr/bin/env python3
"""Isolated, read-only agent-browser worker for Hermes Cloud experiments.

The worker is intentionally a separate service. It accepts only HTTPS URLs on
an explicit exact-host allowlist, requires a bearer token, and exposes no
click/eval/download/file or arbitrary command endpoint.
"""
import hmac
import ipaddress
import json
import os
import re
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

PORT = int(os.getenv("PORT", "8080"))
TOKEN = os.getenv("BROWSER_WORKER_TOKEN", "")
RAW_ALLOWED = os.getenv("AGENT_BROWSER_ALLOWED_DOMAINS", "")
MAX_BODY = 8192
MAX_OUTPUT = 12000
COMMAND_TIMEOUT = 18
BROWSER_LOCK = threading.Lock()


def allowed_hosts():
    hosts = []
    for raw in RAW_ALLOWED.split(","):
        host = raw.strip().lower().rstrip(".")
        if not host:
            continue
        if (len(host) > 253 or not re.fullmatch(
                r"(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)(?:\.(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?))*",
                host)):
            raise ValueError("invalid_allowed_domain")
        try:
            ipaddress.ip_address(host)
            raise ValueError("ip_literals_not_allowed")
        except ValueError as exc:
            if str(exc) == "ip_literals_not_allowed":
                raise
        if "." not in host or host in {"localhost"} or host.endswith((".local", ".internal", ".localhost")):
            raise ValueError("local_host_not_allowed")
        if host not in hosts:
            hosts.append(host)
    return hosts


def validate_target(raw_url, hosts):
    if not isinstance(raw_url, str) or len(raw_url) > 2048:
        raise ValueError("invalid_url")
    try:
        parsed = urlsplit(raw_url)
        hostname = (parsed.hostname or "").lower().rstrip(".")
        port = parsed.port
    except ValueError as exc:
        raise ValueError("invalid_url") from exc
    if parsed.scheme != "https" or not hostname or parsed.username or parsed.password:
        raise ValueError("https_url_required")
    if port not in (None, 443) or hostname not in hosts:
        raise ValueError("domain_not_allowed")
    if parsed.fragment:
        raw_url = raw_url.split("#", 1)[0]
    return raw_url


def read_page(url, hosts):
    # Use agent-browser's bounded, read-only fetch mode for the first validated
    # integration. It avoids the persistent Chromium daemon lifecycle while
    # still applying agent-browser's domain guard to navigation and redirects.
    # This mode reads server-delivered page text; it does not execute page JS.
    domains = ",".join(hosts)
    with BROWSER_LOCK:
        try:
            print("[browser-worker] read operation started", flush=True)
            result = subprocess.run(
                ["agent-browser", "--allowed-domains", domains, "read", url],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=COMMAND_TIMEOUT, check=False,
            )
            print(f"[browser-worker] read operation exited: {result.returncode}", flush=True)
            if result.returncode:
                return {"error": "navigation_failed"}
            text = (result.stdout or "").strip()
            if not text:
                return {"error": "empty_page"}
            return {
                "url": url,
                "content": text[:MAX_OUTPUT],
                "truncated": len(text) > MAX_OUTPUT,
                "trust": "untrusted_web_content",
            }
        except subprocess.TimeoutExpired:
            return {"error": "browser_timeout"}
        except OSError:
            return {"error": "browser_unavailable"}
        except Exception as exc:
            # Never let an unexpected CLI/output exception tear down the HTTP
            # response. Log only the exception type, never URL or page text.
            print(f"[browser-worker] browser operation failed: {type(exc).__name__}", flush=True)
            return {"error": "browser_internal_error"}


class Handler(BaseHTTPRequestHandler):
    server_version = "HermesBrowserWorker/0.1"

    def log_message(self, fmt, *args):
        # Avoid logging URLs, authorization headers, or page contents.
        print("[browser-worker] request handled", flush=True)

    def _send(self, status, payload):
        data = json.dumps(payload, ensure_ascii=True).encode("utf-8")
        print(f"[browser-worker] sending HTTP {status} ({len(data)} bytes)", flush=True)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path != "/health":
            self._send(404, {"error": "not_found"})
            return
        self._send(200, {"ok": True, "service": "isolated-browser-worker"})

    def do_POST(self):
        if self.path != "/read":
            self._send(404, {"error": "not_found"})
            return
        supplied = self.headers.get("Authorization", "")
        expected = "Bearer " + TOKEN
        if not TOKEN or not hmac.compare_digest(supplied, expected):
            self._send(401, {"error": "unauthorized"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send(400, {"error": "invalid_content_length"})
            return
        if length < 1 or length > MAX_BODY:
            self._send(413, {"error": "request_too_large"})
            return
        try:
            body = json.loads(self.rfile.read(length))
            if not isinstance(body, dict) or set(body) != {"url"}:
                raise ValueError("invalid_payload")
            hosts = allowed_hosts()
            if not hosts:
                self._send(503, {"error": "allowlist_not_configured"})
                return
            url = validate_target(body["url"], hosts)
        except (ValueError, TypeError, json.JSONDecodeError):
            self._send(400, {"error": "invalid_request_or_domain_not_allowed"})
            return
        result = read_page(url, hosts)
        self._send(200 if "content" in result else 502, result)


def main():
    if len(TOKEN) < 32:
        raise SystemExit("BROWSER_WORKER_TOKEN must be configured with at least 32 characters")
    try:
        hosts = allowed_hosts()
    except ValueError:
        raise SystemExit("AGENT_BROWSER_ALLOWED_DOMAINS contains an invalid host")
    if not hosts:
        raise SystemExit("AGENT_BROWSER_ALLOWED_DOMAINS must contain exact public hostnames")
    print("[browser-worker] starting; read-only mode enabled", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
