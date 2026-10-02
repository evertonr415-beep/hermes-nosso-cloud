from pathlib import Path

p = Path('/app/hermes-simple.py')
s = p.read_text()

start = s.index('def generate_zero_cost_image(prompt):')
end = s.index('def generate_zero_cost_edit(image_bytes, mime, prompt):', start)

new = r'''def generate_zero_cost_image(prompt):
    """Generate a free image with retries, mirrors, and a short capacity cooldown.

    Pose/scene-sensitive prompts prefer Qwen Image first because it generally
    follows longer structured composition instructions better than the turbo
    mirrors. Turbo providers remain automatic fallbacks.
    """
    from gradio_client import Client

    now = time.time()
    cooldown_until = float(getattr(generate_zero_cost_image, 'cooldown_until', 0) or 0)
    if cooldown_until > now:
        remaining = max(1, int(cooldown_until - now))
        print(f'[hermes-simple] ZeroGPU cooldown active remaining={remaining}s', flush=True)
        raise RuntimeError(f'free_image_capacity_cooldown:{remaining}')

    token = (os.getenv('HF_TOKEN') or '').strip() or None
    configured = (os.getenv('HF_ZERO_IMAGE_SPACE') or '').strip()
    low=(prompt or '').lower()
    strict_terms=(
        'primary composition:', 'primary pose:', 'leg position:',
        'lying down', 'clearly visible modern bed', 'keep the subject seated',
        'keep the subject lying down', 'preserve the requested leg position',
        'full-body composition',
    )
    strict_composition=any(t in low for t in strict_terms)

    if strict_composition:
        spaces = [x for x in [
            'Qwen/Qwen-Image',
            configured,
            'mrfakename/Z-Image-Turbo',
            'Tongyi-MAI/Z-Image-Turbo',
            'mcp-tools/Z-Image-Turbo',
            'anycoderapps/Z-Image-Turbo',
        ] if x]
    else:
        spaces = [x for x in [
            configured,
            'mrfakename/Z-Image-Turbo',
            'Tongyi-MAI/Z-Image-Turbo',
            'mcp-tools/Z-Image-Turbo',
            'anycoderapps/Z-Image-Turbo',
            'Qwen/Qwen-Image',
        ] if x]

    print(f'[hermes-simple] image routing strict_composition={strict_composition} provider_first={next(iter(dict.fromkeys(spaces)),"none")}', flush=True)
    errors = []

    for space in dict.fromkeys(spaces):
        max_attempts = 2 if space == 'Qwen/Qwen-Image' else 3
        for attempt in range(1, max_attempts + 1):
            try:
                client = Client(space, token=token, verbose=False)
                if space == 'Qwen/Qwen-Image':
                    # Horizontal framing gives lying-on-bed/full-scene requests
                    # more room; otherwise preserve the established square mode.
                    aspect = '16:9' if any(t in low for t in ('lying down','visible modern bed','on or in a visible bed')) else '1:1'
                    result = client.predict(prompt, 42, True, aspect, 4.0, 40, True, api_name='/infer')
                else:
                    api_name = '/generate_image'
                    try:
                        info = client.view_api(return_format='dict') or {}
                        endpoints = info.get('named_endpoints') or {}
                        preferred = ['/generate_image', '/generate_image_1']
                        for candidate in preferred:
                            if candidate in endpoints:
                                api_name = candidate
                                break
                        else:
                            candidates = [
                                name for name, spec in endpoints.items()
                                if len((spec or {}).get('parameters') or []) >= 6
                            ]
                            if candidates:
                                api_name = candidates[0]
                    except Exception:
                        pass
                    result = client.predict(prompt, 1024, 1024, 9, 42, True, api_name=api_name)

                mid, size = _store_gradio_result(result)
                generate_zero_cost_image.cooldown_until = 0
                print(f'[hermes-simple] ZeroGPU image success space={space} attempt={attempt} bytes={size} strict_composition={strict_composition}', flush=True)
                return mid, space
            except Exception as exc:
                err = f'{space}:attempt{attempt}:{type(exc).__name__}'
                errors.append(err)
                print(f'[hermes-simple] ZeroGPU image provider failed space={space} attempt={attempt} type={type(exc).__name__}', flush=True)
                if attempt < max_attempts:
                    time.sleep(2 ** attempt)

    generate_zero_cost_image.cooldown_until = time.time() + 10 * 60
    print('[hermes-simple] ZeroGPU capacity cooldown set seconds=600', flush=True)
    raise RuntimeError('free_image_capacity_cooldown:600 ' + ','.join(errors[-18:]))


'''

s = s[:start] + new + s[end:]
p.write_text(s)
