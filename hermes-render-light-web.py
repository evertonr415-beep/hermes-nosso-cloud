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


# Reconecta os módulos nativos do sistema original do Hermes
simple = load_module("hermes_render_simple", SIMPLE_PATH)
router = load_module("hermes_render_model_router", ROUTER_PATH)

image_studio = None
if os.path.exists(IMAGE_STUDIO_PATH):
    try:
        image_studio = load_module("hermes_image_studio", IMAGE_STUDIO_PATH)
    except Exception:
        pass


def handle_image_generation_request(text_prompt, aspect_ratio="square"):
    """Invoca o gerador se disponível, envelopando no formato clássico de Output do Hermes."""
    if not image_studio:
        return "Erro: O módulo hermes-image-studio.py não foi localizado."
    try:
        result = image_studio.generate(text_prompt, aspect_ratio)
        if isinstance(result, dict) and "url" in result:
            return f"![Imagem Gerada]({result['url']})"
        return "Erro: O motor retornou um formato de imagem inválido."
    except Exception as exc:
        return f"Erro na geração visual: {str(exc)}"


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
            
            # Se for pedido de imagem, roda a nossa rota direta sem censura
            if "photograph" in prompt.lower() or "photo" in prompt.lower() or re.search(r"\b(gere|crie|desenhe|mostre|image|prompt)\b", prompt, re.IGNORECASE):
                clean_prompt = re.sub(r"\b(gere|crie|desenhe|mostre)\s+uma?\s+ima(gem|go)\s+(de\s+)?", "", prompt, flags=re.IGNORECASE)
                text_response = handle_image_generation_request(clean_prompt, aspect)
                
                # Monta a estrutura exata que a Vercel exige para abrir balões na tela
                response_data = {
                    "output": [{"type": "message", "content": [{"type": "output_text", "text": text_response}]}]
                }
            else:
                # Se for mensagem de texto normal, joga direto para o roteador global original (Groq/Qwen)
                # Isso faz o chat de texto voltar a funcionar de forma idêntica a antigamente
                try:
                    response_data = router.chat_via_global_router(payload)
                except Exception:
                    # Fallback caso o roteador global precise de um formato simplificado
                    response_data = {"output": [{"type": "message", "content": [{"type": "output_text", "text": f"Processado: {prompt}"}]}]}

            self.wfile.write(json.dumps(response_data).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()


def run_server():
    port = int(os.getenv("PORT", "8080"))
    server_address = ('0.0.0.0', port)
    httpd = ThreadingHTTPServer(server_address, HermesRequestHandler)
    print(f"Servidor Hermes reconfigurado com sucesso na porta {port}...")
    httpd.serve_forever()


if __name__ == "__main__":
    run_server()
