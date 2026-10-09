#!/usr/bin/env python3
"""Owner-approved public-page inspection, HTTP and connectivity diagnostics.

No unrestricted proxy, recursive spidering, cookie harvesting or arbitrary
network probing. Administrators must explicitly allow hostname targets via
HERMES_AUDIT_ALLOWED_HOSTS (comma-separated). Disabled until configured.
"""
import concurrent.futures
import html.parser
import ipaddress
import json
import os
import re
import socket
import urllib.parse
import urllib.request

MAX_BYTES = 196608
PORTS = (80, 443, 554)
ALLOWED_HEADERS = {"accept", "content-type", "user-agent"}


def _approved_hostname(hostname):
    allow = {x.strip().lower() for x in os.getenv("HERMES_AUDIT_ALLOWED_HOSTS", "").split(",") if x.strip()}
    if not hostname or hostname.lower() not in allow:
        raise ValueError("host_not_approved")
    if hostname in ("localhost",) or hostname.endswith((".local", ".internal")):
        raise ValueError("internal_host_denied")
    # The approved hostname must resolve only to globally routable addresses:
    # never connect to arbitrary private networks, cloud metadata or loopback.
    infos = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    ips = {item[4][0] for item in infos}
    if not ips or any(not ipaddress.ip_address(ip).is_global for ip in ips):
        raise ValueError("unsafe_address")
    return sorted(ips)


def _validate_url(url):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or parsed.username or parsed.password or parsed.port not in (None, 443):
        raise ValueError("https_only")
    if parsed.fragment or len(url) > 2048:
        raise ValueError("invalid_url")
    _approved_hostname(parsed.hostname)
    return url


class HtmlOutline(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.nodes = []
        self.styles = []
        self._style = False

    def handle_starttag(self, tag, attrs):
        if len(self.nodes) < 240:
            safe = dict(attrs)
            self.nodes.append({"tag": tag, "id": str(safe.get("id", ""))[:70],
                               "class": str(safe.get("class", ""))[:140]})
        if tag == "style":
            self._style = True

    def handle_endtag(self, tag):
        if tag == "style":
            self._style = False

    def handle_data(self, data):
        if self._style and sum(map(len, self.styles)) < 20000:
            self.styles.append(data[:6000])


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("redirect_blocked")


def inspect_public_page(url):
    """Inspect a permitted public HTTPS page; return bounded structural data."""
    _validate_url(url)
    request = urllib.request.Request(url, headers={"User-Agent": "HermesAudit/1.0", "Accept": "text/html"})
    # No redirects and no ambient cookie jar; responses are untrusted data.
    with urllib.request.build_opener(NoRedirect()).open(request, timeout=6) as response:
        mime = response.headers.get("Content-Type", "").lower()
        if "text/html" not in mime:
            raise ValueError("html_only")
        raw = response.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("oversized_html")
    decoded = raw.decode("utf-8", "replace")
    parser = HtmlOutline()
    parser.feed(decoded)
    return {"source": url, "elements": parser.nodes, "inline_css": "".join(parser.styles)[:20000],
            "note": "Public HTML structure only; JS-rendered content and copyrighted assets not reproduced"}


def authorized_http_request(url, *, method="GET", headers=None):
    """Bounded read-only client for explicitly allowlisted public HTTPS APIs."""
    _validate_url(url)
    if method not in ("GET", "HEAD"):
        raise ValueError("read_only")
    headers = headers or {}
    if not isinstance(headers, dict) or len(headers) > 6:
        raise ValueError("invalid_headers")
    clean = {}
    for key, value in headers.items():
        if not isinstance(key, str) or key.lower() not in ALLOWED_HEADERS or not isinstance(value, str) or len(value) > 200:
            raise ValueError("header_not_allowed")
        clean[key] = value
    # No arbitrary Authorization/Cookie forwarding from a model-controlled request.
    req = urllib.request.Request(url, method=method, headers=clean)
    with urllib.request.build_opener(NoRedirect()).open(req, timeout=6) as response:
        raw = response.read(MAX_BYTES + 1)
        status = response.status
    if len(raw) > MAX_BYTES:
        raise ValueError("oversized_response")
    return {"status": status, "body": raw.decode("utf-8", "replace")[:12000]}


def check_connectivity(hostname, ports=(80, 443, 554)):
    """Concurrent TCP reachability for administrator-approved *public* hosts.

    Not a discovery scanner. No subnet sweeps, no arbitrary ports, no RTSP
    authentication and no host enumeration. Returns status only.
    """
    addresses = _approved_hostname(hostname)
    if not isinstance(ports, (list, tuple)) or len(ports) > 3 or any(type(p) is not int or p not in PORTS for p in ports):
        raise ValueError("ports_not_allowed")

    def probe(port):
        try:
            with socket.create_connection((addresses[0], port), timeout=2):
                return {"port": port, "reachable": True}
        except OSError:
            return {"port": port, "reachable": False}

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        return {"host": hostname, "results": list(pool.map(probe, ports))}
