from pathlib import Path

p = Path('/app/hermes-simple.py')
s = p.read_text()

helper_anchor = 'def _result_path(image_result):\n'
if helper_anchor not in s:
    raise SystemExit('real-person reference helper anchor not found')

helpers = r'''def is_real_person_reference_request(text):
    """Narrow additive route: only image requests explicitly asking for real/web references."""
    t = (text or '').lower()
    if not is_image_generation_request(text):
        return False
    fictional = (
        'fictícia', 'ficticia', 'fictício', 'ficticio', 'personagem fict',
        'mulher virtual', 'homem virtual', 'pessoa virtual', 'modelo virtual'
    )
    if any(x in t for x in fictional):
        return False
    web_cues = (
        'procure na internet', 'pesquise na internet', 'busque na internet',
        'procure na web', 'pesquise na web', 'busque na web',
        'foto real', 'fotos reais', 'imagem real', 'imagens reais',
        'use a foto deles', 'use as fotos deles', 'use a imagem deles',
        'use as imagens deles', 'rosto real', 'rostos reais',
        'pessoas reais', 'pessoa real'
    )
    role_cues = (
        'prefeito', 'prefeita', 'deputado', 'deputada', 'vereador', 'vereadora',
        'governador', 'governadora', 'senador', 'senadora', 'presidente',
        'candidato', 'candidata', 'ministro', 'ministra', 'artista', 'cantor',
        'cantora', 'ator', 'atriz', 'jogador', 'jogadora', 'empresário', 'empresaria'
    )
    return any(x in t for x in web_cues) and any(x in t for x in role_cues)


def _extract_json_object(text):
    raw = (text or '').strip()
    raw = re.sub(r'^```(?:json)?\\s*|\\s*```$', '', raw, flags=re.I | re.S).strip()
    try:
        return json.loads(raw)
    except Exception:
        m = re.search(r'\\{.*\\}', raw, re.S)
        if not m:
            raise RuntimeError('reference_name_extraction_not_json')
        return json.loads(m.group(0))


def extract_real_person_reference_plan(user_text, conversation):
    prompt = (
        '[HERMES REAL PERSON REFERENCE PLANNER]\n'
        'From the user request below, identify only the real named people whose visual identity must be preserved. '
        'Return ONLY valid JSON, no markdown, in this shape: '
        '{"people":[{"name":"Full Name","search_query":"Full Name role city/state official photo"}],'
        '"composition_prompt":"concise neutral visual composition request preserving each identity"}. '
        'Use role/location context from the request to disambiguate names. Do not invent names. '
        'Do not add political slogans, endorsements, attacks, or persuasive claims.\n\n'
        'USER REQUEST:\n' + user_text
    )
    data, _ = call_upstream({
        'input': prompt,
        'conversation': (conversation or 'web') + '-real-person-plan',
        'store': False,
    })
    obj = _extract_json_object(response_text(data))
    people = []
    for item in (obj.get('people') or [])[:4]:
        if not isinstance(item, dict):
            continue
        name = str(item.get('name') or '').strip()
        query = str(item.get('search_query') or '').strip()
        if name and query:
            people.append({'name': name[:120], 'search_query': query[:240]})
    if not people:
        raise RuntimeError('no_real_people_extracted')
    composition = str(obj.get('composition_prompt') or user_text).strip()[:1200]
    return people, composition


def _bing_image_candidates(query):
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
    with urllib.request.urlopen(req, timeout=20) as res:
        page = res.read(2 * 1024 * 1024).decode('utf-8', 'ignore')

    candidates = []
    patterns = [
        r'&quot;murl&quot;:&quot;(.*?)&quot;',
        r'"murl"\s*:\s*"(.*?)"',
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, page, re.I):
            raw = html_lib.unescape(match.group(1))
            raw = raw.replace('\\/', '/').replace('\\u002f', '/').replace('\\u003a', ':')
            if raw.startswith('http') and raw not in candidates:
                candidates.append(raw)
            if len(candidates) >= 16:
                return candidates
    return candidates


def _download_reference_image(url):
    from PIL import Image
    import io
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0',
        'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
        'Referer': 'https://www.bing.com/',
    })
    with urllib.request.urlopen(req, timeout=15) as res:
        ctype = (res.headers.get('Content-Type', '') or '').split(';', 1)[0].strip().lower()
        if not ctype.startswith('image/'):
            raise RuntimeError('reference_not_image')
        raw = res.read(8 * 1024 * 1024 + 1)
    if len(raw) > 8 * 1024 * 1024:
        raise RuntimeError('reference_too_large')
    image = Image.open(io.BytesIO(raw))
    image.load()
    if image.width < 160 or image.height < 160:
        raise RuntimeError('reference_too_small')
    return image.convert('RGB'), url


def find_real_person_reference(query):
    last = None
    for url in _bing_image_candidates(query)[:12]:
        try:
            return _download_reference_image(url)
        except Exception as exc:
            last = exc
    raise RuntimeError('no_reference_image_found:' + (type(last).__name__ if last else 'empty_search'))


def build_reference_sheet(people):
    from PIL import Image, ImageOps, ImageDraw
    import io
    refs = []
    sources = []
    for person in people:
        image, source = find_real_person_reference(person['search_query'])
        refs.append((person['name'], image))
        sources.append({'name': person['name'], 'source': source})

    cell = 512
    cols = 2 if len(refs) > 1 else 1
    rows = (len(refs) + cols - 1) // cols
    sheet = Image.new('RGB', (cell * cols, cell * rows), 'white')
    draw = ImageDraw.Draw(sheet)
    for idx, (name, image) in enumerate(refs):
        x = (idx % cols) * cell
        y = (idx // cols) * cell
        fitted = ImageOps.fit(image, (cell, cell - 42), method=Image.Resampling.LANCZOS, centering=(0.5, 0.35))
        sheet.paste(fitted, (x, y + 42))
        draw.rectangle((x, y, x + cell, y + 42), fill='white')
        draw.text((x + 12, y + 12), name[:52], fill='black')

    buf = io.BytesIO()
    sheet.save(buf, format='JPEG', quality=92)
    return buf.getvalue(), sources


def generate_grounded_real_people_image(text, conversation):
    people, composition = extract_real_person_reference_plan(text, conversation)
    sheet_bytes, sources = build_reference_sheet(people)
    names = ', '.join(p['name'] for p in people)
    grounded_prompt = (
        'Create the requested neutral composition using the attached reference sheet. '
        'The reference sheet contains real public people labelled by name. Preserve each person\'s recognizable facial identity; '
        'do not replace them with generic faces and do not merge identities. '
        'Do not invent political slogans or factual claims. Keep any requested factual labels concise. '
        f'People: {names}. Composition: {composition}. Original request: {text}'
    )
    mid, used_space = generate_zero_cost_edit(sheet_bytes, 'image/jpeg', grounded_prompt)
    return mid, used_space, sources


'''

if 'def is_real_person_reference_request(text):' not in s:
    s = s.replace(helper_anchor, helpers + helper_anchor, 1)

branch_anchor = '''            if is_image_generation_request(text):
                try:
'''
if branch_anchor not in s:
    raise SystemExit('real-person reference branch anchor not found')

branch = '''            if is_real_person_reference_request(text) and not attachment_id:
                try:
                    mid, used_space, sources = generate_grounded_real_people_image(text, conv)
                    names = ', '.join(x.get('name','') for x in sources if x.get('name'))
                    meta={"category":"Imagem","skill":"real-person-reference","provider":"Pesquisa web + Hugging Face ZeroGPU · "+used_space}
                    return self.sendb(200,json.dumps({
                        "text":"Imagem criada usando referências visuais pesquisadas para: "+names+". Os rostos foram enviados ao editor como referência; não foi usado text-to-image puro para inventar identidades.",
                        "via":"web-reference-zerogpu-edit","routeMeta":meta,"imageUrl":"/api/media/"+mid,
                        "referenceSources":sources
                    },ensure_ascii=False))
                except Exception as exc:
                    print(f"[hermes-simple] real-person reference route failed type={type(exc).__name__} detail={str(exc)[:300]}",flush=True)
                    meta={"category":"Imagem","skill":"real-person-reference","provider":"Pesquisa web + referência visual"}
                    return self.sendb(200,json.dumps({
                        "text":"Não consegui obter referências visuais confiáveis para todas as pessoas. Para evitar inventar rostos, nenhuma imagem genérica foi criada. Tente novamente ou anexe uma foto de referência de cada pessoa.",
                        "via":"web-reference-unavailable","routeMeta":meta,"imageUrl":None
                    },ensure_ascii=False))

            if is_image_generation_request(text):
                try:
'''

if 'web-reference-zerogpu-edit' not in s:
    s = s.replace(branch_anchor, branch, 1)

p.write_text(s)
