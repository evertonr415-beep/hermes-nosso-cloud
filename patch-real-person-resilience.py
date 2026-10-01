from pathlib import Path

p = Path('/app/hermes-simple.py')
s = p.read_text()

anchor = 'def build_reference_sheet(people):\n'
if anchor not in s:
    raise SystemExit('real-person resilience anchor not found')

insert = r'''class ReferenceCoverageError(RuntimeError):
    def __init__(self, failures, successes=None):
        self.failures = failures or []
        self.successes = successes or []
        names = ', '.join(x.get('name','?') for x in self.failures)
        super().__init__('missing_reference_people:' + names)


REFERENCE_PERSON_CACHE = {}
REFERENCE_PERSON_CACHE_LOCK = threading.Lock()

# Verified official fallbacks. These are deliberately narrow: they are used only
# when the requested identity matches, so Hermes does not substitute a random face.
VERIFIED_OFFICIAL_REFERENCE_URLS = {
    'edson hugo manueira': [
        'https://www.sabaudia.pr.gov.br/admin/globalarq/municipio/galeria-prefeito/280_219/3aa5349f6b7814e3f1f812646fadf13d.jpeg',
    ],
    'hugo manueira': [
        'https://www.sabaudia.pr.gov.br/admin/globalarq/municipio/galeria-prefeito/280_219/3aa5349f6b7814e3f1f812646fadf13d.jpeg',
    ],
    'pedro de boni lupion mello': [
        'https://www.camara.leg.br/internet/deputado/bandep/pagina_do_deputado/204395.jpg',
    ],
    'pedro deboni lupion mello': [
        'https://www.camara.leg.br/internet/deputado/bandep/pagina_do_deputado/204395.jpg',
    ],
    'pedro lupion': [
        'https://www.camara.leg.br/internet/deputado/bandep/pagina_do_deputado/204395.jpg',
    ],
}


def _norm_person_text(value):
    import unicodedata
    value = unicodedata.normalize('NFKD', str(value or ''))
    value = ''.join(ch for ch in value if not unicodedata.combining(ch)).lower()
    value = re.sub(r'[^a-z0-9 ]+', ' ', value)
    return ' '.join(value.split())


def _verified_official_candidates(person):
    hay = _norm_person_text((person.get('name') or '') + ' ' + (person.get('search_query') or ''))
    out = []
    for key, urls in VERIFIED_OFFICIAL_REFERENCE_URLS.items():
        if _norm_person_text(key) in hay:
            for u in urls:
                if u not in out:
                    out.append(u)
    return out


def _camara_open_data_photo_candidates(person):
    """Resolve federal-deputy photos through Câmara's official open-data API."""
    name = str(person.get('name') or '').strip()
    context = _norm_person_text(name + ' ' + str(person.get('search_query') or ''))
    # Avoid needless API calls for obviously unrelated identities.
    if 'deputad' not in context and 'camara' not in context and 'lupion' not in context:
        return []
    api = 'https://dadosabertos.camara.leg.br/api/v2/deputados?' + urllib.parse.urlencode({
        'nome': name, 'itens': '20', 'ordem': 'ASC', 'ordenarPor': 'nome'
    })
    req = urllib.request.Request(api, headers={
        'User-Agent': 'HermesNosso/1.0 real-person-reference',
        'Accept': 'application/json',
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            payload = json.load(res)
    except Exception as exc:
        print(f'[hermes-simple] camara api lookup failed person={name!r} type={type(exc).__name__}', flush=True)
        return []
    rows = payload.get('dados') or []
    wanted = _norm_person_text(name)
    scored = []
    for row in rows:
        row_name = _norm_person_text(row.get('nome') or '')
        score = 0
        if row_name == wanted:
            score = 100
        elif wanted and (wanted in row_name or row_name in wanted):
            score = 70
        else:
            wanted_tokens = set(wanted.split())
            row_tokens = set(row_name.split())
            score = len(wanted_tokens & row_tokens)
        url = str(row.get('urlFoto') or '').strip()
        if url:
            scored.append((score, url))
    scored.sort(reverse=True)
    return [url for score, url in scored if score > 0][:5]


def _duckduckgo_result_pages(query):
    """Independent web-search fallback when Bing markup/rate limits return no results."""
    url = 'https://html.duckduckgo.com/html/?' + urllib.parse.urlencode({'q': query})
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36',
        'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.7',
    })
    try:
        with urllib.request.urlopen(req, timeout=12) as res:
            page = res.read(2 * 1024 * 1024).decode('utf-8', 'ignore')
    except Exception:
        return []
    import html as html_lib
    out = []
    for m in re.finditer(r'class=["\']result__a["\'][^>]+href=["\']([^"\']+)', page, re.I):
        href = html_lib.unescape(m.group(1))
        parsed = urllib.parse.urlparse(href)
        qs = urllib.parse.parse_qs(parsed.query)
        target = (qs.get('uddg') or [href])[0]
        target = urllib.parse.unquote(target)
        if _safe_public_url(target) and target not in out:
            out.append(target)
        if len(out) >= 12:
            break
    return out


def _person_reference_query_variants(person):
    name = str(person.get('name') or '').strip()
    base = str(person.get('search_query') or name).strip()
    variants = []
    def add(q):
        q = ' '.join((q or '').split()).strip()
        if q and q not in variants:
            variants.append(q)
    add(base)
    add(name + ' foto oficial')
    add(name + ' site:gov.br foto oficial')
    add(name + ' site:leg.br foto oficial')
    add(name + ' site:pr.gov.br foto oficial')
    add(name + ' prefeitura foto')
    add(name + ' camara deputados foto')
    add(name + ' perfil oficial')
    add(name)
    return variants[:9]


def _try_reference_urls(name, urls, query, attempts, cache_key):
    urls = [u for u in urls if u]
    attempts.append({'query': query, 'candidates': len(urls)})
    print(f'[hermes-simple] person reference person={name!r} source={query[:80]!r} candidates={len(urls)}', flush=True)
    for url in urls[:16]:
        try:
            image, source = _download_reference_image(url)
            with REFERENCE_PERSON_CACHE_LOCK:
                REFERENCE_PERSON_CACHE[cache_key] = (image.copy(), source, query)
            return image, source, query, False
        except Exception as exc:
            attempts[-1]['last_download_error'] = type(exc).__name__
    return None


def find_person_reference_resilient(person):
    name = str(person.get('name') or '').strip()
    cache_key = (name + '|' + str(person.get('search_query') or '')).lower().strip()
    with REFERENCE_PERSON_CACHE_LOCK:
        cached = REFERENCE_PERSON_CACHE.get(cache_key)
    if cached:
        image, source, query = cached
        print(f'[hermes-simple] reference cache hit person={name!r}', flush=True)
        return image.copy(), source, query, True

    attempts = []

    # 1) Highest-confidence deterministic official sources.
    got = _try_reference_urls(name, _verified_official_candidates(person), 'verified-official', attempts, cache_key)
    if got:
        return got

    # 2) Official Câmara open-data API for federal deputies.
    got = _try_reference_urls(name, _camara_open_data_photo_candidates(person), 'camara-open-data', attempts, cache_key)
    if got:
        return got

    # 3) Search engines + official/public pages. DuckDuckGo is independent of Bing.
    for query in _person_reference_query_variants(person):
        urls = []
        try:
            urls.extend(_reference_candidate_urls(query))
        except Exception as exc:
            attempts.append({'query': query, 'error': type(exc).__name__, 'candidates': 0})
        if not urls:
            try:
                for page_url in _duckduckgo_result_pages(query)[:10]:
                    for image_url in _page_image_candidates(page_url):
                        if image_url not in urls:
                            urls.append(image_url)
                        if len(urls) >= 30:
                            break
                    if len(urls) >= 30:
                        break
            except Exception as exc:
                attempts.append({'query': query + ' [duckduckgo]', 'error': type(exc).__name__, 'candidates': 0})
        got = _try_reference_urls(name, urls, query, attempts, cache_key)
        if got:
            return got

    err = RuntimeError('no_reference_found')
    err.reference_attempts = attempts
    raise err


def build_reference_sheet_resilient(people):
    from PIL import Image, ImageOps, ImageDraw
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import io

    results = {}
    failures = []
    workers = max(1, min(4, len(people)))
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix='hermes-ref') as pool:
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
        print('[hermes-simple] reference coverage failures=' + json.dumps(failures, ensure_ascii=False)[:5000], flush=True)
        raise ReferenceCoverageError(failures, sources)

    cell = 512
    cols = 2 if len(ordered) > 1 else 1
    rows = (len(ordered) + cols - 1) // cols
    sheet = Image.new('RGB', (cell * cols, cell * rows), 'white')
    draw = ImageDraw.Draw(sheet)
    for idx, row in enumerate(ordered):
        x = (idx % cols) * cell
        y = (idx // cols) * cell
        fitted = ImageOps.fit(row['image'], (cell, cell - 42), method=Image.Resampling.LANCZOS, centering=(0.5, 0.35))
        sheet.paste(fitted, (x, y + 42))
        draw.rectangle((x, y, x + cell, y + 42), fill='white')
        draw.text((x + 12, y + 12), row['name'][:52], fill='black')

    buf = io.BytesIO()
    sheet.save(buf, format='JPEG', quality=92)
    return buf.getvalue(), sources


'''
if 'class ReferenceCoverageError' not in s:
    s = s.replace(anchor, insert + anchor, 1)

old = '''    sheet_bytes, sources = build_reference_sheet(people)\n'''
new = '''    sheet_bytes, sources = build_reference_sheet_resilient(people)\n'''
if old not in s:
    raise SystemExit('grounded image build_reference_sheet call not found')
s = s.replace(old, new, 1)

old_exc = '''                except Exception as exc:\n                    print(f"[hermes-simple] real-person reference route failed type={type(exc).__name__} detail={str(exc)[:300]}",flush=True)\n                    meta={"category":"Imagem","skill":"real-person-reference","provider":"Pesquisa web + referência visual"}\n                    return self.sendb(200,json.dumps({\n                        "text":"Não consegui obter referências visuais confiáveis para todas as pessoas. Para evitar inventar rostos, nenhuma imagem genérica foi criada. Tente novamente ou anexe uma foto de referência de cada pessoa.",\n                        "via":"web-reference-unavailable","routeMeta":meta,"imageUrl":None\n                    },ensure_ascii=False))\n'''
new_exc = '''                except Exception as exc:\n                    print(f"[hermes-simple] real-person reference route failed type={type(exc).__name__} detail={str(exc)[:700]}",flush=True)\n                    meta={"category":"Imagem","skill":"real-person-reference","provider":"Pesquisa web + referência visual"}\n                    if isinstance(exc, ReferenceCoverageError):\n                        ok_names = [x.get("name","") for x in exc.successes if x.get("name")]\n                        bad_names = [x.get("name","") for x in exc.failures if x.get("name")]\n                        parts=[]\n                        if ok_names: parts.append("Referências encontradas: "+", ".join(ok_names)+".")\n                        if bad_names: parts.append("Não encontrei referência visual suficientemente confiável para: "+", ".join(bad_names)+".")\n                        parts.append("Não gerei rostos genéricos. Você pode tentar novamente ou anexar somente a foto da pessoa que faltou.")\n                        return self.sendb(200,json.dumps({\n                            "text":" ".join(parts),"via":"web-reference-partial","routeMeta":meta,"imageUrl":None,\n                            "referenceSources":exc.successes,"referenceFailures":exc.failures\n                        },ensure_ascii=False))\n                    return self.sendb(200,json.dumps({\n                        "text":"A pesquisa de referências reais falhou antes da geração. Nenhum rosto genérico foi inventado. Tente novamente; se persistir, anexe uma referência apenas da pessoa que estiver faltando.",\n                        "via":"web-reference-unavailable","routeMeta":meta,"imageUrl":None\n                    },ensure_ascii=False))\n'''
if old_exc not in s:
    raise SystemExit('real-person exception branch not found')
s = s.replace(old_exc, new_exc, 1)

p.write_text(s)
print('real-person resilience patch applied')
