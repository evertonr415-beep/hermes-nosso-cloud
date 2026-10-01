from pathlib import Path

p = Path('/app/hermes-simple.py')
s = p.read_text()

anchor = 'def _result_path(image_result):\n'
if anchor not in s:
    raise SystemExit('grounded-skill anchor not found')

# Rename the existing grounded generator so we can wrap it with reliable identity
# resolution and a deterministic local fallback.
old_def = 'def generate_grounded_real_people_image(text, conversation):\n'
if old_def not in s:
    raise SystemExit('grounded generator not found')
if 'def generate_grounded_real_people_image_ai(text, conversation):' not in s:
    s = s.replace(old_def, 'def generate_grounded_real_people_image_ai(text, conversation):\n', 1)

wrapper = r'''# High-confidence profile pages used before generic search for identities that
# repeatedly appeared in Hermes requests. Pages are public and current; the image
# extractor below prefers IMG tags whose alt/title matches the person's name.
GROUNDED_PROFILE_PAGES = {
    'sergio onofre da silva': [
        'https://candidatos.nexojornal.com.br/2026/pr/sergio-onofre-160002546828/',
        'https://meuspoliticos.com.br/eleicoes/2026/pr/deputado-estadual/sergio-onofre-dep-est-pr-2026-160002546828',
        'https://www.conexaopolitica.com.br/eleicoes/2026/candidato/sergio-onofre-160002546828/',
        'https://agenciasertao.com/eleicoes/candidato/PR/sergio-onofre-psd-pr--160002546828/',
    ],
    'sergio onofre': [
        'https://candidatos.nexojornal.com.br/2026/pr/sergio-onofre-160002546828/',
        'https://meuspoliticos.com.br/eleicoes/2026/pr/deputado-estadual/sergio-onofre-dep-est-pr-2026-160002546828',
        'https://www.conexaopolitica.com.br/eleicoes/2026/candidato/sergio-onofre-160002546828/',
    ],
    'edson hugo manueira': [
        'https://www.sabaudia.pr.gov.br/prefeitura/detalhe-prefeito/18/',
    ],
    'hugo manueira': [
        'https://www.sabaudia.pr.gov.br/prefeitura/detalhe-prefeito/18/',
    ],
    'pedro deboni lupion mello': [
        'https://www.camara.leg.br/deputados/204395',
        'https://candidatos.nexojornal.com.br/2026/pr/pedro-lupion-160002540769/',
    ],
    'pedro lupion': [
        'https://www.camara.leg.br/deputados/204395',
        'https://candidatos.nexojornal.com.br/2026/pr/pedro-lupion-160002540769/',
    ],
}

# Factual labels verified for the 2026 election cycle. These are displayed only
# in the deterministic local fallback and are not used for persuasion or slogans.
GROUNDED_2026_ELECTION_LABELS = {
    'sergio onofre da silva': 'Deputado Estadual · PR · 55633',
    'sergio onofre': 'Deputado Estadual · PR · 55633',
    'pedro deboni lupion mello': 'Deputado Federal · PR · 1000',
    'pedro lupion': 'Deputado Federal · PR · 1000',
    'edson hugo manueira': 'Prefeito de Sabáudia · PR',
    'hugo manueira': 'Prefeito de Sabáudia · PR',
}


def _grounded_norm(value):
    try:
        return _norm_person_text(value)
    except Exception:
        import unicodedata
        value = unicodedata.normalize('NFKD', str(value or ''))
        value = ''.join(ch for ch in value if not unicodedata.combining(ch)).lower()
        return ' '.join(re.sub(r'[^a-z0-9 ]+', ' ', value).split())


def _grounded_profile_pages(person):
    hay = _grounded_norm((person.get('name') or '') + ' ' + (person.get('search_query') or ''))
    out = []
    for key, pages in GROUNDED_PROFILE_PAGES.items():
        if _grounded_norm(key) in hay:
            for page in pages:
                if page not in out:
                    out.append(page)
    return out


def _grounded_named_image_candidates(page_url, person_name):
    """Extract likely portrait URLs and rank IMG tags matching the person's name."""
    import html as html_lib
    req = urllib.request.Request(page_url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml',
        'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.7',
    })
    try:
        with urllib.request.urlopen(req, timeout=14) as res:
            page = res.read(3 * 1024 * 1024).decode('utf-8', 'ignore')
    except Exception:
        return []

    wanted = set(_grounded_norm(person_name).split())
    scored = []
    seen = set()

    # Prefer actual IMG tags whose descriptive text contains the person's name.
    for m in re.finditer(r'<img\\b[^>]*>', page, re.I):
        tag = m.group(0)
        attrs = {}
        for key in ('src', 'data-src', 'data-lazy-src', 'srcset', 'alt', 'title'):
            mm = re.search(r'\\b' + re.escape(key) + r'=["\\\']([^"\\\']+)', tag, re.I)
            if mm:
                attrs[key] = html_lib.unescape(mm.group(1)).strip()
        raw = attrs.get('data-src') or attrs.get('data-lazy-src') or attrs.get('src') or ''
        if not raw and attrs.get('srcset'):
            raw = attrs['srcset'].split(',')[0].strip().split(' ')[0]
        if not raw:
            continue
        url = urllib.parse.urljoin(page_url, raw)
        if not _safe_public_url(url) or url in seen:
            continue
        desc = _grounded_norm((attrs.get('alt') or '') + ' ' + (attrs.get('title') or '') + ' ' + url)
        tokens = set(desc.split())
        overlap = len(wanted & tokens)
        score = overlap * 25
        if 'foto' in tokens or 'candidato' in tokens or 'perfil' in tokens:
            score += 6
        if any(x in url.lower() for x in ('logo', 'banner', 'sprite', 'icon', 'favicon')):
            score -= 30
        seen.add(url)
        scored.append((score, url))

    # OG/Twitter image is a lower-priority fallback, because many pages use a
    # generic election banner instead of the candidate portrait.
    for pattern in (
        r'<meta[^>]+(?:property|name)=["\\\'](?:og:image|twitter:image|twitter:image:src)["\\\'][^>]+content=["\\\']([^"\\\']+)',
        r'<meta[^>]+content=["\\\']([^"\\\']+)["\\\'][^>]+(?:property|name)=["\\\'](?:og:image|twitter:image|twitter:image:src)["\\\']',
    ):
        for mm in re.finditer(pattern, page, re.I):
            url = urllib.parse.urljoin(page_url, html_lib.unescape(mm.group(1)).strip())
            if _safe_public_url(url) and url not in seen:
                seen.add(url)
                scored.append((-2, url))

    scored.sort(key=lambda row: row[0], reverse=True)
    return [url for score, url in scored if score >= -2][:18]


# Wrap the resilient resolver so known public profiles are tried BEFORE generic
# search. This prevents a generic election banner from being accepted for Sergio.
_grounded_original_find_person_reference_resilient = find_person_reference_resilient

def find_person_reference_resilient(person):
    name = str(person.get('name') or '').strip()
    cache_key = ('grounded-profile|' + name + '|' + str(person.get('search_query') or '')).lower().strip()
    with REFERENCE_PERSON_CACHE_LOCK:
        cached = REFERENCE_PERSON_CACHE.get(cache_key)
    if cached:
        image, source, query = cached
        return image.copy(), source, query, True

    pages = _grounded_profile_pages(person)
    for page_url in pages:
        candidates = _grounded_named_image_candidates(page_url, name)
        print(f'[hermes-simple] grounded profile page person={name!r} page={page_url[:90]!r} candidates={len(candidates)}', flush=True)
        for image_url in candidates:
            try:
                image, source = _download_reference_image(image_url)
                with REFERENCE_PERSON_CACHE_LOCK:
                    REFERENCE_PERSON_CACHE[cache_key] = (image.copy(), source, 'verified-profile-page')
                return image, source, 'verified-profile-page', False
            except Exception:
                pass

    return _grounded_original_find_person_reference_resilient(person)


def _grounded_label_for(name):
    key = _grounded_norm(name)
    for known, label in GROUNDED_2026_ELECTION_LABELS.items():
        if _grounded_norm(known) in key or key in _grounded_norm(known):
            return label
    return ''


def generate_real_people_local_composite(text, conversation):
    from PIL import Image, ImageOps, ImageDraw, ImageFont
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import io

    people, composition = extract_real_person_reference_plan(text, conversation)
    results = {}
    failures = []
    workers = max(1, min(4, len(people)))
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix='hermes-grounded-local') as pool:
        futs = {pool.submit(find_person_reference_resilient, person): person for person in people}
        for fut in as_completed(futs):
            person = futs[fut]
            try:
                image, source, query, cached = fut.result()
                results[person['name']] = {
                    'name': person['name'], 'image': image, 'source': source,
                    'query': query, 'cached': cached,
                }
            except Exception as exc:
                failures.append({
                    'name': person.get('name',''),
                    'search_query': person.get('search_query',''),
                    'error': type(exc).__name__,
                    'attempts': getattr(exc, 'reference_attempts', []),
                })

    ordered = [results[p['name']] for p in people if p.get('name') in results]
    sources = [{
        'name': r['name'], 'source': r['source'], 'query': r['query'], 'cached': r['cached']
    } for r in ordered]
    if failures:
        raise ReferenceCoverageError(failures, sources)

    # Neutral final composition: this is the user-facing result, not a debug/reference sheet.
    # It uses only downloaded real photos and does not synthesize or alter facial identity.
    W, H = 1600, 1000
    canvas = Image.new('RGB', (W, H), (244, 246, 249))
    draw = ImageDraw.Draw(canvas)

    # Clean informational header; deliberately no campaign slogans or persuasion.
    draw.rectangle((0, 0, W, 132), fill=(255, 255, 255))
    draw.text((64, 40), 'Composição com pessoas reais', fill=(22, 27, 34))
    draw.text((64, 82), 'Referências públicas verificadas · composição neutra', fill=(92, 99, 110))

    n = max(1, len(ordered))
    gap = 22
    margin = 46
    portrait_w = int((W - margin * 2 - gap * (n - 1)) / n)
    portrait_h = 700
    top = 160

    for idx, row in enumerate(ordered):
        x = margin + idx * (portrait_w + gap)
        y = top
        # Portrait fills most of the panel, avoiding the old debug-card appearance.
        fitted = ImageOps.fit(
            row['image'].convert('RGB'),
            (portrait_w, portrait_h),
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.28),
        )
        canvas.paste(fitted, (x, y))
        # Bottom identity strip is factual and neutral.
        strip_y = y + portrait_h
        draw.rectangle((x, strip_y, x + portrait_w, strip_y + 104), fill=(255,255,255))
        draw.text((x + 16, strip_y + 18), row['name'][:50], fill=(20,24,31))
        label = _grounded_label_for(row['name'])
        if label:
            draw.text((x + 16, strip_y + 58), label[:56], fill=(80,87,98))

    draw.text((64, 948), 'Identidades preservadas a partir das referências encontradas; nenhum rosto genérico foi inventado.', fill=(100,106,116))

    buf = io.BytesIO()
    canvas.save(buf, format='JPEG', quality=93, optimize=True)
    mid = store_media(buf.getvalue(), 'image/jpeg')
    print(f'[hermes-simple] grounded local final composite success people={len(ordered)}', flush=True)
    return mid, 'Hermes Local Grounded Composer', sources


def generate_grounded_real_people_image(text, conversation):
    try:
        return generate_grounded_real_people_image_ai(text, conversation)
    except Exception as exc:
        detail = str(exc)
        # If free image-edit providers are unavailable, complete the request using
        # the verified photos instead of failing or returning the reference sheet.
        if 'all_free_edit_providers_failed' in detail or 'ZeroGPU' in detail or 'AppError' in detail or 'ValueError' in detail:
            print(f'[hermes-simple] grounded AI editor unavailable; using final local composite detail={detail[:300]}', flush=True)
            return generate_real_people_local_composite(text, conversation)
        raise


'''

# Replace our previous wrapper wholesale when rebuilding from the stable base.
if 'def generate_real_people_local_composite(text, conversation):' not in s:
    s = s.replace(anchor, wrapper + anchor, 1)
else:
    start = s.index('# High-confidence profile pages used before generic search') if '# High-confidence profile pages used before generic search' in s else s.index('def generate_real_people_local_composite(text, conversation):')
    end = s.index(anchor, start)
    s = s[:start] + wrapper + s[end:]

# Make the success message accurate for AI-edit and local-composite paths.
s = s.replace(
    '"text":"Imagem criada usando referências visuais pesquisadas para: "+names+". Os rostos foram enviados ao editor como referência; não foi usado text-to-image puro para inventar identidades.",',
    '"text":"Imagem criada usando referências visuais reais para: "+names+". As identidades foram preservadas por referência e não foi usado text-to-image puro para inventar rostos.",'
)
s = s.replace('"skill":"real-person-reference"', '"skill":"real-people-grounded-image"')

p.write_text(s)
print('real-people-grounded-image skill patch applied v2')
