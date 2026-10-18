#!/usr/bin/env python3
"""High-fidelity photographic image studio adapter for Pollinations.ai.

This adapter uses the advanced turbovisionxl model to ensure crisp facial features,
accurate human anatomy, and professional photographic textures without filters.
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
        "provider": "pollinations-turbovision",
        "configured": True,
        "paid_fallback": False,
        "message": "Motor TurboVisionXL ativado para máxima nitidez e perfeição anatômica.",
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
    
    # Codifica o prompt para tráfego HTTP limpo
    encoded_prompt = urllib.parse.quote(prompt)
    
    # Alteramos o parâmetro model para 'turbovisionxl' para ativar o motor de fotografia realista.
    # Adicionamos parâmetros de realismo extremo na própria URL para forçar a perfeição do traço.
    url = (
        f"https://pollinations.ai{encoded_prompt}"
        f"?model=turbovisionxl"
        f"&width={width}"
        f"&height={height}"
        f"&nologo=true"
        f"&private=true"
        f"&safe=false"
        f"&enhance=true"
    )

    return {
        "url": url,
        "model": "turbovisionxl-photorealistic",
        "width": width,
        "height": height
    }
