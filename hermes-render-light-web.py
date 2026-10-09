#!/usr/bin/env python3
"""Hermes Render/Spaces lightweight chat web server: no s6 or Railway bridge.

The existing hermes-simple UI is preserved. Only text inference is enabled
in this bootstrap mode. The full agent remains in the image and can be run
with HERMES_STARTUP_MODE=full if s6 is viable on the target platform.
"""
import importlib.util
import json
import os
import re
import sys
from importlib.machinery import SourceFileLoader
from http.server import ThreadingHTTPServer

SIMPLE_PATH = "/opt/hermes-render/hermes-simple.py"
ROUTER_PATH = "/usr/local/bin/hermes-global-model-router"
AGENT_PATH = "/usr/local/bin/hermes-light-agent"

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

# The legacy UI displayed Railway-specific model names and a Railway link.
# In lightweight mode all chat prompts use ONLY this deployment's global router.
simple.HTML = (simple.HTML
    .replace('<option value="auto">Automático · GPT-5.6 Sol</option>', '<option value="auto">Groq grátis · Qwen 27B</option><option value="advanced">Avançado · raciocínio + ferramentas</option>')
    .replace('<option value="matrix">Matrix</option>', "")
    .replace('<option value="local">Hermes Local</option>', "")
    .replace("Hermes pode usar ferramentas, memória e skills em segundo plano.",
             "Groq Free: limites de uso diário. Não envie informações confidenciais.")
)
# The previous sidebar "Advanced" link navigated to Railway (or "/"),
# so it never activated the new Render advanced chat mode.
# Replace it only in the lightweight Render interface; leave the full UI intact.
old_sidebar_link = (
    '<a class="advanced" href="' + simple.ADVANCED_URL +
    '" target="_blank">⚙ Avançado</a>'
)
new_sidebar_button = (
    '<button class="advanced" type="button" id="advanced-mode-link">'
    '⚙ Avançado · ferramentas</button>'
)
if old_sidebar_link not in simple.HTML:
    raise RuntimeError("advanced sidebar UI anchor not found")
simple.HTML = simple.HTML.replace(old_sidebar_link, new_sidebar_button, 1)
simple.HTML = simple.HTML.replace(
    '.advanced:hover{',
    '.advanced{width:100%;border:0;background:transparent;text-align:left;cursor:pointer}.advanced:hover{',
    1,
)
simple.HTML = simple.HTML.replace(
    "$('#menu').onclick=()=>$('#sidebar').classList.toggle('open');",
    "$('#menu').onclick=()=>$('#sidebar').classList.toggle('open');\\n"
    "const advancedButton=$('#advanced-mode-link');\\n"
    "if(advancedButton) advancedButton.onclick=()=>{\\n"
    "  $('#model').value='advanced';\\n"
    "  $('#sidebar').classList.remove('open');\\n"
    "  statusEl.textContent='modo avançado';\\n"
    "  input.focus();\\n"
    "};",
    1,
)
if "id=\"advanced-mode-link\"" not in simple.HTML:
    raise RuntimeError("advanced sidebar button unavailable")

simple.HTML = simple.HTML.replace(
    "https://hermes-cloud-production-13fb.up.railway.app", "/"
)

class ModelUnavailable(RuntimeError):
    """Public error that is safe to show in the chat without exposing secrets."""
    def __init__(self, user_message):
        super().__init__("inference_provider_unavailable")
        self.user_message = user_message


def chat_via_global_router(payload):
    prompt = payload.get("input", "")
    if not isinstance(prompt, str) or not 1 <= len(prompt.strip()) <= 8000:
        raise ValueError("message_invalid")
    # Forward only this text: not Supabase memory, files or tool outputs.
    if re.search(r"(?i)(?:hf_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{15,}|sk-(?:proj-)?[A-Za-z0-9_-]{20,}|bearer\s+[A-Za-z0-9._-]{16,})", prompt):
        raise ModelUnavailable("Não enviei a mensagem: foi detectada uma possível chave privada.")
    mode = os.getenv("HERMES_INFERENCE_MODE", "groq").strip().lower()
    req = {"prompt": prompt.strip(), "sensitivity": "normal", "max_tokens": 512}
    if mode == "groq":
        req["provider_id"] = "groq-free"
    elif mode == "anonymous":
        req.update({"provider_id": "anonymous-public", "sensitivity": "public"})
    if mode == "groq" and payload.get("route") == "advanced" and os.getenv("HERMES_AGENT_TOOLS_ENABLED", "1") == "1":
        result = agent.answer(prompt.strip())
    else:
        result = router.run(req)
    if not result.get("ok"):
        failures = result.get("failures") or []
        statuses = [f.get("status") for f in failures if isinstance(f,dict) and isinstance(f.get("status"),int)]
        errors = [f.get("error") for f in failures if isinstance(f,dict)]
        # Classify using only local error codes. Never display provider
        # response bodies, prompts or credentials in an error message.
        if mode == "groq":
            if not os.getenv("GROQ_API_KEY", "").strip():
                public_message = "Falta GROQ_API_KEY no Render. Crie uma chave gratuita em console.groq.com/keys e salve em Environment."
            elif result.get("error") == "no_authorized_healthy_backends":
                public_message = "A chave GROQ_API_KEY parece inválida ou ausente."
            elif 401 in statuses:
                public_message = "Groq HTTP 401: chave GROQ_API_KEY inválida, revogada ou incorreta. Gere uma nova chave no GroqCloud e atualize o Render."
            elif 403 in statuses:
                details = [f.get("code") for f in failures if isinstance(f,dict)]
                if "model_permission_blocked_org" in details:
                    public_message = "Groq HTTP 403: modelo bloqueado na organização. Em GroqCloud, abra Settings > Organization > Limits."
                elif "model_permission_blocked_project" in details:
                    public_message = "Groq HTTP 403: modelo bloqueado no projeto. Em GroqCloud, abra Settings > Projects > Limits."
                elif any(f.get("response_kind") == "html" for f in failures if isinstance(f,dict)):
                    public_message = "Groq HTTP 403: resposta HTML recebida. Possível recusa por gateway/proteção de rede antes da inferência; confira o provedor e o tráfego do Render."
                elif any(f.get("response_kind") in ("other", "empty") for f in failures if isinstance(f,dict)):
                    public_message = "Groq HTTP 403: resposta não-JSON ou vazia. Pode ser bloqueio intermediário na conexão de saída do Render."
                elif any(f.get("response_kind") == "json" for f in failures if isinstance(f,dict)):
                    public_message = "Groq HTTP 403: resposta JSON da API, sem código conhecido de bloqueio de modelo. Consulte as permissões e o suporte da Groq."
                else:
                    public_message = "Groq HTTP 403: acesso negado sem detalhe classificável. Confira logs do Render."
            elif result.get("error") in ("advanced_tool_budget_reached", "invalid_tool_call"):
                public_message = "Modo avançado atingiu seu limite de ferramentas. Divida a tarefa em etapas."
            elif result.get("error") in ("empty_advanced_response", "advanced_provider_unavailable"):
                public_message = "Modo avançado sem resposta. Tente novamente ou volte ao chat normal."
            elif 429 in statuses:
                public_message = "O limite de chamadas gratuitas da Groq foi atingido (HTTP 429). Aguarde."
            elif any(s in (400, 404, 422) for s in statuses):
                public_message = "Modelo indisponível na Groq (HTTP " + str(statuses[-1]) + "). Verifique HERMES_GROQ_MODEL."
            elif statuses:
                public_message = "Groq temporariamente indisponível (HTTP " + str(statuses[-1]) + ")."
            else:
                public_message = "Sem resposta da Groq. Consulte os logs do Render."
        elif mode == "anonymous":
            if result.get("error") == "no_authorized_healthy_backends":
                public_message = "Rota pública desativada. Verifique HERMES_PUBLIC_ANONYMOUS_ENABLED."
            elif statuses:
                public_message = "API pública indisponível (HTTP " + str(statuses[-1]) + ")."
            else:
                public_message = "Não foi possível acessar o provedor público. Verifique logs do Render."
        elif 402 in statuses:
            public_message = "HF retornou HTTP 402 e a rota pública não respondeu."
        elif statuses:
            public_message = "Falha de inferência HTTP " + str(statuses[-1])
        else:
            public_message = "Não há provedor de IA disponível."

        raise ModelUnavailable(public_message)
    output = {"output": [{
        "type": "message",
        "content": [{"type":"output_text","text":result["response"]}]
    }]}
    return output, result.get("provider", "groq-free")

simple.call_upstream = chat_via_global_router

if __name__ == "__main__":
    # The endpoint can become healthy even when inference is not configured.
    # Without a password, all other endpoints stay unauthorized (fail closed).
    port = int(os.environ.get("PORT","8080"))
    if not 1 <= port <= 65535:
        raise SystemExit("invalid PORT")
    print("[hermes-light] ready port=%d auth_configured=%s inference_configured=%s" % (
        port, bool(simple.PASSWORD), bool(os.getenv("GROQ_API_KEY"))), flush=True)
    ThreadingHTTPServer(("0.0.0.0",port), simple.Handler).serve_forever()
