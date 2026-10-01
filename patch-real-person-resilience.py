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


def _person_reference_query_variants(person):
    name = str(person.get('name') or '').strip()
    base = str(person.get('search_query') or name).strip()
    variants = []
    def add(q):
        q = ' '.join((q or '').split()).strip()
        if q and q not in variants:
            variants.append(q)
    # First preserve the planner's disambiguated query, then broaden gradually.
    add(base)
    add(name + ' foto oficial')
    add(name + ' site:gov.br foto')
    add(name + ' site:leg.br foto')
    add(name + ' site:pr.gov.br foto')
    add(name + ' perfil oficial')
    add(name)
    return variants[:7]


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
    for query in _person_reference_query_variants(person):
        try:
            urls = _reference_candidate_urls(query)
        except Exception as exc:
            attempts.append({'query':query, 'error':type(exc).__name__, 'candidates':0})
            continue
        print(f'[hermes-simple] person reference person={name!r} query={query[:100]!r} candidates={len(urls)}', flush=True)
        attempts.append({'query':query, 'candidates':len(urls)})
        for url in urls[:12]:
            try:
                image, source = _download_reference_image(url)
                with REFERENCE_PERSON_CACHE_LOCK:
                    REFERENCE_PERSON_CACHE[cache_key] = (image.copy(), source, query)
                return image, source, query, False
            except Exception as exc:
                attempts[-1]['last_download_error'] = type(exc).__name__
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
        print('[hermes-simple] reference coverage failures=' + json.dumps(failures, ensure_ascii=False)[:2500], flush=True)
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
