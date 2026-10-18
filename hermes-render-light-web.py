#!/usr/bin/env python3
"""Hermes Render/Spaces lightweight chat web server - Autonomous Version."""
import json
import os
import re
import sys
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

IMAGE_STUDIO_PATH = "./hermes-image-studio.py"

# Configurações básicas padrão para o ambiente de contêiner da Render
os.environ.setdefault("HERMES_GLOBAL_ROUTER_ENABLED", "1")
os.environ.setdefault("HERMES_GLOBAL_KEYLESS_ALLOW", "0")
os.environ.setdefault("HERMES_INFERENCE_MODE", "groq")
os.environ.setdefault("HERMES_PUBLIC_ANONYMOUS_ENABLED", "0")
os.environ.setdefault("HERMES_FALLBACK_ON_HF_402", "0")

# HTML Base nativo para garantir que a interface abra mesmo se os arquivos locais falharem
DEFAULT_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Hermes Cloud Chat</title>
    <style>
        body { font-family: sans-serif; background: #121212; color: #fff; padding: 20px; }
        #chat { max-width: 600px; margin: 0 auto; }
        input { width: 100%; padding: 10px; background: #222; color: #fff; border: 1px solid #444; }
    </style>
</head>
<body>
    <div id="chat">
        <h2>Groq grátis · Qwen 27B</h2>
        <div id="output"></div>
        <input type="text" id="input" placeholder="Digite sua mensagem ou comando de imagem...">
    </div>
</body>
</html>
"""

# Tenta carregar o módulo de imagem com segurança
image_studio = None
if os.path.exists(IMAGE_STUDIO_PATH):
    try:
        from importlib.machinery import SourceFileLoader
        import importlib.util
        loader = SourceFileLoader("hermes_image_studio", IMAGE_STUDIO_PATH)
        spec = importlib.util.spec_from_loader("hermes_image_studio", loader)
        image_studio = importlib.util.module_from_spec(spec)
        sys.modules["hermes_image_studio"] = image_studio
        loader.exec_module(image_studio)
    except Exception:
        print("Aviso: Falha ao carregar o módulo hermes-image-studio.py")


def handle_image_generation_request(text_prompt, aspect_ratio="square"):
    """Invoca o gerador de imagem da Pollinations e retorna envolvido em Markdown."""
    if not image_studio:
        return {"response": "Erro: O adaptador hermes-image-studio.py não foi localizado ou está corrompido."}
    try:
        result = image_studio.generate(text_prompt, aspect_ratio)
        if isinstance(result, dict) and "url" in result:
            # Envia no padrão Markdown para abrir a imagem automaticamente na tela
            return {"response": f"![Imagem Gerada]({result['url']})"}
        else:
            return {"response": "Erro: O motor de imagem retornou um formato inválido."}
    except Exception as exc:
        return {"response": f"Erro na geração de imagem: {str(exc)}"}


class HermesRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(DEFAULT_HTML.encode("utf-8"))
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
            
            # Captura ordens de imagem baseadas em palavras em inglês ou comandos em português
            if "photograph" in prompt.lower() or "photo" in prompt.lower() or re.search(r"\b(gere|crie|desenhe|mostre|image|prompt)\b", prompt, re.IGNORECASE):
                clean_prompt = re.sub(r"\b(gere|crie|desenhe|mostre)\s+uma?\s+ima(gem|go)\s+(de\s+)?", "", prompt, flags=re.IGNORECASE)
                response_data = handle_image_generation_request(clean_prompt, aspect)
            else:
                # Retorno de texto padrão para o chat continuar respondendo normalmente
                response_data = {"response": f"Processado como texto: {prompt}"}

            self.wfile.write(json.dumps(response_data).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()


def run_server():
    port = int(os.getenv("PORT", "10000"))
    server_address = ('0.0.0.0', port)
    httpd = ThreadingHTTPServer(server_address, HermesRequestHandler)
    print(f"Servidor HTTP Independente ativo na porta {port}...")
    httpd.serve_forever()


if __name__ == "__main__":
    run_server()
