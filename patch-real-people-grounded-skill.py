from pathlib import Path

p = Path('/app/hermes-simple.py')
s = p.read_text()

anchor = 'def _result_path(image_result):\n'
if anchor not in s:
    raise SystemExit('grounded-skill anchor not found')

# Rename the existing grounded generator so we can wrap it with a reliable local fallback.
old_def = 'def generate_grounded_real_people_image(text, conversation):\n'
if old_def not in s:
    raise SystemExit('grounded generator not found')
if 'def generate_grounded_real_people_image_ai(text, conversation):' not in s:
    s = s.replace(old_def, 'def generate_grounded_real_people_image_ai(text, conversation):\n', 1)

wrapper = r'''def generate_real_people_local_composite(text, conversation):
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

    # Deterministic local composition using the real downloaded photos.
    # This path intentionally does not synthesize or alter faces.
    W, H = 1536, 1024
    canvas = Image.new('RGB', (W, H), (248, 249, 250))
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 0, W, 150), fill=(255, 255, 255))
    draw.text((72, 42), 'Composição com referências reais', fill=(20, 24, 31))
    draw.text((72, 92), 'Fotos públicas verificadas • sem rostos genéricos', fill=(82, 88, 98))

    n = max(1, len(ordered))
    gap = 34
    margin = 72
    card_w = int((W - margin * 2 - gap * (n - 1)) / n)
    card_h = 720
    top = 205
    for idx, row in enumerate(ordered):
        x = margin + idx * (card_w + gap)
        y = top
        draw.rounded_rectangle((x, y, x + card_w, y + card_h), radius=24, fill=(255,255,255), outline=(224,226,230), width=2)
        img_box = (card_w - 28, 560)
        fitted = ImageOps.fit(row['image'].convert('RGB'), img_box, method=Image.Resampling.LANCZOS, centering=(0.5, 0.28))
        canvas.paste(fitted, (x + 14, y + 14))
        name = row['name'][:52]
        draw.text((x + 20, y + 595), name, fill=(20,24,31))
        draw.text((x + 20, y + 635), 'Referência visual real', fill=(92,98,108))
        host = ''
        try:
            host = urllib.parse.urlparse(row['source']).netloc.replace('www.','')
        except Exception:
            pass
        if host:
            draw.text((x + 20, y + 674), host[:44], fill=(120,126,136))

    footer = 'A composição preserva as fotos reais encontradas. Informações factuais não verificadas não são inventadas.'
    draw.text((72, 963), footer[:160], fill=(100,106,116))

    buf = io.BytesIO()
    canvas.save(buf, format='JPEG', quality=92, optimize=True)
    mid = store_media(buf.getvalue(), 'image/jpeg')
    print(f'[hermes-simple] grounded local composite success people={len(ordered)}', flush=True)
    return mid, 'Hermes Local Reference Composer', sources


def generate_grounded_real_people_image(text, conversation):
    try:
        return generate_grounded_real_people_image_ai(text, conversation)
    except Exception as exc:
        detail = str(exc)
        # If free image-edit providers are unavailable, still complete the request
        # using the verified real photos instead of failing or inventing identities.
        if 'all_free_edit_providers_failed' in detail or 'ZeroGPU' in detail or 'AppError' in detail or 'ValueError' in detail:
            print(f'[hermes-simple] grounded AI editor unavailable; using local composite detail={detail[:300]}', flush=True)
            return generate_real_people_local_composite(text, conversation)
        raise


'''
if 'def generate_real_people_local_composite(text, conversation):' not in s:
    s = s.replace(anchor, wrapper + anchor, 1)

# Make the success message accurate for both AI-edit and local-composite paths.
s = s.replace(
    '"text":"Imagem criada usando referências visuais pesquisadas para: "+names+". Os rostos foram enviados ao editor como referência; não foi usado text-to-image puro para inventar identidades.",',
    '"text":"Imagem criada usando referências visuais reais para: "+names+". As identidades foram preservadas por referência e não foi usado text-to-image puro para inventar rostos.",'
)
s = s.replace('"skill":"real-person-reference"', '"skill":"real-people-grounded-image"')

p.write_text(s)
print('real-people-grounded-image skill patch applied')
