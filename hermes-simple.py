import base64, hmac, json, os, time, threading, urllib.request, urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PORT = int(os.getenv("PORT", "9119"))
USER = os.getenv("HERMES_DASHBOARD_BASIC_AUTH_USERNAME", "everton")
PASSWORD = os.getenv("HERMES_DASHBOARD_BASIC_AUTH_PASSWORD", "")
DIRECT_UPSTREAM = os.getenv("HERMES_SIMPLE_DIRECT_UPSTREAM", "http://hermes-cloud.railway.internal:8642").rstrip("/")
DIRECT_KEY = os.getenv("API_SERVER_KEY", "")
BRIDGE_UPSTREAM = os.getenv("HERMES_SIMPLE_BRIDGE_UPSTREAM", "http://hermes-chatgpt-bridge-v2.railway.internal:9120").rstrip("/")
BRIDGE_KEY = os.getenv("HERMES_BRIDGE_KEY", "")
ADVANCED_URL = os.getenv("HERMES_ADVANCED_URL", "https://hermes-cloud-production-13fb.up.railway.app")

HTML = r'''<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Hermes</title>
<style>
:root{
  --bg:#f7f7f5;--panel:#fff;--text:#202123;--muted:#6b6f76;--line:#e6e6e2;
  --accent:#111827;--soft:#f0f1ef;--user:#ececf1;--shadow:0 10px 35px rgba(0,0,0,.06);
}
*{box-sizing:border-box} html,body{height:100%;margin:0}
body{font-family:Inter,ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:var(--bg);color:var(--text)}
button,input,textarea,select{font:inherit}
.app{height:100%;display:grid;grid-template-columns:260px 1fr}
.sidebar{background:#171717;color:#eee;padding:14px 12px;display:flex;flex-direction:column;gap:12px}
.brand{display:flex;align-items:center;gap:10px;padding:8px 9px 14px;font-weight:650}
.logo{width:30px;height:30px;border-radius:9px;background:#fff;color:#111;display:grid;place-items:center;font-weight:800}
.newchat{border:1px solid #3a3a3a;background:#242424;color:#fff;border-radius:10px;padding:11px 12px;text-align:left;cursor:pointer}
.newchat:hover{background:#303030}
.history{overflow:auto;flex:1}
.hist{display:flex;align-items:center;gap:8px;width:100%;border:0;background:transparent;color:#ddd;border-radius:8px;padding:9px 10px;text-align:left;cursor:pointer;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.hist:hover,.hist.active{background:#2b2b2b;color:#fff}
.sidebottom{border-top:1px solid #333;padding-top:10px}
.advanced{display:block;color:#aaa;text-decoration:none;padding:9px 10px;border-radius:8px;font-size:14px}
.advanced:hover{background:#2b2b2b;color:#fff}
.main{min-width:0;display:flex;flex-direction:column;height:100vh}
.topbar{height:58px;border-bottom:1px solid var(--line);background:rgba(255,255,255,.88);backdrop-filter:blur(10px);display:flex;align-items:center;padding:0 18px;gap:12px;position:relative;z-index:3}
.menu{display:none;border:0;background:transparent;font-size:22px;cursor:pointer}
.model{border:1px solid var(--line);background:#fff;border-radius:9px;padding:7px 10px;color:#333}
.status{margin-left:auto;font-size:12px;color:var(--muted)}
.chatwrap{flex:1;overflow:auto}
.chat{max-width:820px;margin:0 auto;padding:34px 22px 160px}
.empty{min-height:60vh;display:grid;place-items:center;text-align:center;color:#34363a}
.empty h1{font-size:30px;margin:0 0 8px}.empty p{color:var(--muted);margin:0}
.msg{display:flex;margin:22px 0}
.msg.user{justify-content:flex-end}
.bubble{max-width:min(78%,720px);line-height:1.55;white-space:pre-wrap;word-wrap:break-word}
.user .bubble{background:var(--user);padding:11px 15px;border-radius:18px 18px 4px 18px}
.assistant .bubble{padding:2px 0}
.role{font-size:12px;color:var(--muted);margin-bottom:5px}
.tool{font-size:12px;color:#8b5e00;background:#fff6d8;border:1px solid #f1df9e;border-radius:8px;padding:7px 9px;margin:6px 0}
.composerbar{position:fixed;left:260px;right:0;bottom:0;padding:18px 22px 24px;background:linear-gradient(transparent,var(--bg) 32%)}
.composer{max-width:820px;margin:0 auto;background:#fff;border:1px solid #dadad6;border-radius:18px;box-shadow:var(--shadow);padding:9px 10px 9px 14px;display:flex;align-items:flex-end;gap:8px}
textarea{flex:1;border:0;outline:none;resize:none;min-height:38px;max-height:180px;padding:8px 2px;background:transparent;line-height:1.45}
.send{width:38px;height:38px;border:0;border-radius:12px;background:#111;color:#fff;cursor:pointer;font-size:18px}
.send:disabled{opacity:.35;cursor:not-allowed}
.note{max-width:820px;margin:7px auto 0;text-align:center;color:#8b8e93;font-size:11px}
.err{background:#fff1f1;border:1px solid #f1c5c5;color:#9e2525;border-radius:10px;padding:10px 12px}
.typing{display:inline-flex;gap:5px;padding:8px 0}.dot{width:6px;height:6px;background:#8c8f93;border-radius:50%;animation:b 1.1s infinite}.dot:nth-child(2){animation-delay:.15s}.dot:nth-child(3){animation-delay:.3s}@keyframes b{0%,80%,100%{opacity:.25;transform:translateY(0)}40%{opacity:1;transform:translateY(-3px)}}
@media(max-width:760px){
 .app{grid-template-columns:1fr}.sidebar{position:fixed;z-index:10;left:0;top:0;bottom:0;width:270px;transform:translateX(-100%);transition:.2s}.sidebar.open{transform:none}.menu{display:block}.composerbar{left:0}.chat{padding-top:22px}.bubble{max-width:90%}
}
</style>
</head>
<body>
<div class="app">
  <aside class="sidebar" id="sidebar">
    <div class="brand"><div class="logo">H</div><div>Hermes</div></div>
    <button class="newchat" id="newchat">＋ Nova conversa</button>
    <div class="history" id="history"></div>
    <div class="sidebottom"><a class="advanced" href="__ADVANCED_URL__" target="_blank">⚙ Avançado</a></div>
  </aside>
  <main class="main">
    <header class="topbar">
      <button class="menu" id="menu">☰</button>
      <select class="model" id="model">
        <option value="auto">Automático · GPT-6 Sol</option>
        <option value="matrix">Matrix</option>
        <option value="local">Hermes Local</option>
      </select>
      <div class="status" id="status">pronto</div>
    </header>
    <div class="chatwrap" id="chatwrap"><div class="chat" id="chat"></div></div>
    <div class="composerbar">
      <div class="composer">
        <textarea id="input" rows="1" placeholder="Pergunte alguma coisa ao Hermes..."></textarea>
        <button class="send" id="send" aria-label="Enviar">↑</button>
      </div>
      <div class="note">Hermes pode usar ferramentas, memória e skills em segundo plano.</div>
    </div>
  </main>
</div>
<script>
const $=s=>document.querySelector(s);
const chat=$('#chat'), input=$('#input'), send=$('#send'), historyEl=$('#history'), statusEl=$('#status');
const key='hermes-simple-conversations-v1';
let conversations=JSON.parse(localStorage.getItem(key)||'[]');
let active=localStorage.getItem('hermes-simple-active')||'';
function uid(){return (crypto.randomUUID?crypto.randomUUID():Date.now()+'-'+Math.random().toString(16).slice(2))}
function save(){localStorage.setItem(key,JSON.stringify(conversations));localStorage.setItem('hermes-simple-active',active);renderHistory()}
function current(){return conversations.find(c=>c.id===active)}
function ensure(){
 if(!current()){const c={id:uid(),title:'Nova conversa',messages:[],created:Date.now()};conversations.unshift(c);active=c.id;save()}
}
function esc(s){return (s||'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}
function renderHistory(){
 historyEl.innerHTML=conversations.map(c=>'<button class="hist '+(c.id===active?'active':'')+'" data-id="'+c.id+'" title="'+esc(c.title)+'">💬 '+esc(c.title)+'</button>').join('');
 historyEl.querySelectorAll('.hist').forEach(b=>b.onclick=()=>{active=b.dataset.id;save();render();$('#sidebar').classList.remove('open')})
}
function render(){
 ensure(); const c=current();
 if(!c.messages.length){chat.innerHTML='<div class="empty"><div><h1>Como posso ajudar?</h1><p>Converse com o Hermes de forma simples.</p></div></div>';return}
 chat.innerHTML=c.messages.map(m=>'<div class="msg '+m.role+'"><div class="bubble">'+(m.role==='assistant'?'<div class="role">Hermes</div>':'')+(m.error?'<div class="err">'+esc(m.text)+'</div>':esc(m.text))+'</div></div>').join('');
 requestAnimationFrame(()=>{$('#chatwrap').scrollTop=$('#chatwrap').scrollHeight})
}
function titleFrom(s){s=(s||'').trim().replace(/\s+/g,' ');return s.length>38?s.slice(0,38)+'…':s||'Nova conversa'}
async function submit(){
 const text=input.value.trim(); if(!text||send.disabled)return;
 ensure(); const c=current(); c.messages.push({role:'user',text});
 if(c.title==='Nova conversa')c.title=titleFrom(text);
 input.value=''; input.style.height='auto'; send.disabled=true; statusEl.textContent='pensando…'; save(); render();
 const holder=document.createElement('div');holder.className='msg assistant';holder.innerHTML='<div class="bubble"><div class="role">Hermes</div><div class="typing"><i class="dot"></i><i class="dot"></i><i class="dot"></i></div></div>';chat.appendChild(holder);$('#chatwrap').scrollTop=$('#chatwrap').scrollHeight;
 try{
  const res=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({conversation:'web-'+c.id,input:text,route:$('#model').value})});
  const data=await res.json().catch(()=>({}));
  holder.remove();
  if(!res.ok)throw new Error(data.error||'Falha ao conversar com o Hermes');
  c.messages.push({role:'assistant',text:data.text||'(sem resposta)'});
 }catch(e){holder.remove();c.messages.push({role:'assistant',text:e.message||'Erro de conexão',error:true})}
 finally{send.disabled=false;statusEl.textContent='pronto';save();render();input.focus()}
}
$('#newchat').onclick=()=>{const c={id:uid(),title:'Nova conversa',messages:[],created:Date.now()};conversations.unshift(c);active=c.id;save();render();input.focus();$('#sidebar').classList.remove('open')};
send.onclick=submit;
input.onkeydown=e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();submit()}};
input.oninput=()=>{input.style.height='auto';input.style.height=Math.min(input.scrollHeight,180)+'px'};
$('#menu').onclick=()=>$('#sidebar').classList.toggle('open');
ensure();renderHistory();render();
</script>
</body></html>'''.replace("__ADVANCED_URL__", ADVANCED_URL)

def auth_ok(headers):
    if not USER or not PASSWORD:
        return False
    h = headers.get("Authorization", "")
    if not h.startswith("Basic "):
        return False
    try:
        decoded = base64.b64decode(h[6:]).decode("utf-8")
        u, p = decoded.split(":", 1)
        return hmac.compare_digest(u, USER) and hmac.compare_digest(p, PASSWORD)
    except Exception:
        return False

def call_upstream(payload):
    """Use the isolated bridge as the single stable chat path."""
    if not BRIDGE_KEY:
        raise RuntimeError("Bridge Hermes não configurado")
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(BRIDGE_UPSTREAM + "/v1/responses", data=body, method="POST", headers={
        "Authorization": "Bearer " + BRIDGE_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=900) as res:
            return json.load(res), "bridge"
    except urllib.error.HTTPError as e:
        raw = e.read(8192)
        raise RuntimeError(f"bridge HTTP {e.code}: " + raw.decode("utf-8","ignore")[:400]) from e

def bridge_smoke():
    """One bounded startup self-test. Never logs credentials."""
    if not BRIDGE_KEY:
        print("[hermes-simple] bridge-smoke skipped: missing bridge key", flush=True)
        return
    try:
        req = urllib.request.Request(BRIDGE_UPSTREAM + "/v1/models", headers={
            "Authorization": "Bearer " + BRIDGE_KEY,
            "Accept": "application/json",
        })
        with urllib.request.urlopen(req, timeout=15) as res:
            data = json.load(res)
        models_ok = bool(data.get("data"))
        print(f"[hermes-simple] bridge-models status=200 models_ok={str(models_ok).lower()}", flush=True)
    except urllib.error.HTTPError as e:
        print(f"[hermes-simple] bridge-models status={e.code}", flush=True)
        return
    except Exception as e:
        print(f"[hermes-simple] bridge-models error={type(e).__name__}", flush=True)
        return

    try:
        body = json.dumps({
            "model": "hermes-agent",
            "messages": [{"role": "user", "content": "Reply only: HERMES_SIMPLE_OK"}],
            "stream": False,
        }).encode("utf-8")
        req = urllib.request.Request(BRIDGE_UPSTREAM + "/v1/chat/completions", data=body, method="POST", headers={
            "Authorization": "Bearer " + BRIDGE_KEY,
            "Content-Type": "application/json",
            "Accept": "application/json",
        })
        with urllib.request.urlopen(req, timeout=90) as res:
            data = json.load(res)
        text = str((((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""))
        print(f"[hermes-simple] bridge-chat status=200 ok={str('HERMES_SIMPLE_OK' in text).lower()}", flush=True)
    except urllib.error.HTTPError as e:
        print(f"[hermes-simple] bridge-chat status={e.code}", flush=True)
    except Exception as e:
        print(f"[hermes-simple] bridge-chat error={type(e).__name__}", flush=True)


def response_text(data):
    parts=[]
    for item in data.get("output",[]) or []:
        if item.get("type")=="message":
            for c in item.get("content",[]) or []:
                if c.get("type") in ("output_text","text") and c.get("text"):
                    parts.append(c["text"])
    if parts:
        return "\n".join(parts).strip()
    if isinstance(data.get("output_text"), str):
        return data["output_text"].strip()
    return ""

class Handler(BaseHTTPRequestHandler):
    protocol_version="HTTP/1.1"
    def log_message(self, fmt, *args):
        print("[hermes-simple] "+(fmt%args), flush=True)
    def sendb(self,status,body,ctype="application/json; charset=utf-8"):
        if isinstance(body,str): body=body.encode()
        self.send_response(status)
        self.send_header("Content-Type",ctype)
        self.send_header("Content-Length",str(len(body)))
        self.send_header("Cache-Control","no-store")
        self.end_headers()
        self.wfile.write(body)
    def require_auth(self):
        if auth_ok(self.headers): return True
        self.send_response(401)
        self.send_header("WWW-Authenticate",'Basic realm="Hermes"')
        self.send_header("Content-Length","0")
        self.end_headers()
        return False
    def do_GET(self):
        if self.path=="/health":
            return self.sendb(200,'{"status":"ok"}')
        if not self.require_auth(): return
        if self.path.split("?",1)[0] in ("/","/index.html","/chat"):
            return self.sendb(200,HTML,"text/html; charset=utf-8")
        return self.sendb(404,'{"error":"not_found"}')
    def do_POST(self):
        if not self.require_auth(): return
        if self.path!="/api/chat":
            return self.sendb(404,'{"error":"not_found"}')
        try:
            n=int(self.headers.get("Content-Length","0"))
            msg=json.loads(self.rfile.read(n) or b"{}")
            text=(msg.get("input") or "").strip()
            conv=(msg.get("conversation") or "").strip()
            route=(msg.get("route") or "auto").strip()
            if not text:
                return self.sendb(400,'{"error":"Mensagem vazia"}')
            payload={"input":text,"conversation":conv or ("web-"+str(int(time.time()*1000))),"store":True}
            if route=="matrix":
                payload.update({"provider":"matrix","model":"claude-opus-5"})
            elif route=="local":
                payload.update({"provider":"hermes-local","model":"hermes-agent"})
            data, via=call_upstream(payload)
            out=response_text(data)
            if not out:
                out="O Hermes concluiu a execução, mas não retornou texto."
            return self.sendb(200,json.dumps({"text":out,"via":via},ensure_ascii=False))
        except Exception as e:
            print("[hermes-simple] chat error "+type(e).__name__+": "+str(e)[:500],flush=True)
            return self.sendb(502,json.dumps({"error":"Não consegui falar com o Hermes agora. Tente novamente.","type":type(e).__name__},ensure_ascii=False))

if __name__=="__main__":
    if not PASSWORD:
        raise SystemExit("HERMES_DASHBOARD_BASIC_AUTH_PASSWORD missing")
    print(f"[hermes-simple] listening on 0.0.0.0:{PORT}",flush=True)
    threading.Thread(target=bridge_smoke, daemon=True).start()
    ThreadingHTTPServer(("0.0.0.0",PORT),Handler).serve_forever()
