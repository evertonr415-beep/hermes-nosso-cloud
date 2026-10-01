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


def is_image_generation_request(text):
    t = (text or '').lower()
    verbs = ('crie ', 'criar ', 'gere ', 'gerar ', 'faça ', 'faca ', 'desenhe ', 'produza ', 'edite ', 'editar ', 'modifique ', 'mude ', 'troque ', 'coloque ', 'remova ')
    nouns = ('imagem', 'foto', 'ilustração', 'ilustracao', 'arte', 'rosto', 'fundo', 'óculos', 'oculos')
    return any(v in t for v in verbs) and any(n in t for n in nouns)


def _result_path(image_result):
    if isinstance(image_result, (tuple, list)):
        image_result = image_result[0] if image_result else None
    if isinstance(image_result, str):
        return image_result
    if isinstance(image_result, dict):
        return image_result.get('path') or image_result.get('name')
    return getattr(image_result, 'path', None) or getattr(image_result, 'name', None)


def _store_gradio_result(result):
    path = _result_path(result)
    if not path or not os.path.isfile(path):
        raise RuntimeError('generated_image_missing')
    with open(path, 'rb') as fh:
        raw = fh.read(25 * 1024 * 1024 + 1)
    if len(raw) > 25 * 1024 * 1024:
        raise RuntimeError('generated_image_too_large')
    mime = 'image/png'
    low = path.lower()
    if low.endswith(('.jpg', '.jpeg')): mime = 'image/jpeg'
    elif low.endswith('.webp'): mime = 'image/webp'
    mid = store_media(raw, mime)
    return mid, len(raw)


def generate_zero_cost_image(prompt):
    from gradio_client import Client
    token = (os.getenv('HF_TOKEN') or '').strip() or None
    configured = (os.getenv('HF_ZERO_IMAGE_SPACE') or '').strip()
    spaces = [x for x in [configured, 'mrfakename/Z-Image-Turbo', 'Qwen/Qwen-Image'] if x]
    errors = []
    for space in dict.fromkeys(spaces):
        try:
            client = Client(space, token=token, verbose=False)
            if space == 'Qwen/Qwen-Image':
                result = client.predict(prompt, 42, True, '1:1', 4.0, 40, True, api_name='/infer')
            else:
                api_name = '/generate_image'
                try:
                    info = client.view_api(return_format='dict') or {}
                    endpoints = info.get('named_endpoints') or {}
                    if api_name not in endpoints and endpoints:
                        candidates = [name for name, spec in endpoints.items() if len((spec or {}).get('parameters') or []) >= 6]
                        api_name = candidates[0] if candidates else next(iter(endpoints))
                except Exception:
                    pass
                result = client.predict(prompt, 1024, 1024, 9, 42, True, api_name=api_name)
            mid, size = _store_gradio_result(result)
            print(f'[hermes-simple] ZeroGPU image success space={space} bytes={size}', flush=True)
            return mid, space
        except Exception as exc:
            errors.append(f'{space}:{type(exc).__name__}')
            print(f'[hermes-simple] ZeroGPU image provider failed space={space} type={type(exc).__name__}', flush=True)
    raise RuntimeError('all_free_image_providers_failed ' + ','.join(errors))


def generate_zero_cost_edit(image_bytes, mime, prompt):
    from gradio_client import Client, handle_file
    token = (os.getenv('HF_TOKEN') or '').strip() or None
    configured = (os.getenv('HF_ZERO_EDIT_SPACE') or '').strip()
    spaces = [x for x in [configured, 'Qwen/Qwen-Image-Edit', 'zerogpu-aoti/FLUX.1-Kontext-Dev'] if x]
    suffix = '.png'
    if 'jpeg' in mime or 'jpg' in mime: suffix = '.jpg'
    elif 'webp' in mime: suffix = '.webp'
    errors = []
    with tempfile.TemporaryDirectory() as td:
        src = os.path.join(td, 'reference' + suffix)
        with open(src, 'wb') as fh:
            fh.write(image_bytes)
        uploaded = handle_file(src)
        for space in dict.fromkeys(spaces):
            try:
                client = Client(space, token=token, verbose=False)
                if space == 'Qwen/Qwen-Image-Edit':
                    result = client.predict(uploaded, prompt, 42, True, 4.0, 40, True, api_name='/infer')
                else:
                    # FLUX Kontext common signature: image, prompt, seed, randomize_seed, guidance, steps
                    result = client.predict(uploaded, prompt, 42, True, 2.5, 28, api_name='/infer')
                mid, size = _store_gradio_result(result)
                print(f'[hermes-simple] ZeroGPU edit success space={space} bytes={size}', flush=True)
                return mid, space
            except Exception as exc:
                errors.append(f'{space}:{type(exc).__name__}')
                print(f'[hermes-simple] ZeroGPU edit provider failed space={space} type={type(exc).__name__}', flush=True)
    raise RuntimeError('all_free_edit_providers_failed ' + ','.join(errors))

'''

if 'def cache_internal_media_from_text(text):' not in s:
    s = s.replace(anchor, helper + anchor)
elif 'def generate_zero_cost_edit(image_bytes, mime, prompt):' not in s:
    start = s.index('def cache_internal_media_from_text(text):')
    end = s.index(anchor, start)
    s = s[:start] + helper + s[end:]

old = '''            payload={"input":text,"conversation":conv or ("web-"+str(int(time.time()*1000))),"store":True}
            if route=="matrix":
'''
new = '''            if is_image_generation_request(text):
                try:
                    if attachment_id:
                        with MEDIA_LOCK:
                            item=MEDIA_STORE.get(attachment_id)
                        if not item or not str(item.get("mime","")).startswith("image/"):
                            return self.sendb(400,json.dumps({"error":"A imagem anexada não está mais disponível. Anexe novamente."},ensure_ascii=False))
                        mid, used_space=generate_zero_cost_edit(item["bytes"], item["mime"], text)
                        meta={"category":"Imagem","skill":"image-editing","provider":"Hugging Face ZeroGPU · "+used_space}
                        return self.sendb(200,json.dumps({"text":"Imagem editada usando a foto anexada como referência.","via":"huggingface-zerogpu-edit","routeMeta":meta,"imageUrl":"/api/media/"+mid},ensure_ascii=False))
                    mid, used_space=generate_zero_cost_image(text)
                    meta={"category":"Imagem","skill":"image-generation","provider":"Hugging Face ZeroGPU · "+used_space}
                    return self.sendb(200,json.dumps({"text":"Imagem gerada pelo modo gratuito.","via":"huggingface-zerogpu","routeMeta":meta,"imageUrl":"/api/media/"+mid},ensure_ascii=False))
                except Exception as exc:
                    print(f"[hermes-simple] ZeroGPU image unavailable type={type(exc).__name__} detail={str(exc)[:240]}",flush=True)
                    meta={"category":"Imagem","skill":"image-generation","provider":"Hugging Face ZeroGPU · fallback"}
                    return self.sendb(200,json.dumps({"text":"Os geradores gratuitos estão temporariamente sem capacidade. A foto de referência não foi ignorada e nenhum resultado aleatório foi criado. Tente novamente em alguns minutos.","via":"huggingface-zerogpu-unavailable","routeMeta":meta,"imageUrl":None},ensure_ascii=False))
            payload={"input":text,"conversation":conv or ("web-"+str(int(time.time()*1000))),"store":True}
            if route=="matrix":
'''
if old not in s:
    raise SystemExit('chat payload anchor not found')
s = s.replace(old, new)

old2 = '''            route_meta=classify_route(text, route)
            image_url=None
            if route_meta.get("category")=="Imagem":
                mid=cache_image_from_text(out)
                if mid:
                    image_url="/api/media/"+mid
            return self.sendb(200,json.dumps({"text":out,"via":via,"routeMeta":route_meta,"imageUrl":image_url},ensure_ascii=False))
'''
new2 = '''            route_meta=classify_route(text, route)
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
if old2 in s:
    s = s.replace(old2, new2)

p.write_text(s)
