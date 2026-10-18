#!/usr/bin/env python3
"""Authenticated Together AI image-generation adapter for Hermes.

The provider safety checker remains enabled. API credentials are read only
from TOGETHER_API_KEY and are never returned to the client or written to logs.
"""
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request

API_URL = "https://api.together.xyz/v1/images/generations"
MODEL = "black-forest-labs/FLUX.1-dev"
MAX_PROMPT_CHARS = 4000
TIMEOUT_SECONDS = 180


class TogetherImageError(RuntimeError):
    def __init__(self, code, message, status=503):
        super().__init__(code)
        self.code = code
        self.message = message
        self.status = status


def generate(prompt, width=1024, height=1024):
    if not isinstance(prompt, str):
        raise TogetherImageError("invalid_prompt", "Descreva a imagem em texto.", 400)
    prompt = prompt.strip()
    if not 3 <= len(prompt) <= MAX_PROMPT_CHARS:
        raise TogetherImageError("invalid_prompt", "A descrição precisa ter entre 3 e 4.000 caracteres.", 400)
    if re.search(r"(?i)(?:hf_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{15,}|gsk_[A-Za-z0-9_-]{20,}|sk-(?:proj-)?[A-Za-z0-9_-]{20,})", prompt):
        raise TogetherImageError("possible_secret", "Remova possíveis chaves ou credenciais da descrição.", 400)
    if type(width) is not int or type(height) is not int or width not in (768, 1024) or height not in (768, 1024):
        raise TogetherImageError("invalid_dimensions", "As dimensões permitidas são 768 ou 1024 pixels.", 400)

    api_key = os.getenv("TOGETHER_API_KEY", "").strip()
    if not api_key:
        raise TogetherImageError("provider_not_configured", "O gerador Together AI não está configurado no servidor.", 503)

    # Explicitly keep the safety checker enabled. Do not set this to True.
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "width": width,
        "height": height,
        "steps": 28,
        "n": 1,
        "response_format": "url",
        "disable_safety_checker": False,
    }
    request = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": "Bearer " + api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Hermes-Image-Studio/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            raw = response.read(2 * 1024 * 1024 + 1)
            if len(raw) > 2 * 1024 * 1024:
                raise TogetherImageError("response_too_large", "A resposta do gerador excedeu o limite permitido.", 502)
    except TogetherImageError:
        raise
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            raise TogetherImageError("provider_rate_limited", "A Together AI atingiu um limite temporário. Tente novamente mais tarde.", 429) from exc
        if exc.code in (401, 403):
            raise TogetherImageError("provider_access_denied", "A Together AI recusou a solicitação. Confira a chave e as permissões no servidor.", 503) from exc
        raise TogetherImageError("provider_http_error", f"A Together AI respondeu com HTTP {exc.code}.", 502) from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise TogetherImageError("provider_unavailable", "A Together AI está indisponível ou demorou demais para responder.", 503) from exc

    try:
        data = json.loads(raw.decode("utf-8"))
        image_url = data["data"][0]["url"]
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError, IndexError, TypeError):
        raise TogetherImageError("provider_protocol_error", "A Together AI não retornou uma URL de imagem válida.", 502)

    if not isinstance(image_url, str):
        raise TogetherImageError("provider_protocol_error", "A Together AI não retornou uma URL de imagem válida.", 502)
    parsed = urllib.parse.urlsplit(image_url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise TogetherImageError("unsafe_provider_result", "O provedor retornou uma URL de imagem não permitida.", 502)

    return {
        "ok": True,
        "image_url": image_url,
        "model": MODEL,
        "provider": "together-ai",
        "width": width,
        "height": height,
    }
