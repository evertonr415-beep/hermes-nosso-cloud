from pathlib import Path

p = Path('/app/hermes-simple.py')
s = p.read_text()

start = s.index('def _bing_image_candidates(query):')
end = s.index('\ndef _download_reference_image(url):', start)

new = r'''def _safe_public_url(url):
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ('http', 'https'):
            return False
        host = (parsed.hostname or '').lower().strip('.')
        if not host or host in ('localhost', '127.0.0.1', '::1'):
            return False
        if host.endswith('.railway.internal') or host.endswith('.local'):
            return False
        return True
    except Exception:
        return False


def _bing_image_candidates(query):
    """Best-effort direct image candidates from Bing Images.

    Bing changes its markup often, so failure here is expected and callers must
    continue to web-page and Wikimedia fallbacks.
    """
    import html as html_lib
    url = 'https://www.bing.com/images/search?' + urllib.parse.urlencode({
        'q': query,
        'form': 'HDRSC3',
        'first': '1',
    })
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36',
        'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.7',
    })
    try:
        with urllib.request.urlopen(req, timeout=20) as res:
            page = res.read(3 * 1024 * 1024).decode('utf-8', 'ignore')
    except Exception:
        return []

    candidates = []
    patterns = [
        r'&quot;murl&quot;:&quot;(.*?)&quot;',
        r'"murl"\\s*:\\s*"(.*?)"',
        r'murl\\x22:\\x22(.*?)\\x22',
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, page, re.I):
            raw = html_lib.unescape(match.group(1))
            raw = raw.replace('\\/', '/').replace('\\u002f', '/').replace('\\u003a', ':')
            if _safe_public_url(raw) and raw not in candidates:
                candidates.append(raw)
            if len(candidates) >= 24:
                return candidates
    return candidates


def _bing_web_pages(query):
    """Return public result pages from Bing web search."""
    import html as html_lib
    url = 'https://www.bing.com/search?' + urllib.parse.urlencode({'q': query, 'count': '12'})
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36',
        'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.7',
    })
    try:
        with urllib.request.urlopen(req, timeout=20) as res:
            page = res.read(2 * 1024 * 1024).decode('utf-8', 'ignore')
    except Exception:
        return []

    out = []
    for m in re.finditer(r'<li[^>]+class="[^"]*b_algo[^"]*"[\\s\\S]*?<a[^>]+href="([^"]+)"', page, re.I):
        u = html_lib.unescape(m.group(1))
        if _safe_public_url(u) and u not in out:
            out.append(u)
        if len(out) >= 12:
            break
    if not out:
        for m in re.finditer(r'<a[^>]+href="(https?://[^"]+)"', page, re.I):
            u = html_lib.unescape(m.group(1))
            host = (urllib.parse.urlparse(u).hostname or '').lower()
            if ('bing.com' in host or 'microsoft.com' in host):
                continue
            if _safe_public_url(u) and u not in out:
                out.append(u)
            if len(out) >= 12:
                break
    return out


def _page_image_candidates(page_url):
    """Extract representative images from a public result page."""
    import html as html_lib
    req = urllib.request.Request(page_url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml',
        'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.7',
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            ctype = (res.headers.get('Content-Type', '') or '').lower()
            if 'html' not in ctype:
                return []
            page = res.read(2 * 1024 * 1024).decode('utf-8', 'ignore')
    except Exception:
        return []

    vals = []
    patterns = [
        r'<meta[^>]+(?:property|name)=["\\'](?:og:image|twitter:image|twitter:image:src)["\\'][^>]+content=["\\']([^"\\']+)',
        r'<meta[^>]+content=["\\']([^"\\']+)["\\'][^>]+(?:property|name)=["\\'](?:og:image|twitter:image|twitter:image:src)["\\']',
        r'<img[^>]+src=["\\']([^"\\']+)["\\']',
    ]
    for pattern in patterns:
        for m in re.finditer(pattern, page, re.I):
            raw = html_lib.unescape(m.group(1)).strip()
            u = urllib.parse.urljoin(page_url, raw)
            if _safe_public_url(u) and u not in vals:
                vals.append(u)
            if len(vals) >= 18:
                return vals
    return vals


def _wikimedia_image_candidates(query):
    """Use Wikimedia Commons MediaSearch as a public fallback."""
    api = 'https://commons.wikimedia.org/w/api.php?' + urllib.parse.urlencode({
        'action': 'query',
        'generator': 'search',
        'gsrsearch': query,
        'gsrnamespace': '6',
        'gsrlimit': '8',
        'prop': 'imageinfo',
        'iiprop': 'url',
        'iiurlwidth': '900',
        'format': 'json',
        'origin': '*',
    })
    req = urllib.request.Request(api, headers={'User-Agent': 'HermesNosso/1.0 image-reference'})
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            data = json.load(res)
    except Exception:
        return []
    out = []
    pages = ((data.get('query') or {}).get('pages') or {})
    for page in pages.values():
        for info in (page.get('imageinfo') or []):
            for key in ('thumburl', 'url'):
                u = str(info.get(key) or '')
                if _safe_public_url(u) and u not in out:
                    out.append(u)
    return out


def _reference_candidate_urls(query):
    out = []
    def add_many(items):
        for u in items:
            if _safe_public_url(u) and u not in out:
                out.append(u)

    add_many(_bing_image_candidates(query))
    add_many(_wikimedia_image_candidates(query))

    # Search normal web pages and prefer their declared social/hero image.
    for page_url in _bing_web_pages(query + ' foto oficial')[:10]:
        add_many(_page_image_candidates(page_url))
        if len(out) >= 36:
            break

    # One broader query helps when municipal pages do not rank for "foto oficial".
    if len(out) < 6:
        for page_url in _bing_web_pages(query)[:10]:
            add_many(_page_image_candidates(page_url))
            if len(out) >= 36:
                break
    return out[:40]

'''

s = s[:start] + new + s[end:]

start2 = s.index('def find_real_person_reference(query):')
end2 = s.index('\ndef build_reference_sheet(people):', start2)
new2 = r'''def find_real_person_reference(query):
    last = None
    candidates = _reference_candidate_urls(query)
    print(f'[hermes-simple] reference search query={query[:90]!r} candidates={len(candidates)}', flush=True)
    for url in candidates:
        try:
            return _download_reference_image(url)
        except Exception as exc:
            last = exc
    raise RuntimeError('no_reference_image_found:' + (type(last).__name__ if last else 'empty_search'))

'''
s = s[:start2] + new2 + s[end2 + 1:]

p.write_text(s)
