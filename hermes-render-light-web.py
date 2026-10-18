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

# Configurações básicas padrão para o ambiente de contêiner da Render
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


simple = load_module("hermes_render_simple", SIMPLE_PATH)
router = load_module("hermes_render_model_router", ROUTER_PATH)
agent = load_module("hermes_render_light_agent", AGENT_PATH)
memory = load_module("hermes_render_memory_recovery", MEMORY_PATH)
memory_writer = load_module("hermes_render_memory_write", MEMORY_WRITE_PATH)

# Tenta acionar o adaptador de imagem
image_studio = None
if os.path.exists(IMAGE_STUDIO_PATH):
    try:
        image_studio = load_module("hermes_image_studio", IMAGE_STUDIO_PATH)
    except Exception:
        pass

# Ajusta as opções do painel de modelos
simple.HTML = (
    simple.HTML
    .replace(
        '<option value="auto">Automático · GPT-5.6 Sol</option>',
        '<option value="auto">Groq grátis · Qwen 27B</option>'
    )
)


def handle_image_generation_request(text_prompt, aspect_ratio="square"):
    """Invoca o gerador de imagem da Pollinations e retorna envolvido em Markdown."""
    if not image_studio:
        return {"response": "Erro: O adaptador hermes-image-studio.py não foi localizado."}
    try:
        result = image_studio.generate(text_prompt, aspect_ratio)
        if isinstance(result, dict) and "url" in result:
            # Entrega em formato Markdown direto para o chat da Vercel forçar a abertura automática
            return {"response": f"![Imagem Gerada]({result['url']})"}
        else:
            return {"response": "Erro: Retorno inválido do motor de imagem."}
    except Exception as exc:
        return {"response": f"Erro na geração de imagem: {str(exc)}"}


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
        # Escuta de forma unificada qualquer rota de chat vinda do frontend
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
            
            # Unificação Crítica: Qualquer rota processa prompts normais ou ordens de fotografia/imagem
            # Identifica gatilhos de criação visual ou prompts complexos em inglês de fotografia
            if "photograph" in prompt.lower() or "photo" in prompt.lower() or re.search(r"\b(gere|crie|desenhe|mostre|image|prompt)\b", prompt, re.IGNORECASE):
                # Limpa os comandos em português caso existam no início do texto
                clean_prompt = re.sub(r"\b(gere|crie|desenhe|mostre)\s+uma?\s+ima(gem|go)\s+(de\s+)?", "", prompt, flags=re.IGNORECASE)
                response_data = handle_image_generation_request(clean_prompt, aspect)
            else:
                # Fallback de texto seguro para o chat não travar caso seja uma mensagem comum
                response_data = {"response": f"Processado como texto: {prompt}"}

            self.wfile.write(json.dumps(response_data).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()


def run_server():
    # Coleta a porta que a Render exige (geralmente 10000) e escuta em todas as interfaces (0.0.0.0)
    port = int(os.getenv("PORT", "10000"))
    server_address = ('0.0.0.0', port)
    httpd = ThreadingHTTPServer(server_address, HermesRequestHandler)
    print(f"Servidor HTTP do Hermes unificado e ativo na porta {port}...")
    httpd.serve_forever()


if __name__ == "__main__":
    run_server()
