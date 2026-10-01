from pathlib import Path

p = Path('/app/hermes-simple.py')
s = p.read_text()

start = s.index('def generate_zero_cost_image(prompt):')
end = s.index('def generate_zero_cost_edit(image_bytes, mime, prompt):', start)

new = r'''def generate_zero_cost_image(prompt):
    """Generate a free image with retries and multiple independent ZeroGPU mirrors.

    ZeroGPU capacity is bursty, so one provider failing once must not abort the
    request.  We try several compatible Z-Image spaces and retry transient
    AppError/queue failures before reporting unavailability.
    """
    from gradio_client import Client
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
                    # Z-Image mirrors use the same six-argument generation API.
                    # Discover the active endpoint because some mirrors rename it
                    # between /generate_image and /generate_image_1.
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
                print(f'[hermes-simple] ZeroGPU image success space={space} attempt={attempt} bytes={size}', flush=True)
                return mid, space
            except Exception as exc:
                err = f'{space}:attempt{attempt}:{type(exc).__name__}'
                errors.append(err)
                print(f'[hermes-simple] ZeroGPU image provider failed space={space} attempt={attempt} type={type(exc).__name__}', flush=True)
                # Short exponential backoff prevents a brief ZeroGPU saturation
                # from immediately exhausting all mirrors.
                if attempt < 3:
                    time.sleep(2 ** attempt)

    raise RuntimeError('all_free_image_providers_failed ' + ','.join(errors[-18:]))


'''

s = s[:start] + new + s[end:]
p.write_text(s)
