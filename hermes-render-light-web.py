#!/usr/bin/env python3
"""Hermes Render/Spaces lightweight chat web server: no s6 or Railway bridge.

The existing hermes-simple UI is preserved. Only text inference is enabled
in this bootstrap mode. The full agent remains in the image and can be run
with HERMES_STARTUP_MODE=full if s6 is viable on the target platform.
"""
import importlib.util
import json
import os
import sys
from importlib.machinery import SourceFileLoader
from http.server import ThreadingHTTPServer

SIMPLE_PATH = "/opt/hermes-render/hermes-simple.py"
ROUTER_PATH = "/usr/local/bin/hermes-global-model-router"

def load_module(name, path):
    loader = SourceFileLoader(name, path)
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module

simple = load_module("hermes_render_simple", SIMPLE_PATH)
router = load_module("hermes_render_model_router", ROUTER_PATH)

# The legacy UI displayed Railway-specific model names and a Railway link.
# In lightweight mode all chat prompts use ONLY this deployment's global router.
simple.HTML = (simple.HTML
    .replace("Automático · GPT-5.6 Sol", "Hugging Face · Automático")
    .replace('<option value="matrix">Matrix</option>', "")
    .replace('<option value="local">Hermes Local</option>', "")
    .replace("Hermes pode usar ferramentas, memória e skills em segundo plano.",
             "Modo leve: chat de texto. Ferramentas avançadas requerem o Hermes completo.")
)
simple.HTML = simple.HTML.replace(
    "https://hermes-cloud-production-13fb.up.railway.app", "/"
)

def chat_via_global_router(payload):
    prompt = payload.get("input", "")
    if not isinstance(prompt, str) or not 1 <= len(prompt.strip()) <= 8000:
        raise ValueError("message_invalid")
    result = router.run({
        "prompt": prompt.strip(),
        "sensitivity": "normal",  # Never opt into public-only, unaudited endpoints.
        "provider_id": "huggingface-official",
        "max_tokens": 512,
    })
    if not result.get("ok"):
        failures = result.get("failures") or []
        codes = [str(f.get("status")) for f in failures if f.get("status")]
        # Expose only HTTP codes; never tokens, provider error bodies or prompts.
        label = "HTTP " + ",".join(codes) if codes else str(result.get("error","unavailable"))
        raise RuntimeError("model_unavailable: " + label)
    output = {"output": [{
        "type": "message",
        "content": [{"type":"output_text","text":result["response"]}]
    }]}
    return output, "huggingface-official"

simple.call_upstream = chat_via_global_router

if __name__ == "__main__":
    # The endpoint can become healthy even when inference is not configured.
    # Without a password, all other endpoints stay unauthorized (fail closed).
    port = int(os.environ.get("PORT","8080"))
    if not 1 <= port <= 65535:
        raise SystemExit("invalid PORT")
    print("[hermes-light] ready port=%d auth_configured=%s inference_configured=%s" % (
        port, bool(simple.PASSWORD), bool(os.getenv("HF_TOKEN"))), flush=True)
    ThreadingHTTPServer(("0.0.0.0",port), simple.Handler).serve_forever()
