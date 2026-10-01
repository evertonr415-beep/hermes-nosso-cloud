from pathlib import Path

p = Path('/app/hermes-simple.py')
s = p.read_text()

s = s.replace(
    'import base64, hmac, json, os, time, threading, urllib.request, urllib.error, re, uuid, tempfile, subprocess',
    'import base64, hmac, json, os, time, threading, urllib.request, urllib.error, urllib.parse, re, uuid, tempfile, subprocess'
)

anchor = 'def response_text(data):\n'
helper = '''def cache_internal_media_from_text(text):
    m = re.search(r'MEDIA:(/[^\\r\\n]+?\\.(?:png|jpe?g|gif|webp|bmp|svg))(?=$|[\\s),.;])', text or '', re.I)
    if not m:
        return None, text
    media_path = m.group(1).strip()
    try:
        query = urllib.parse.urlencode({'path': media_path})
        auth = base64.b64encode((USER + ':' + PASSWORD).encode('utf-8')).decode('ascii')
        req = urllib.request.Request(
            ADVANCED_URL.rstrip('/') + '/api/media?' + query,
            headers={'Authorization': 'Basic ' + auth, 'Accept': 'application/json'},
        )
        with urllib.request.urlopen(req, timeout=20) as res:
            data = json.load(res)
        data_url = str(data.get('data_url') or '')
        if not data_url.startswith('data:image/') or ';base64,' not in data_url:
            return None, text
        header, encoded = data_url.split(',', 1)
        mime = header[5:].split(';', 1)[0].lower()
        raw = base64.b64decode(encoded)
        if len(raw) > 25 * 1024 * 1024:
            return None, text
        mid = store_media(raw, mime)
        cleaned = (text[:m.start()] + text[m.end():]).strip()
        print(f'[hermes-simple] cached Hermes MEDIA bytes={len(raw)}', flush=True)
        return mid, cleaned
    except Exception as exc:
        print(f'[hermes-simple] Hermes MEDIA fetch skipped type={type(exc).__name__}', flush=True)
        return None, text

'''

if 'def cache_internal_media_from_text(text):' not in s:
    s = s.replace(anchor, helper + anchor)

old = '''            route_meta=classify_route(text, route)
            image_url=None
            if route_meta.get("category")=="Imagem":
                mid=cache_image_from_text(out)
                if mid:
                    image_url="/api/media/"+mid
            return self.sendb(200,json.dumps({"text":out,"via":via,"routeMeta":route_meta,"imageUrl":image_url},ensure_ascii=False))
'''
new = '''            route_meta=classify_route(text, route)
            image_url=None
            internal_mid, cleaned_out = cache_internal_media_from_text(out)
            if internal_mid:
                image_url="/api/media/"+internal_mid
                out=cleaned_out or "Imagem gerada."
            elif route_meta.get("category")=="Imagem":
                mid=cache_image_from_text(out)
                if mid:
                    image_url="/api/media/"+mid
            return self.sendb(200,json.dumps({"text":out,"via":via,"routeMeta":route_meta,"imageUrl":image_url},ensure_ascii=False))
'''

if old not in s:
    raise SystemExit('image response anchor not found')
s = s.replace(old, new)
p.write_text(s)
