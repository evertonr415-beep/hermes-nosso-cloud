from pathlib import Path

p = Path('/app/hermes-simple.py')
s = p.read_text()

# Keep automatic chat on the existing strong Hermes brain. Free/local executors
# remain first for media. The paid GPT route below is manual-only: it runs only
# when the user explicitly selects it in the model dropdown.
s = s.replace('Automático · GPT-6 Sol', 'Automático · Inteligência forte')
s = s.replace(
    '<option value="auto">Automático · Inteligência forte</option>',
    '<option value="auto">Automático · Inteligência forte</option>\n        <option value="paid">GPT-5.6 Sol · Pago</option>'
)
s = s.replace('<span class="zerocost">Zero Cost Mode</span>', '<span class="zerocost">Mídia grátis primeiro</span>')
s = s.replace(
    'Zero Cost Mode: vídeo com imagem anexada é gerado localmente. Provider pago não é usado nesse caminho.',
    'Modo híbrido: cérebro forte no Automático · mídia grátis/local primeiro · GPT-5.6 Sol Pago só quando selecionado manualmente.'
)
s = s.replace('provider = "GPT-6 Sol"', 'provider = "Hermes · inteligência forte"')
s = s.replace(
    'Os geradores gratuitos estão temporariamente sem capacidade. A foto de referência não foi ignorada e nenhum resultado aleatório foi criado. Tente novamente em alguns minutos.',
    'Capacidade gratuita de imagem esgotada no momento. Tente novamente em cerca de 10 minutos. Nenhum serviço pago foi utilizado.'
)

helper = r'''def call_paid_upstream(payload):
    """Call the bridge's explicit paid GPT-5.6 Sol route.

    This helper is never used by automatic fallback logic; route=paid must be
    selected by the user in the UI.
    """
    if not BRIDGE_KEY:
        raise RuntimeError("Bridge Hermes não configurado")
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(BRIDGE_UPSTREAM + "/v1/paid/responses", data=body, method="POST", headers={
        "Authorization": "Bearer " + BRIDGE_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=360) as res:
            return json.load(res), "paid-gpt-5.6-sol"
    except urllib.error.HTTPError as e:
        raw = e.read(8192)
        raise RuntimeError(f"paid GPT HTTP {e.code}: " + raw.decode("utf-8","ignore")[:400]) from e


'''
if 'def call_paid_upstream(payload):' not in s:
    anchor='def bridge_smoke():\n'
    if anchor not in s:
        raise SystemExit('bridge smoke anchor not found')
    s=s.replace(anchor, helper + anchor)

old = '''            payload={"input":text,"conversation":conv or ("web-"+str(int(time.time()*1000))),"store":True}
            if route=="matrix":
                payload.update({"provider":"matrix","model":"claude-opus-5"})
            elif route=="local":
                payload.update({"provider":"hermes-local","model":"hermes-agent"})
            data, via=call_upstream(payload)
'''
new = '''            payload={"input":text,"conversation":conv or ("web-"+str(int(time.time()*1000))),"store":True}
            if route=="paid":
                data, via=call_paid_upstream(payload)
            else:
                if route=="matrix":
                    payload.update({"provider":"matrix","model":"claude-opus-5"})
                elif route=="local":
                    payload.update({"provider":"hermes-local","model":"hermes-agent"})
                data, via=call_upstream(payload)
'''
if old not in s:
    raise SystemExit('paid route execution anchor not found')
s=s.replace(old,new)

old_meta='''    if route == "matrix":
        provider = "Matrix" if category == "Geral" else provider
    elif route == "local":
        provider = "Hermes Local" if category == "Geral" else provider
    elif route == "auto" and category == "Geral":
        provider = "Hermes · inteligência forte"
'''
new_meta='''    if route == "matrix":
        provider = "Matrix" if category == "Geral" else provider
    elif route == "local":
        provider = "Hermes Local" if category == "Geral" else provider
    elif route == "paid":
        provider = "GPT-5.6 Sol · Pago" if category == "Geral" else provider
    elif route == "auto" and category == "Geral":
        provider = "Hermes · inteligência forte"
'''
if old_meta in s:
    s=s.replace(old_meta,new_meta)

p.write_text(s)
