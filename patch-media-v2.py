from pathlib import Path

p = Path('/app/hermes-simple.py')
s = p.read_text()

start = s.index('def cache_internal_media_from_text(text):')
end = s.index('\ndef is_image_generation_request(text):', start)

new = r'''def cache_internal_media_from_text(text):
    """Resolve Hermes MEDIA:/absolute/image tags into this web service's cache.

    Try the legacy dashboard media JSON endpoint first, then the restricted raw
    endpoint added by hermes-nosso-cloud. On success the literal MEDIA tag is
    removed so the frontend receives a normal /api/media/<id> imageUrl.
    """
    m = re.search(
        r'MEDIA:(/opt/data/(?:cache/images|image_cache)/[^\r\n\"\'<>]+?\.(?:png|jpe?g|gif|webp|bmp|svg|avif))(?=$|[\s\"\'),.;])',
        text or '',
        re.I,
    )
    if not m:
        return None, text

    media_path = m.group(1).strip()
    query = urllib.parse.urlencode({'path': media_path})
    auth = base64.b64encode((USER + ':' + PASSWORD).encode('utf-8')).decode('ascii')
    headers = {
        'Authorization': 'Basic ' + auth,
        'Accept': 'image/*,application/json;q=0.9,*/*;q=0.5',
        'User-Agent': 'HermesNossoWeb/2',
    }

    endpoints = [
        ADVANCED_URL.rstrip('/') + '/api/media?' + query,
        ADVANCED_URL.rstrip('/') + '/api/hermes-nosso/media?' + query,
    ]

    for endpoint in endpoints:
        try:
            req = urllib.request.Request(endpoint, headers=headers)
            with urllib.request.urlopen(req, timeout=25) as res:
                ctype = (res.headers.get('Content-Type', '') or '').split(';', 1)[0].strip().lower()
                raw = res.read(25 * 1024 * 1024 + 1)

            if len(raw) > 25 * 1024 * 1024:
                raise RuntimeError('generated_image_too_large')

            mime = ctype
            image_bytes = raw

            if ctype == 'application/json' or raw[:1] in (b'{', b'['):
                data = json.loads(raw.decode('utf-8'))
                data_url = str(data.get('data_url') or '')
                if not data_url.startswith('data:image/') or ';base64,' not in data_url:
                    raise RuntimeError('media_json_missing_data_url')
                header, encoded = data_url.split(',', 1)
                mime = header[5:].split(';', 1)[0].lower()
                image_bytes = base64.b64decode(encoded)

            if not str(mime).startswith('image/'):
                raise RuntimeError('media_response_not_image')

            mid = store_media(image_bytes, mime)
            cleaned = (text[:m.start()] + text[m.end():]).strip()
            print(f'[hermes-simple] cached Hermes MEDIA bytes={len(image_bytes)} endpoint={endpoint.split("?")[0]}', flush=True)
            return mid, cleaned
        except Exception as exc:
            print(f'[hermes-simple] Hermes MEDIA endpoint failed url={endpoint.split("?")[0]} type={type(exc).__name__}', flush=True)

    return None, text

'''

s = s[:start] + new + s[end + 1:]
p.write_text(s)
