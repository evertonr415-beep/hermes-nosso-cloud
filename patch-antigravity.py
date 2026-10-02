from pathlib import Path

p = Path('/app/hermes-simple.py')
s = p.read_text()

# Google Antigravity managed-agent route. This is intentionally manual-only in
# the model picker for now, so the existing automatic Hermes routing is not
# changed. A GEMINI_API_KEY is required at runtime.
anchor = 'ADVANCED_URL = os.getenv("HERMES_ADVANCED_URL", "https://hermes-cloud-production-13fb.up.railway.app")\n'
insert = '''ADVANCED_URL = os.getenv("HERMES_ADVANCED_URL", "https://hermes-cloud-production-13fb.up.railway.app")\nGEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()\nANTIGRAVITY_AGENT = os.getenv("HERMES_ANTIGRAVITY_AGENT", "antigravity-preview-09-2026").strip() or "antigravity-preview-09-2026"\nANTIGRAVITY_MODEL = os.getenv("HERMES_ANTIGRAVITY_MODEL", "").strip()\ntry:\n    ANTIGRAVITY_MAX_TOKENS = max(5000, min(100000, int(os.getenv("HERMES_ANTIGRAVITY_MAX_TOKENS", "30000"))))\nexcept Exception:\n    ANTIGRAVITY_MAX_TOKENS = 30000\nANTIGRAVITY_SESSIONS = {}\nANTIGRAVITY_LOCK = threading.Lock()\nANTIGRAVITY_SESSION_TTL = 6 * 60 * 60\n'''
if 'GEMINI_API_KEY = os.getenv("GEMINI_API_KEY"' not in s:
    if anchor not in s:
        raise SystemExit('antigravity env anchor not found')
    s = s.replace(anchor, insert, 1)

# Add the fifth manual route beside the established paid route. Running this
# after patch-hybrid-mode keeps the current four routes untouched.
paid_option = '<option value="paid">GPT-5.6 Sol · Pago</option>'
if '<option value="antigravity">Antigravity · Agente</option>' not in s:
    if paid_option not in s:
        raise SystemExit('antigravity model option anchor not found')
    s = s.replace(paid_option, paid_option + '\n        <option value="antigravity">Antigravity · Agente</option>', 1)

helpers = r'''def _antigravity_cleanup_sessions():
    now = time.time()
    with ANTIGRAVITY_LOCK:
        for key, item in list(ANTIGRAVITY_SESSIONS.items()):
            if now - float(item.get("updated") or now) > ANTIGRAVITY_SESSION_TTL:
                ANTIGRAVITY_SESSIONS.pop(key, None)


def _antigravity_request(method, url, payload=None, timeout=90):
    if not GEMINI_API_KEY:
        raise RuntimeError("Antigravity ainda não está configurado. Adicione GEMINI_API_KEY ao serviço hermes-web no Railway.")
    headers = {
        "x-goog-api-key": GEMINI_API_KEY,
        "Accept": "application/json",
        "Api-Revision": "2026-05-20",
    }
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            raw = res.read(8 * 1024 * 1024)
            return json.loads(raw.decode("utf-8", "ignore") or "{}")
    except urllib.error.HTTPError as exc:
        raw = exc.read(1024 * 1024).decode("utf-8", "ignore")
        raise RuntimeError(f"Antigravity HTTP {exc.code}: {raw[:1000]}") from exc


def call_antigravity(text, conversation):
    """Run one Google Antigravity managed-agent interaction.

    The browser request is already detached by Hermes' async job layer, so this
    worker can safely poll Google's background interaction for several minutes.
    Conversation state is continued while this hermes-web replica stays alive.
    """
    if not GEMINI_API_KEY:
        raise RuntimeError("Antigravity ainda não está configurado. Adicione GEMINI_API_KEY ao serviço hermes-web no Railway.")

    _antigravity_cleanup_sessions()
    conv_key = (conversation or "").strip() or ("antigravity-" + uuid.uuid4().hex)
    with ANTIGRAVITY_LOCK:
        previous = dict(ANTIGRAVITY_SESSIONS.get(conv_key) or {})

    config = {
        "type": "antigravity",
        "max_total_tokens": ANTIGRAVITY_MAX_TOKENS,
    }
    if ANTIGRAVITY_MODEL:
        config["model"] = ANTIGRAVITY_MODEL

    payload = {
        "agent": ANTIGRAVITY_AGENT,
        "input": text,
        "agent_config": config,
        "background": True,
    }
    if previous.get("interaction_id") and previous.get("environment_id"):
        payload["previous_interaction_id"] = previous["interaction_id"]
        payload["environment"] = previous["environment_id"]
    else:
        payload["environment"] = "remote"

    base = "https://generativelanguage.googleapis.com/v1beta/interactions"
    started = _antigravity_request("POST", base, payload, timeout=90)
    interaction_id = str(started.get("id") or "").strip()
    if not interaction_id:
        raise RuntimeError("Antigravity não retornou um interaction id válido")

    result = started
    deadline = time.time() + 13 * 60
    while str(result.get("status") or "").lower() in ("in_progress", "pending", "queued"):
        if time.time() >= deadline:
            raise RuntimeError("Antigravity excedeu o tempo máximo desta execução")
        time.sleep(3)
        result = _antigravity_request("GET", base + "/" + urllib.parse.quote(interaction_id, safe=""), timeout=90)

    status = str(result.get("status") or "").lower()
    environment_id = str(result.get("environment_id") or started.get("environment_id") or "").strip()
    final_id = str(result.get("id") or interaction_id).strip()
    if environment_id:
        with ANTIGRAVITY_LOCK:
            ANTIGRAVITY_SESSIONS[conv_key] = {
                "interaction_id": final_id,
                "environment_id": environment_id,
                "updated": time.time(),
            }

    if status in ("failed", "cancelled", "canceled"):
        detail = result.get("error") or result.get("status_message") or status
        raise RuntimeError("Antigravity terminou com erro: " + str(detail)[:1000])

    output_text = result.get("output_text")
    if not isinstance(output_text, str) or not output_text.strip():
        # Keep response_text() compatibility if Google returns message items.
        output_text = response_text(result)
    if not output_text:
        if status == "incomplete":
            output_text = "O Antigravity atingiu o limite de execução antes de produzir uma resposta final. Você pode pedir para continuar nesta mesma conversa."
        else:
            output_text = "O Antigravity concluiu a execução, mas não retornou texto."

    return {
        "output_text": output_text,
        "id": final_id,
        "environment_id": environment_id,
        "status": status or "completed",
    }, "google-antigravity"


'''
helper_anchor = 'def call_paid_upstream(payload):\n'
if 'def call_antigravity(text, conversation):' not in s:
    if helper_anchor not in s:
        raise SystemExit('antigravity helper anchor not found')
    s = s.replace(helper_anchor, helpers + helper_anchor, 1)

# urllib.parse is required only by the Antigravity interaction polling URL.
if 'urllib.parse' not in s.split('\n', 1)[0]:
    first = s.split('\n', 1)[0]
    if 'urllib.error' in first:
        s = s.replace('urllib.request, urllib.error,', 'urllib.request, urllib.error, urllib.parse,', 1)
    else:
        raise SystemExit('urllib import anchor not found')

old_route = '''            if route=="paid":\n                data, via=call_paid_upstream(payload)\n            else:\n                if route=="matrix":\n                    payload.update({"provider":"matrix","model":"claude-opus-5"})\n                elif route=="local":\n                    payload.update({"provider":"hermes-local","model":"hermes-agent"})\n                data, via=call_upstream(payload)\n'''
new_route = '''            if route=="antigravity":\n                data, via=call_antigravity(text, payload.get("conversation") or conv)\n            elif route=="paid":\n                data, via=call_paid_upstream(payload)\n            else:\n                if route=="matrix":\n                    payload.update({"provider":"matrix","model":"claude-opus-5"})\n                elif route=="local":\n                    payload.update({"provider":"hermes-local","model":"hermes-agent"})\n                data, via=call_upstream(payload)\n'''
if 'route=="antigravity"' not in s:
    if old_route not in s:
        raise SystemExit('antigravity route execution anchor not found')
    s = s.replace(old_route, new_route, 1)

old_meta = '''    elif route == "paid":\n        provider = "GPT-5.6 Sol · Pago" if category == "Geral" else provider\n    elif route == "auto" and category == "Geral":\n'''
new_meta = '''    elif route == "paid":\n        provider = "GPT-5.6 Sol · Pago" if category == "Geral" else provider\n    elif route == "antigravity":\n        provider = "Google Antigravity"\n        if category == "Geral":\n            skill = "managed-agent"\n    elif route == "auto" and category == "Geral":\n'''
if 'provider = "Google Antigravity"' not in s:
    if old_meta not in s:
        raise SystemExit('antigravity route metadata anchor not found')
    s = s.replace(old_meta, new_meta, 1)

# Give missing-key and quota errors a useful UI message instead of a generic 502.
old_error_branch = '''            if "credit_balance_exhausted" in detail or "no credits remaining" in detail.lower() or "insufficient_quota" in detail:\n                message="A rota GPT-5.6 Sol · Pago está sem créditos de API no momento. Adicione créditos na conta da API OpenAI para usar esta rota."\n            else:\n                message="Não consegui falar com o Hermes agora. Tente novamente."\n'''
new_error_branch = '''            if "Antigravity ainda não está configurado" in detail:\n                message="A rota Antigravity foi instalada, mas falta configurar GEMINI_API_KEY no hermes-web. Depois de adicionar a chave, ela fica ativa sem mudar o código."\n            elif "Antigravity HTTP 429" in detail:\n                message="O Antigravity atingiu o limite/cota da Gemini API. Verifique a cota do projeto no Google AI Studio e tente novamente."\n            elif "credit_balance_exhausted" in detail or "no credits remaining" in detail.lower() or "insufficient_quota" in detail:\n                message="A rota GPT-5.6 Sol · Pago está sem créditos de API no momento. Adicione créditos na conta da API OpenAI para usar esta rota."\n            else:\n                message="Não consegui falar com o Hermes agora. Tente novamente."\n'''
if 'A rota Antigravity foi instalada' not in s:
    if old_error_branch in s:
        s = s.replace(old_error_branch, new_error_branch, 1)

p.write_text(s)
print('antigravity agent route patch applied')
