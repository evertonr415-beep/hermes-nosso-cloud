#!/usr/bin/env python3
"""Hermes Render/Spaces lightweight chat web server."""
import importlib.util
import json
import os
import re
import sys
from importlib.machinery import SourceFileLoader
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

SIMPLE_PATH = "/opt/hermes-render/hermes-simple.py"
ROUTER_PATH = "/usr/local/bin/hermes-global-model-router"
AGENT_PATH = "/usr/local/bin/hermes-light-agent"
MEMORY_PATH = "/usr/local/bin/hermes-memory-recovery"
MEMORY_WRITE_PATH = "/usr/local/bin/hermes-memory-write"
IMAGE_STUDIO_PATH = "./hermes-image-studio.py"

os.environ.setdefault("HERMES_GLOBAL_ROUTER_ENABLED", "1")
os.environ.setdefault("HERMES_GLOBAL_KEYLESS_ALLOW", "0")
os.environ.setdefault("HERMES_INFERENCE_MODE", "groq")
os.environ.setdefault("HERMES_PUBLIC_ANONYMOUS_ENABLED", "0")
os.environ.setdefault("HERMES_FALLBACK_ON_HF_402", "0")


def load_module(name, path):
    loader = SourceFileLoader(name, path)
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


# Carrega os módulos originais do ecossistema Hermes
simple = load_module("hermes_render_simple", SIMPLE_PATH)
router = load_module("hermes_render_model_router", ROUTER_PATH)

image_studio = None
if os.path.exists(IMAGE_STUDIO_PATH):
    try:
        image_studio = load_module("hermes_image_studio", IMAGE_STUDIO_PATH)
    except Exception:
        pass

# SUBSTITUIÇÃO CIRÚRGICA DO MENU: Modifica as opções preservando a compatibilidade do HTML original
# Remove os modelos indisponíveis e força a exibição do Qwen e do Raciocínio Avançado na tela
if '<option value="auto">' in simple.HTML:
    simple.HTML = simple.HTML.replace(
        '<option value="auto">Automático · GPT-5.6 Sol</option>',
        '<option value="auto">Groq grátis · Qwen 2.7B</option>\n<option value="advanced">Avançado · Raciocínio Lógico</option>'
    )
else:
    # Fallback de segurança injetando direto no bloco de seleção caso a string mude
    simple.HTML = re.sub(
        r'<select[^>]* id="model"[^>]*>.*?</select>',
        '<select id="model" name="route">\n<option value="auto">Groq grátis · Qwen 2.7B</option>\n<option value="advanced">Avançado · Raciocínio Lógico</option>\n</select>',
        simple.HTML,
        flags=re.DOTALL
    )


def handle_image_generation_request(text_prompt, aspect_ratio="square"):
    """Envia o prompt para o estúdio Pollinations e envelopa no formato Markdown."""
    if not image_studio:
        return "Erro: O adaptador hermes-image-studio.py não está ativo."
    try:
        result = image_studio.generate(text_prompt, aspect_ratio)
        if isinstance(result, dict) and "url" in result:
            return f"![Imagem Gerada]({result['url']})"
        return "Erro: Retorno inválido do gerador de imagem."
    except Exception as exc:
        return f"Erro ao processar imagem: {str(exc)}"


class HermesRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(simple.HTML.encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path in ("/api/chat", "/api/images/together"):
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            try:
                payload = json.loads(post_data.decode('utf-8'))
            except Exception:
                self.send_response(400)
                self.end_headers()
                return

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()

            prompt = payload.get("input", "").strip()
            aspect = payload.get("aspect", "square")
            
            # Se for uma ordem de imagem, desvia para a Pollinations sem censura
            if "photograph" in prompt.lower() or "photo" in prompt.lower() or re.search(r"\b(gere|crie|desenhe|mostre|image|prompt)\b", prompt, re.IGNORECASE):
                clean_prompt = re.sub(r"\b(gere|crie|desenhe|mostre)\s+uma?\s+ima(gem|go)\s+(de\s+)?", "", prompt, flags=re.IGNORECASE)
                text_response = handle_image_generation_request(clean_prompt, aspect)
                
                response_data = {
                    "output": [{"type": "message", "content": [{"type": "output_text", "text": text_response}]}]
                }
            else:
                # Se for mensagem de texto comum, encaminha direto para a inteligência nativa do roteador global
                try:
                    response_data = router.chat_via_global_router(payload)
                except Exception:
                    response_data = {"output": [{"type": "message", "content": [{"type": "output_text", "text": f"Texto processado: {prompt}"}]}]}

            self.wfile.write(json.dumps(response_data).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()


def run_server():
    port = int(os.getenv("PORT", "8080"))
    server_address = ('0.0.0.0', port)
    httpd = ThreadingHTTPServer(server_address, HermesRequestHandler)
    print(f"Servidor Hermes original restaurado com segurança na porta {port}...")
    httpd.serve_forever()


if __name__ == "__main__":
    run_server()
