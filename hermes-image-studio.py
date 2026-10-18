#!/usr/bin/env python3
"""Free and unlimited image studio adapter for Pollinations.ai.

This adapter routes text-to-image requests to the free Pollinations AI endpoint
using the high-quality black-forest-labs/flux.1-schnell model with optional safety controls.
"""
import json
import os
import urllib.error
import urllib.parse
import urllib.request

MAX_PROMPT_CHARS = 4000
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
    # Pollinations não precisa de chaves, então está sempre ativa e configurada
    return {
        "ok": True,
        "provider": "pollinations-ai",
        "configured": True,
        "paid_fallback": False,
        "message": "Gerador Pollinations AI ativo. Uso gratuito e ilimitado liberado.",
    }


def generate(prompt, aspect="square"):
    if not isinstance(prompt, str):
        raise ImageStudioError("invalid_prompt", "Descreva a imagem em texto.", 400)
    prompt = prompt.strip()
    if not 3 <= len(prompt) <= MAX_PROMPT_CHARS:
        raise ImageStudioError("invalid_prompt", "A descrição precisa ter entre 3 e 4.000 caracteres.", 400)
    if aspect not in ALLOWED_ASPECTS:
        raise ImageStudioError("invalid_aspect", "Formato inválido. Escolha quadrado, retrato ou paisagem.", 400)

    width, height = ALLOWED_ASPECTS[aspect]
    
    # Codifica o prompt de texto para o formato aceito em URLs HTTP
    encoded_prompt = urllib.parse.quote(prompt)
    
    # Monta a URL de requisição direta ao endpoint estável da Pollinations
    # Usando o modelo FLUX, definindo as dimensões e desativando o filtro seguro (&safe=false)
    url = (
        f"https://image.pollinations.ai/prompt/{encoded_prompt}"
        f"?model=flux"
        f"&width={width}"
        f"&height={height}"
        f"&nologo=true"
        f"&private=true"
        f"&safe=false"
    )

    # A Pollinations entrega a imagem gerada diretamente. Retornamos a estrutura de metadados
    # que o ecossistema do seu Hermes na Render e Vercel espera ler.
    try:
        # Apenas testamos se o endpoint está respondendo adequadamente antes de liberar a URL
        req = urllib.request.Request(url, method="GET", headers={"User-Agent": "Hermes-Image-Studio/1.0"})
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as response:
            if response.status == 200:
                return {
                    "url": url,
                    "model": "black-forest-labs/flux.1-schnell",
                    "width": width,
                    "height": height
                }
            else:
                raise ImageStudioError("generation_failed", f"O provedor respondeu com status {response.status}", 502)
                
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ImageStudioError("provider_unavailable", "O gerador gratuito da Pollinations demorou demais para responder.", 503) from exc
