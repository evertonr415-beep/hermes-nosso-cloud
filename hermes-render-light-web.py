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

# Configurações padrão seguras para o ambiente Render
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


# Carrega o layout original do Hermes sem quebras
simple = load_module("hermes_render_simple", SIMPLE_PATH)
router = load_module("hermes_render_model_router", ROUTER_PATH)
agent = load_module("hermes_render_light_agent", AGENT_PATH)
memory = load_module("hermes_render_memory_recovery", MEMORY_PATH)
memory_writer = load_module("hermes_render_memory_write", MEMORY_WRITE_PATH)

image_studio = None
if os.path.exists(IMAGE_STUDIO_PATH):
    try:
        image_studio = load_module("hermes_image_studio", IMAGE_STUDIO_PATH)
    except Exception:
        pass

# Ajusta o menu de seleção do layout original
simple.HTML = (
    simple.HTML
    .replace(
        '<option value="auto">Automático · GPT-5.6 Sol</option>',
        '<option value="auto">Groq grátis · Qwen 27B</option>'
    )
)


def handle_image_generation_request(text_prompt, aspect_ratio="square"):
    """Invoca a Pollinations via TurboVision e injeta tags Markdown de exibição."""
    if not image_studio:
        return {"response": "Erro: O adaptador hermes-image-studio.py não está ativo."}
    try:
        result = image_studio.generate(text_prompt, aspect_ratio)
        if isinstance(result, dict) and "url" in result:
            # Força o link a ir formatado em Markdown para abrir estourado na tela
            return {"response": f"![Imagem Gerada]({result['url']})"}
        else:
            return {"response": "Erro: Retorno inválido do motor de imagem."}
    except Exception as exc:
        return {"response": f"Erro ao processar imagem: {str(exc)}"}


class HermesRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(simple.HTML.encode("utf-8"))
        elif self.path == "/api/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            status_data = {"ok": True, "image_engine": "active" if image_studio else "inactive"}
            self.wfile.write(json.dumps(status_data).encode("utf-8"))
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
            
            # Se for comando ou prompt de fotografia/imagem, desvia para a Pollinations
            if "photograph" in prompt.lower() or "photo" in prompt.lower() or re.search(r"\b(gere|crie|desenhe|mostre|image|prompt)\b", prompt, re.IGNORECASE):
                clean_prompt = re.sub(r"\b(gere|crie|desenhe|mostre)\s+uma?\s+ima(gem|go)\s+(de\s+)?", "", prompt, flags=re.IGNORECASE)
                response_data = handle_image_generation_request(clean_prompt, aspect)
            else:
                # Resposta padrão estável para mensagens de texto
                response_data = {"response": f"Processado como texto: {prompt}"}

            self.wfile.write(json.dumps(response_data).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()


def run_server():
    port = int(os.getenv("PORT", "10000"))
    server_address = ('0.0.0.0', port)
    httpd = ThreadingHTTPServer(server_address, HermesRequestHandler)
    print(f"Servidor Hermes original restaurado na porta {port}...")
    httpd.serve_forever()


if __name__ == "__main__":
    run_server()
