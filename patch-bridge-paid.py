from pathlib import Path

p = Path('/app/bridge.py')
s = p.read_text()

if 'PAID_STATE={}' not in s:
    s = s.replace(
        'IMAGE_TTL=60*60\n',
        'IMAGE_TTL=60*60\nPAID_STATE={}\nPAID_LOCK=threading.Lock()\n'
    )

helper = r'''
def paid_gpt_response(prompt, conversation=""):
    """Explicit paid GPT-5.6 Sol route. Never used as an automatic fallback."""
    if not OPENAI_KEY:
        raise RuntimeError("OPENAI_API_KEY missing")
    prompt=(prompt or "").strip()
    if not prompt:
        raise ValueError("input_required")
    conversation=(conversation or "paid-default").strip()
    payload={
        "model":"gpt-5.6-sol",
        "input":prompt,
        "reasoning":{"effort":"medium"},
        "store":True,
    }
    with PAID_LOCK:
        previous=PAID_STATE.get(conversation)
    if previous:
        payload["previous_response_id"]=previous

    def request_once(data):
        body=json.dumps(data).encode("utf-8")
        req=urllib.request.Request(
            "https://api.openai.com/v1/responses",
            data=body,
            method="POST",
            headers={
                "Authorization":"Bearer "+OPENAI_KEY,
                "Content-Type":"application/json",
                "Accept":"application/json",
            },
        )
        with urllib.request.urlopen(req,timeout=300) as res:
            return json.load(res)

    try:
        data=request_once(payload)
    except urllib.error.HTTPError as exc:
        # A stale previous_response_id should not break a new paid chat after a restart.
        if previous and exc.code in (400,404):
            payload.pop("previous_response_id",None)
            data=request_once(payload)
        else:
            raise
    rid=str(data.get("id") or "")
    if rid:
        with PAID_LOCK:
            PAID_STATE[conversation]=rid
    print(f"[paid-gpt] success model=gpt-5.6-sol conversation={conversation[:40]}",flush=True)
    return data

'''

if 'def paid_gpt_response(' not in s:
    s = s.replace('class Handler(BaseHTTPRequestHandler):\n', helper + 'class Handler(BaseHTTPRequestHandler):\n')

route = r'''        if path=="/v1/paid/responses" and self.command=="POST":
            if not self.authorized(): return self.reply(401,b'{"error":"unauthorized"}')
            try:
                body=self.rfile.read(int(self.headers.get("Content-Length","0")))
                msg=json.loads(body or b"{}")
                prompt=msg.get("input") or ""
                conversation=msg.get("conversation") or ""
                data=paid_gpt_response(prompt,conversation)
                return self.reply(200,json.dumps(data).encode())
            except urllib.error.HTTPError as exc:
                raw=exc.read(8192)
                print(f"[paid-gpt] http={exc.code}",flush=True)
                return self.reply(exc.code,raw or json.dumps({"error":"openai_paid_http"}))
            except Exception as exc:
                print(f"[paid-gpt] failed type={type(exc).__name__}",flush=True)
                return self.reply(502,json.dumps({"error":"paid_gpt_failed","type":type(exc).__name__}).encode())
'''

if '/v1/paid/responses' not in s:
    anchor='        if path=="/mcp" and self.command=="POST": return self.mcp()\n'
    if anchor not in s:
        raise SystemExit('paid route anchor not found')
    s=s.replace(anchor, route + anchor)

p.write_text(s)
