from pathlib import Path

p = Path('/app/hermes-simple.py')
s = p.read_text()

anchor = 'def is_image_generation_request(text):\n'
helper = r'''def cache_internal_video_from_text(text):
    """Resolve generated Hermes video paths into the simple web media cache.

    Prefer MP4/WebM when Hermes also emits a GIF preview, so the browser gets a
    normal inline <video> player instead of showing MEDIA:/opt/data/... text.
    """
    source = text or ''
    patterns = [
        r'(?:MEDIA:)?(/opt/data/cache/videos/[^\r\n\"\'<>]+?\.(?:mp4|webm|m4v|mov))(?=$|[\s\"\'),.;])',
        r'(?:MEDIA:)?(/opt/data/cache/videos/[^\r\n\"\'<>]+?\.gif)(?=$|[\s\"\'),.;])',
    ]
    match = None
    for pattern in patterns:
        match = re.search(pattern, source, re.I)
        if match:
            break
    if not match:
        return None, source, None

    media_path = match.group(1).strip()
    query = urllib.parse.urlencode({'path': media_path})
    auth = base64.b64encode((USER + ':' + PASSWORD).encode('utf-8')).decode('ascii')
    headers = {
        'Authorization': 'Basic ' + auth,
        'Accept': 'video/*,image/gif,application/octet-stream,*/*;q=0.5',
        'User-Agent': 'HermesNossoWeb/3',
    }
    endpoints = [
        ADVANCED_URL.rstrip('/') + '/api/hermes-nosso/media?' + query,
        ADVANCED_URL.rstrip('/') + '/api/media?' + query,
    ]

    for endpoint in endpoints:
        try:
            req = urllib.request.Request(endpoint, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as res:
                ctype = (res.headers.get('Content-Type', '') or '').split(';', 1)[0].strip().lower()
                raw = res.read(80 * 1024 * 1024 + 1)
            if len(raw) > 80 * 1024 * 1024:
                raise RuntimeError('generated_video_too_large')

            mime = ctype or 'application/octet-stream'
            if media_path.lower().endswith('.mp4'): mime = 'video/mp4'
            elif media_path.lower().endswith('.webm'): mime = 'video/webm'
            elif media_path.lower().endswith('.m4v'): mime = 'video/x-m4v'
            elif media_path.lower().endswith('.mov'): mime = 'video/quicktime'
            elif media_path.lower().endswith('.gif'): mime = 'image/gif'

            if not (mime.startswith('video/') or mime == 'image/gif'):
                raise RuntimeError('media_response_not_video')

            mid = store_media(raw, mime)
            # Remove the exact matched path and any matching MEDIA: prefix from text.
            cleaned = (source[:match.start()] + source[match.end():]).strip()
            print(f'[hermes-simple] cached Hermes VIDEO bytes={len(raw)} mime={mime}', flush=True)
            return mid, cleaned, mime
        except Exception as exc:
            print(f'[hermes-simple] Hermes VIDEO endpoint failed url={endpoint.split("?")[0]} type={type(exc).__name__}', flush=True)

    return None, source, None


'''
if 'def cache_internal_video_from_text(text):' not in s:
    s = s.replace(anchor, helper + anchor, 1)

old = '''            route_meta=classify_route(text, route)
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
new = '''            route_meta=classify_route(text, route)
            image_url=None
            video_url=None

            video_mid, cleaned_video, video_mime = cache_internal_video_from_text(out)
            if video_mid:
                if video_mime == "image/gif":
                    image_url="/api/media/"+video_mid
                else:
                    video_url="/api/media/"+video_mid
                out=cleaned_video or "Vídeo gerado."
            else:
                internal_mid, cleaned_out = cache_internal_media_from_text(out)
                if internal_mid:
                    image_url="/api/media/"+internal_mid
                    out=cleaned_out or "Imagem gerada."
                elif route_meta.get("category")=="Imagem":
                    mid=cache_image_from_text(out)
                    if mid:
                        image_url="/api/media/"+mid

            return self.sendb(200,json.dumps({"text":out,"via":via,"routeMeta":route_meta,"imageUrl":image_url,"videoUrl":video_url},ensure_ascii=False))
'''
if old not in s:
    raise SystemExit('video media integration anchor not found')
s = s.replace(old, new, 1)

p.write_text(s)
