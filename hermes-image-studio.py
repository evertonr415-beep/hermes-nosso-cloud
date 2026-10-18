#!/usr/bin/env python3
"""Together AI image studio adapter for Hermescloud.

This adapter routes text-to-image requests to the Together AI Inference API
using the high-quality black-forest-labs/FLUX.1-dev model with safety filters disabled.
"""
import base64
import json
import os
import re
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request

MAX_PROMPT_CHARS = 4000
MAX_IMAGE_BYTES = 12 * 1024 * 1024
ALLOWED_ASPECTS = {
    "square": (1024, 1024),
    "portrait": (768, 1024),
    "landscape": (1024, 768),
}
TIMEOUT_SECONDS = 180


class ImageStudioError(RuntimeError):
    def __init__(self, code, message, status=503):
        super().__init__(code)
        self.code = code
        self.message = message
        self.status = status


def status():
    configured = bool(os.getenv("TOGETHER_API_KEY", "").strip())
    return {
        "ok": True,
        "provider": "together-ai" if configured else None,
        "configured": configured,
        "paid_fallback": True,
        "message": (
            "Gerador Together AI configurado e ativo."
            if configured else
            "Nenhum gerador conectado. Configure a variável TOGETHER_API_KEY no Render."
        ),
    }


def _request(url, data=None, headers=None, timeout=TIMEOUT_SECONDS):
    request_headers = {
        "User-Agent": "Hermes-Image-Studio/1.0",
        "Accept": "application/json",
    }
    if headers:
        request_headers.update(headers)
    body = None if data is None else json.dumps(data).encode("utf-8")
    if body is not None:
        request_headers["Content-Type"] = "application/json"
        
    req = urllib.request.Request(url, data=body, headers=request_headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            payload = response.read()
            return payload
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            raise ImageStudioError("quota_exhausted", "Limite de requisições atingido na Together AI.", 429) from exc
        if exc.code in (401, 403):
            raise ImageStudioError("access_denied", "Chave TOGETHER_API_KEY inválida ou sem permissão.", 503) from exc
        raise ImageStudioError("provider_http_error", f"A Together AI respondeu com HTTP {exc.code}.", 502) from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ImageStudioError("provider_unavailable", "O servidor da Together AI demorou demais para responder.", 503) from exc


def generate(prompt, aspect="square"):
    if not isinstance(prompt, str):
        raise ImageStudioError("invalid_prompt", "Descreva a imagem em texto.", 400)
    prompt = prompt.strip()
    if not 3 <= len(prompt) <= MAX_PROMPT_CHARS:
        raise ImageStudioError("invalid_prompt", "A descrição precisa ter entre 3 e 4.000 caracteres.", 400)
    if aspect not in ALLOWED_ASPECTS:
        raise ImageStudioError("invalid_aspect", "Formato inválido. Escolha quadrado, retrato ou paisagem.", 400)

    api_key = os.getenv("TOGETHER_API_KEY", "").strip()
    if not api_key:
        raise ImageStudioError(
            "provider_not_configured",
            "A variável TOGETHER_API_KEY não foi configurada nas variáveis de ambiente do Render.",
            500
        )

    width, height = ALLOWED_ASPECTS[aspect]
    url = "https://together.xyz"
    
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    
    # Payload configurado seguindo estritamente a documentação da Together AI
    # O parâmetro disable_safety_checker definido como True desativa o filtro de censura
    api_data = {
        "model": "black-forest-labs/FLUX.1-dev",
        "prompt": prompt,
        "width": width,
        "height": height,
        "steps": 28,
        "n": 1,
        "response_format": "b64_json",
        "disable_safety_checker": True
    }

    response_payload = _request(url, data=api_data, headers=headers)
    
    try:
        result = json.loads(response_payload)
        image_data = result.get("data", [{}])[0]
        
        # Caso a API retorne em formato Base64, convertemos ou retornamos a URL
        if "b64_json" in image_data:
            # Retorna uma URL simulada contendo o dicionário com os metadados esperados pelo seu ecossistema
            return {
                "url": f"data:image/png;base64,{image_data['b64_json']}",
                "model": "black-forest-labs/FLUX.1-dev",
                "width": width,
                "height": height
            }
        elif "url" in image_data:
            return {
                "url": image_data["url"],
                "model": "black-forest-labs/FLUX.1-dev",
                "width": width,
                "height": height
            }
        else:
            raise ImageStudioError("generation_failed", "A resposta da API não continha dados de imagem válidos.", 502)
            
    except (json.JSONDecodeError, KeyError, IndexError) as exc:
        raise ImageStudioError("provider_protocol_error", "Erro ao processar a resposta de imagem da Together AI.", 502) from exc
