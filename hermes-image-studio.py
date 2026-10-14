#!/usr/bin/env python3
"""Zero-cost-first image studio adapter for a public Hugging Face Gradio Space.

The adapter never calls a paid image API. It only invokes an explicitly
configured HTTPS *.hf.space endpoint. Missing provider means unavailable,
not a silent paid fallback.
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
    "square": (768, 768),
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


def _space_base_url():
    raw = os.getenv("HERMES_IMAGE_STUDIO_SPACE_URL", "").strip().rstrip("/")
    if not raw:
        raise ImageStudioError(
            "provider_not_configured",
            "O gerador gratuito ainda não está conectado. Configure um Space Hugging Face ZeroGPU e HERMES_IMAGE_STUDIO_SPACE_URL.",
        )
    parsed = urllib.parse.urlsplit(raw)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or not parsed.hostname.endswith(".hf.space")
        or parsed.username
        or parsed.password
        or parsed.port not in (None, 443)
        or parsed.query
        or parsed.fragment
        or parsed.path not in ("", "/")
    ):
        raise ImageStudioError(
            "provider_url_invalid",
            "A URL do gerador precisa ser a URL HTTPS direta de um Space *.hf.space.",
            400,
        )
    return raw


def status():
    configured = bool(os.getenv("HERMES_IMAGE_STUDIO_SPACE_URL", "").strip())
    return {
        "ok": True,
        "provider": "huggingface-zero-gpu-space" if configured else None,
        "configured": configured,
        "paid_fallback": False,
        "message": (
            "Gerador gratuito configurado; disponibilidade e cotas dependem do Hugging Face."
            if configured else
            "Nenhum gerador conectado. O Hermes não fará chamadas pagas automaticamente."
        ),
    }


def _request(url, data=None, headers=None, timeout=TIMEOUT_SECONDS, limit=MAX_IMAGE_BYTES):
    request_headers = {
        "User-Agent": "Hermes-Image-Studio/1.0",
        "Accept": "application/json, text/event-stream, image/png, image/jpeg, image/webp",
    }
    if headers:
        request_headers.update(headers)
    body = None if data is None else json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers=request_headers, method="GET" if body is None else "POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            content_type = response.headers.get("Content-Type", "").lower()
            payload = response.read(limit + 1)
            if len(payload) > limit:
                raise ImageStudioError("response_too_large", "A resposta do gerador excedeu o limite permitido.", 502)
            return payload, content_type
    except ImageStudioError:
        raise
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            raise ImageStudioError("free_quota_exhausted", "O gerador gratuito atingiu o limite temporário. Tente novamente mais tarde.", 429) from exc
        if exc.code in (401, 403):
            raise ImageStudioError("provider_access_denied", "O Space não permite esta solicitação. Confira a visibilidade e as permissões do Space.", 503) from exc
        raise ImageStudioError("provider_http_error", f"O gerador respondeu com HTTP {exc.code}.", 502) from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ImageStudioError("provider_unavailable", "O gerador gratuito está indisponível ou demorou demais para responder.", 503) from exc


def _same_space_url(base, candidate):
    parsed_base = urllib.parse.urlsplit(base)
    if candidate.startswith("/"):
        return base + candidate
    parsed = urllib.parse.urlsplit(candidate)
    if parsed.scheme != "https" or parsed.hostname != parsed_base.hostname or parsed.port not in (None, 443):
        raise ImageStudioError("unsafe_provider_result", "O gerador retornou um endereço de imagem não permitido.", 502)
    return candidate


def _event_data(raw):
    # Gradio streams Server-Sent Events. Return the last valid JSON data frame.
    result = None
    for line in raw.decode("utf-8", "replace").splitlines():
        if not line.startswith("data:"):
            continue
        value = line[5:].strip()
        if not value or value == "[DONE]":
            continue
        try:
            result = json.loads(value)
        except json.JSONDecodeError:
            continue
    return result


def generate(prompt, aspect="square"):
    if not isinstance(prompt, str):
        raise ImageStudioError("invalid_prompt", "Descreva a imagem em texto.", 400)
    prompt = prompt.strip()
    if not 3 <= len(prompt) <= MAX_PROMPT_CHARS:
        raise ImageStudioError("invalid_prompt", "A descrição precisa ter entre 3 e 4.000 caracteres.", 400)
    if re.search(r"(?i)(?:hf_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{15,}|gsk_[A-Za-z0-9_-]{20,}|sk-(?:proj-)?[A-Za-z0-9_-]{20,})", prompt):
        raise ImageStudioError("possible_secret", "Remova possíveis chaves ou credenciais da descrição.", 400)
    if aspect not in ALLOWED_ASPECTS:
        raise ImageStudioError("invalid_aspect", "Formato inválido. Escolha quadrado, retrato ou paisagem.", 400)

    base = _space_base_url()
    headers = {}
    token = os.getenv("HERMES_IMAGE_STUDIO_SPACE_TOKEN", "").strip()
    if token:
        if len(token) > 500 or any(c.isspace() for c in token):
            raise ImageStudioError("provider_token_invalid", "O token do Space está malformado.", 500)
        headers["Authorization"] = "Bearer " + token

    # The worker exposes a named Gradio API: generate(prompt, aspect).
    payload, _ = _request(
        base + "/gradio_api/call/generate",
        {"data": [prompt, aspect], "session_hash": secrets.token_hex(12)},
        headers=headers,
        timeout=30,
        limit=1024 * 1024,
    )
    try:
        accepted = json.loads(payload)
        event_id = accepted.get("event_id")
    except (json.JSONDecodeError, AttributeError):
        event_id = None
    if not isinstance(event_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,200}", event_id):
        raise ImageStudioError("provider_protocol_error", "O gerador retornou uma resposta inesperada.", 502)

    # Gradio returns a stream; poll/read until it emits the final data frame.
    stream_url = base + "/gradio_api/call/generate/" + urllib.parse.quote(event_id, safe="")
    stream, _ = _request(stream_url, headers=headers, timeout=TIMEOUT_SECONDS, limit=2 * 1024 * 1024)
    result = _event_data(stream)
    if not isinstance(result, list) or not result:
        raise ImageStudioError("generation_failed", "O gerador não retornou uma imagem. Tente novamente.", 502)

    image_item = result[0]
    image_url = image_item.get("url") if isinstance(image_item, dict) else None
    if not isinstance(image_url, str) or not image_url:
        raise ImageStudioError("generation_failed", "O gerador terminou sem fornecer um arquivo de imagem.", 502)

    image_url = _same_space_url(base, image_url)
    image_bytes, content_type = _request(
        image_url, headers=headers, timeout=45, limit=MAX_IMAGE_BYTES
    )
    if not content_type.startswith("image/"):
        # Some Gradio file responses omit Content-Type. Verify common signatures.
        if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
            content_type = "image/png"
        elif image_bytes.startswith(b"\xff\xd8\xff"):
            content_type = "image/jpeg"
        elif image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP":
            content_type = "image/webp"
        else:
            raise ImageStudioError("invalid_image_result", "O arquivo retornado não parece ser uma imagem válida.", 502)
    if content_type not in ("image/png", "image/jpeg", "image/webp"):
        raise ImageStudioError("unsupported_image_type", "O gerador retornou um formato de imagem não suportado.", 502)

    return {
        "ok": True,
        "image_base64": base64.b64encode(image_bytes).decode("ascii"),
        "mime": content_type,
        "bytes": len(image_bytes),
        "aspect": aspect,
        "provider": "huggingface-zero-gpu-space",
        "paid_fallback": False,
    }


HTML = r'''<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Hermes Image Studio</title>
<style>
:root{color-scheme:light dark;font-family:system-ui,-apple-system,sans-serif}*{box-sizing:border-box}
body{margin:0;background:Canvas;color:CanvasText}.wrap{max-width:900px;margin:auto;padding:22px}
nav{display:flex;gap:12px;align-items:center;margin-bottom:26px}nav a{color:inherit}
h1{font-size:clamp(26px,5vw,40px);margin:12px 0}p{line-height:1.5;color:GrayText}
form{display:grid;gap:12px}textarea,select,button{font:inherit;border-radius:12px;padding:12px;border:1px solid #888;background:Canvas;color:CanvasText}
textarea{min-height:120px;resize:vertical}button{cursor:pointer;background:#222;color:white;border-color:#222}
button:disabled{opacity:.5;cursor:wait}.row{display:grid;grid-template-columns:1fr 1fr;gap:12px}.status{padding:12px;border:1px solid #8885;border-radius:12px;margin:14px 0}
img{display:block;width:100%;height:auto;border-radius:14px;margin-top:18px}small{color:GrayText}
@media(max-width:600px){.wrap{padding:15px}.row{grid-template-columns:1fr}}
</style></head>
<body><main class="wrap">
<nav><a href="/">← Voltar ao Hermes</a><span>·</span><strong>Image Studio</strong></nav>
<h1>Crie imagens com o Hermes</h1>
<p>O estúdio prioriza geração gratuita. Não chama serviços pagos automaticamente. A disponibilidade depende das cotas do provedor.</p>
<div id="provider" class="status">Verificando gerador…</div>
<form id="form">
<label for="prompt">Descreva a imagem</label>
<textarea id="prompt" maxlength="4000" required minlength="3" placeholder="Ex.: fotografia editorial realista de uma cidade futurista ao amanhecer, luz natural, detalhes nítidos…"></textarea>
<div class="row"><label>Formato
<select id="aspect"><option value="square">Quadrado · 1:1</option><option value="portrait">Retrato · 3:4</option><option value="landscape">Paisagem · 4:3</option></select></label>
<div><small>Modelo inicial: FLUX.1 schnell, 4 etapas</small><p><small>Evite inserir dados pessoais ou segredos.</small></p></div></div>
<button id="submit" type="submit">Gerar imagem</button>
</form>
<div id="status" class="status" role="status">Pronto.</div>
<div id="result"></div>
<script>
const $=id=>document.getElementById(id), form=$('form'), button=$('submit');
async function loadStatus(){try{const r=await fetch('/api/images/status');const d=await r.json();$('provider').textContent=d.message;}catch{$('provider').textContent='Não foi possível consultar o estado do gerador.'}}
form.addEventListener('submit',async e=>{e.preventDefault();if(button.disabled)return;button.disabled=true;$('result').replaceChildren();$('status').textContent='Enviando ao gerador gratuito… isso pode levar alguns minutos.';
try{const r=await fetch('/api/images',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt:$('prompt').value,aspect:$('aspect').value})});const d=await r.json();if(!r.ok)throw new Error(d.error||'Não foi possível gerar a imagem.');const img=document.createElement('img');img.alt='Imagem gerada pelo Hermes';img.src='data:'+d.mime+';base64,'+d.image_base64;$('result').appendChild(img);$('status').textContent='Imagem gerada. Provedor: '+d.provider+' · '+Math.round(d.bytes/1024)+' KB.';}catch(err){$('status').textContent=err.message||'Falha na geração.'}finally{button.disabled=false}});
loadStatus();
</script></main></body></html>'''
