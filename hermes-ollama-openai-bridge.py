#!/usr/bin/env python3
"""Local, bearer-authenticated OpenAI-compatible bridge to Ollama.

Bind only to loopback. Publish it only through a secured tunnel; never bind to
0.0.0.0. This bridge is intended for owner-operated testing, not as a public
multi-tenant service.
"""
import hmac
import json
import os
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MODEL = os.getenv("HERMES_OLLAMA_MODEL", "llama3.2:3b")
# Keep this name aligned with the Render custom-provider api_key_env.
KEY = os.getenv("HERMES_LLAMA_BRIDGE_KEY", "")
OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
HOST = "127.0.0.1"
PORT = int(os.getenv("HERMES_OLLAMA_BRIDGE_PORT", "8766"))
MAX_BODY = 1_048_576
MAX_RESPONSE = 2_097_152


def make_openai_response(model, content, created=None):
    """Convert an Ollama message into an OpenAI chat-completion response."""
    return {
        "id": "chatcmpl-hermes-local",
        "object": "chat.completion",
        "created": int(created if created is not None else time.time()),
        "model": model,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": content},
            "finish_reason": "stop",
        }],
    }


def validate_payload(payload):
    if not isinstance(payload, dict):
        raise ValueError("json_object_required")
    if payload.get("model", MODEL) != MODEL:
        raise ValueError("model_not_allowed")
    if payload.get("stream", False) is True:
        raise ValueError("streaming_not_supported")
    messages = payload.get("messages")
    if not isinstance(messages, list) or not 1 <= len(messages) <= 64:
        raise ValueError("invalid_messages")
    clean = []
    total = 0
    for message in messages:
        if not isinstance(message, dict):
            raise ValueError("invalid_message")
        role = message.get("role")
        content = message.get("content")
        if role not in ("system", "user", "assistant") or not isinstance(content, str):
            raise ValueError("invalid_message")
        total += len(content)
        if total > 32000:
            raise ValueError("prompt_too_large")
        clean.append({"role": role, "content": content})
    options = payload.get("temperature", 0.3)
    if type(options) not in (int, float) or not 0 <= options <= 2:
        options = 0.3
    num_predict = payload.get("max_tokens", 512)
    if type(num_predict) is not int:
        num_predict = 512
    num_predict = min(max(num_predict, 1), 2048)
    return {"model": MODEL, "messages": clean, "stream": False,
            "options": {"temperature": options, "num_predict": num_predict}}


class Handler(BaseHTTPRequestHandler):
    server_version = "HermesOllamaBridge/1.0"

    def send_json(self, status, data):
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path == "/health":
            self.send_json(200, {"status": "ok", "model": MODEL})
        else:
            self.send_json(404, {"error": "not_found"})

    def do_POST(self):
        if self.path != "/v1/chat/completions":
            self.send_json(404, {"error": "route_not_allowed"})
            return
        if not KEY or not hmac.compare_digest(
            self.headers.get("Authorization", ""), "Bearer " + KEY
        ):
            self.send_json(401, {"error": "unauthorized"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > MAX_BODY:
                self.send_json(413, {"error": "invalid_body_size"})
                return
            raw = self.rfile.read(length)
            if len(raw) != length:
                self.send_json(400, {"error": "incomplete_body"})
                return
            payload = validate_payload(json.loads(raw))
        except (ValueError, TypeError, json.JSONDecodeError):
            self.send_json(400, {"error": "invalid_request"})
            return

        request = urllib.request.Request(
            OLLAMA_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=300) as response:
                result_raw = response.read(MAX_RESPONSE + 1)
            if len(result_raw) > MAX_RESPONSE:
                self.send_json(502, {"error": "response_too_large"})
                return
            result = json.loads(result_raw)
            message = result.get("message", {}) if isinstance(result, dict) else {}
            answer = message.get("content") if isinstance(message, dict) else None
            if not isinstance(answer, str):
                self.send_json(502, {"error": "invalid_ollama_response"})
                return
            self.send_json(200, make_openai_response(MODEL, answer))
        except urllib.error.HTTPError as exc:
            self.send_json(502, {"error": "ollama_error", "status": exc.code})
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            self.send_json(502, {"error": "ollama_unavailable"})

    def log_message(self, fmt, *args):
        # Do not log prompts, response bodies, authorization headers, or secrets.
        print("[ollama-bridge] " + (fmt % args), flush=True)


def main():
    if len(KEY) < 32:
        raise SystemExit("ERRO: HERMES_LLAMA_BRIDGE_KEY ausente ou curta (mínimo 32 caracteres).")
    if not MODEL or len(MODEL) > 100:
        raise SystemExit("ERRO: modelo inválido.")
    if not 1 <= PORT <= 65535:
        raise SystemExit("ERRO: porta inválida.")
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Intermediário OpenAI-compatible ativo em {HOST}:{PORT}; modelo={MODEL}")
    print("Autenticação obrigatória; Ctrl+C encerra.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nIntermediário encerrado.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
