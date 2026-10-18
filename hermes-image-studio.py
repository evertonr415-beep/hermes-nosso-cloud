#!/usr/bin/env python3
"""Free and unlimited image studio adapter for Pollinations.ai.

This adapter routes text-to-image requests directly to Pollinations AI
using the high-quality black-forest-labs/flux model with safety controls disabled.
"""
import urllib.parse

MAX_PROMPT_CHARS = 4000
ALLOWED_ASPECTS = {
    "square": (1024, 1024),
    "portrait": (768, 1024),
    "landscape": (1024, 768),
}


def status():
    return {
        "ok": True,
        "provider": "pollinations-ai",
        "configured": True,
        "paid_fallback": False,
        "message": "Gerador Pollinations AI otimizado para entrega imediata.",
    }


def generate(prompt, aspect="square"):
    if not isinstance(prompt, str):
        return {"error": "Descreva a imagem em texto."}
        
    prompt = prompt.strip()
    if not 3 <= len(prompt) <= MAX_PROMPT_CHARS:
        return {"error": "A descrição precisa ter entre 3 e 4.000 caracteres."}
        
    if aspect not in ALLOWED_ASPECTS:
        return {"error": "Formato inválido. Escolha quadrado, retrato ou paisagem."}

    width, height = ALLOWED_ASPECTS[aspect]
    
    # Codifica o prompt de texto para o formato aceito em URLs HTTP
    encoded_prompt = urllib.parse.quote(prompt)
    
    # Monta a URL direta. Removemos o teste de download do backend para evitar timeouts.
    # O link é retornado instantaneamente para a Vercel renderizar na tela aberta.
    url = (
        f"https://image.pollinations.ai/prompt/{encoded_prompt}"
        f"?model=flux"
        f"&width={width}"
        f"&height={height}"
        f"&nologo=true"
        f"&private=true"
        f"&safe=false"
    )

    return {
        "url": url,
        "model": "black-forest-labs/flux",
        "width": width,
        "height": height
    }
