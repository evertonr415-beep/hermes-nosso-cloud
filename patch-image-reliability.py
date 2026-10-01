from pathlib import Path

p = Path('/app/hermes-simple.py')
s = p.read_text()

start = s.index('def generate_zero_cost_image(prompt):')
end = s.index('def generate_zero_cost_edit(image_bytes, mime, prompt):', start)

new = r'''def generate_zero_cost_image(prompt):
    """Generate a free image with retries, mirrors, and a short capacity cooldown.

    If every free provider fails, remember that state for 10 minutes so the next
    request fails fast instead of burning time and queue attempts. Paid providers
    are never called from this function.
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
    spaces = [x for x in [
        configured,
        'mrfakename/Z-Image-Turbo',
        'Tongyi-MAI/Z-Image-Turbo',
        'mcp-tools/Z-Image-Turbo',
        'anycoderapps/Z-Image-Turbo',
        'Qwen/Qwen-Image',
    ] if x]
    errors = []

    for space in dict.fromkeys(spaces):
        for attempt in range(1, 4):
            try:
                client = Client(space, token=token, verbose=False)
                if space == 'Qwen/Qwen-Image':
                    result = client.predict(prompt, 42, True, '1:1', 4.0, 40, True, api_name='/infer')
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
                print(f'[hermes-simple] ZeroGPU image success space={space} attempt={attempt} bytes={size}', flush=True)
                return mid, space
            except Exception as exc:
                err = f'{space}:attempt{attempt}:{type(exc).__name__}'
                errors.append(err)
                print(f'[hermes-simple] ZeroGPU image provider failed space={space} attempt={attempt} type={type(exc).__name__}', flush=True)
                if attempt < 3:
                    time.sleep(2 ** attempt)

    generate_zero_cost_image.cooldown_until = time.time() + 10 * 60
    print('[hermes-simple] ZeroGPU capacity cooldown set seconds=600', flush=True)
    raise RuntimeError('free_image_capacity_cooldown:600 ' + ','.join(errors[-18:]))


'''

s = s[:start] + new + s[end:]
p.write_text(s)
